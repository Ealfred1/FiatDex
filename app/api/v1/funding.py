from fastapi import APIRouter, Depends, Request, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import User
from app.models.funding import AccountFunding
from app.services.auth_service import auth_service
from app.services.paystack_service import PaystackService
from app.schemas.funding import (
    FundingInitiateRequest, FundingInitiateResponse, 
    FundingHistoryResponse, BalanceResponse
)
from typing import List
import json
from decimal import Decimal

router = APIRouter()
paystack_service = PaystackService()

@router.post("/initiate", response_model=FundingInitiateResponse)
async def initiate_funding(
    request: FundingInitiateRequest,
    user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Initialize a fiat funding transaction via Paystack.
    Returns the authorization URL for the user to complete payment.
    """
    if not user.email:
        raise HTTPException(status_code=400, detail="Email required for funding")

    # Call Paystack
    res = await paystack_service.initialize_transaction(
        email=user.email,
        amount_fiat=request.amount,
        currency=request.currency
    )
    if not res:
        raise HTTPException(status_code=500, detail="Failed to initialize Paystack transaction")

    # Calculate USD equivalent
    rate = await paystack_service.get_fiat_to_usd_rate(request.currency)
    amount_usd = request.amount / rate

    # Save pending record
    funding = AccountFunding(
        user_id=user.id,
        reference=res["reference"],
        amount=request.amount,
        currency=request.currency.upper(),
        amount_usd=amount_usd,
        status="pending"
    )
    db.add(funding)
    await db.commit()

    return FundingInitiateResponse(
        authorization_url=res["authorization_url"],
        access_code=res["access_code"],
        reference=res["reference"]
    )

@router.post("/webhook/paystack")
async def paystack_webhook(
    request: Request,
    x_paystack_signature: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Webhook handler for Paystack status updates.
    Verifies signature and updates user balance on success.
    """
    body = await request.body()
    if not paystack_service.verify_webhook_signature(body, x_paystack_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = json.loads(body)
    event = payload.get("event")
    data = payload.get("data")

    if event == "charge.success":
        reference = data.get("reference")
        # Find funding record
        stmt = select(AccountFunding).where(AccountFunding.reference == reference)
        res = await db.execute(stmt)
        funding = res.scalar_one_or_none()

        if funding and funding.status == "pending":
            funding.status = "success"
            funding.paystack_id = str(data.get("id"))
            funding.channel = data.get("channel")
            
            # Increment user balance
            stmt_user = select(User).where(User.id == funding.user_id)
            res_user = await db.execute(stmt_user)
            user = res_user.scalar_one()
            user.account_balance += funding.amount_usd
            
            await db.commit()
    
    elif event in ["charge.failed", "transfer.failed"]:
        reference = data.get("reference")
        stmt = select(AccountFunding).where(AccountFunding.reference == reference)
        res = await db.execute(stmt)
        funding = res.scalar_one_or_none()
        if funding and funding.status == "pending":
            funding.status = "failed"
            await db.commit()

    return {"status": "success"}

@router.get("/balance", response_model=BalanceResponse)
async def get_balance(user: User = Depends(auth_service.get_current_user)):
    """
    Get current funded account balance in USD.
    """
    return BalanceResponse(account_balance=user.account_balance)

@router.get("/history", response_model=List[FundingHistoryResponse])
async def get_funding_history(
    user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get funding transaction history.
    """
    stmt = select(AccountFunding).where(AccountFunding.user_id == user.id).order_by(AccountFunding.created_at.desc())
    res = await db.execute(stmt)
    fundings = res.scalars().all()
    return fundings
