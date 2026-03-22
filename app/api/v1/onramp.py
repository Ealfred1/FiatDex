from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal
import uuid
from datetime import datetime

from app.core.database import get_db
from app.models.user import User
from app.models.transaction import Transaction
from app.schemas.onramp import OnrampQuote, OnrampSession, FiatQuote
from app.services.transak_service import transak_service
from app.services.kado_service import kado_service
from app.services.swap_service import swap_service
from app.services.price_service import price_service
from app.dependencies import get_current_user

router = APIRouter(prefix="/onramp", tags=["Onramp"])

@router.post("/quote", response_model=OnrampQuote)
async def get_onramp_quote(
    fiat_amount: Decimal,
    fiat_currency: str,
    target_market_id: str,
    payment_method: str = "credit_debit_card",
    current_user: User = Depends(get_current_user)
):
    """
    Get a fiat onramp quote from available providers.
    """
    # Primary: Transak
    try:
        quote = await transak_service.get_fiat_quote(
            fiat_amount=fiat_amount,
            fiat_currency=fiat_currency,
            payment_method=payment_method
        )
        provider = "transak"
    except Exception:
        # Fallback: Kado
        quote = await kado_service.get_quote(fiat_amount, fiat_currency)
        provider = "kado"

    # Estimate final token output
    swap_est = await swap_service.get_swap_estimate(quote.crypto_amount, target_market_id)

    return OnrampQuote(
        provider=provider,
        fiat_amount=fiat_amount,
        fiat_currency=fiat_currency,
        estimated_inj_amount=quote.crypto_amount,
        estimated_target_token_amount=swap_est.target_amount,
        exchange_rate=quote.conversion_price,
        fees={
            "onramp_fee": quote.service_fee,
            "network_fee": quote.network_fee,
            "swap_fee": swap_est.fee_amount,
            "total_fee": quote.total_fee + swap_est.fee_amount
        },
        min_amount=Decimal("10.00"),
        max_amount=Decimal("5000.00"),
        supported_payment_methods=["credit_debit_card", "bank_transfer"]
    )

@router.post("/initiate", response_model=OnrampSession)
async def initiate_onramp(
    fiat_amount: Decimal,
    fiat_currency: str,
    target_market_id: str,
    payment_method: str = "credit_debit_card",
    slippage_tolerance: float = 0.01,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a transaction record and generate a widget URL for the onramp session.
    """
    order_id = str(uuid.uuid4())
    
    # 1. Create transaction in DB
    new_tx = Transaction(
        user_id=current_user.id,
        onramp_provider="transak", # Default for now
        onramp_order_id=order_id,
        fiat_amount=fiat_amount,
        fiat_currency=fiat_currency,
        target_market_id=target_market_id,
        target_token_symbol="UNKNOWN", # Should be resolved from market_id
        swap_slippage_tolerance=slippage_tolerance
    )
    db.add(new_tx)
    await db.commit()
    
    # 2. Generate widget URL
    widget_url = await transak_service.generate_widget_url(
        fiat_amount=fiat_amount,
        fiat_currency=fiat_currency,
        wallet_address=current_user.wallet_address,
        order_id=order_id
    )
    
    return OnrampSession(
        transaction_id=str(new_tx.id),
        widget_url=widget_url,
        provider="transak",
        order_id=order_id,
        expires_at=datetime.utcnow() + timedelta(minutes=30)
    )

@router.post("/webhook/transak")
async def transak_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Handle incoming webhooks from Transak upon order completion.
    """
    payload = await request.body()
    signature = request.headers.get("x-transak-signature")
    
    if not await transak_service.verify_webhook_signature(payload, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
        
    data = await request.json()
    result = await transak_service.process_order_completed_webhook(data)
    
    if result.status == "COMPLETED":
        # 1. Find transaction
        stmt = select(Transaction).where(Transaction.onramp_order_id == result.order_id)
        db_res = await db.execute(stmt)
        tx = db_res.scalar_one_or_none()
        
        if tx:
            tx.fiat_status = "completed"
            tx.inj_amount = result.crypto_amount
            await db.commit()
            
            # 2. Trigger auto-swap task
            await swap_service.initiate_auto_swap(
                transaction_id=tx.id,
                inj_amount=result.crypto_amount,
                target_market_id=tx.target_market_id,
                wallet_address=result.wallet_address
            )
            
    return {"status": "ok"}

from datetime import timedelta
