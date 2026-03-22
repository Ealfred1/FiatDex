from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import User
from app.models.holding import Holding
from app.models.transaction import Transaction
from app.services.auth_service import auth_service
from app.services.injective_service import injective_service
from app.schemas.sell import (
    SellQuoteRequest, SellQuoteResponse, SellExecuteRequest, SellExecuteResponse
)
from datetime import datetime, timedelta, timezone
import uuid
from decimal import Decimal

router = APIRouter(tags=["Sell Tokens"])

@router.post("/quote", response_model=SellQuoteResponse)
async def get_sell_quote(
    request: SellQuoteRequest,
    user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a quote for selling a token back to USD balance.
    """
    # 1. Verify user holds the token
    stmt = select(Holding).where(
        Holding.user_id == user.id,
        Holding.token_denom == request.token_denom
    )
    res = await db.execute(stmt)
    holding = res.scalar_one_or_none()
    
    if not holding or holding.amount < request.amount:
        raise HTTPException(status_code=400, detail="Insufficient holdings")

    # 2. Get market price 
    # For now, simulate price from injective_service
    # market_id = request.token_denom # Simplified
    summaries = await injective_service.get_all_market_summaries()
    # Market IDs in this system seem to be denoms or a specific format
    # We'll just look for a match
    summary = next((s for s in summaries if s.market_id == request.token_denom or s.base_denom == request.token_denom), None)
    
    if not summary:
        raise HTTPException(status_code=404, detail="Market not found for this token")

    price = summary.last_price
    gross_usd = request.amount * price
    fee_usd = gross_usd * Decimal("0.01") # 1% fee
    net_usd = gross_usd - fee_usd

    return SellQuoteResponse(
        token_denom=request.token_denom,
        token_symbol=holding.token_symbol,
        amount_to_sell=request.amount,
        estimated_usd_received=net_usd,
        exchange_rate=price,
        fee_usd=fee_usd,
        expires_at=datetime.utcnow() + timedelta(seconds=30)
    )

@router.post("/execute", response_model=SellExecuteResponse)
async def execute_sell(
    request: SellExecuteRequest,
    user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Execute a token sell. 
    1. Deducts from holdings.
    2. Increments user balance.
    3. Records transaction.
    """
    # 1. Verify and Lock Holding
    stmt = select(Holding).where(
        Holding.user_id == user.id,
        Holding.token_denom == request.token_denom
    )
    res = await db.execute(stmt)
    holding = res.scalar_one_or_none()
    
    if not holding or holding.amount < request.amount:
        raise HTTPException(status_code=400, detail="Insufficient holdings")

    # 2. Re-verify price (Simplified simulation)
    summaries = await injective_service.get_all_market_summaries()
    summary = next((s for s in summaries if s.market_id == request.token_denom or s.base_denom == request.token_denom), None)
    if not summary:
        raise HTTPException(status_code=404, detail="Market not found")
        
    price = summary.last_price
    gross_usd = request.amount * price
    fee_usd = gross_usd * Decimal("0.01")
    net_usd = gross_usd - fee_usd

    if net_usd < request.min_usd_expected:
        raise HTTPException(status_code=400, detail="Price moved too much (slippage exceeded)")

    # 3. Update DB
    holding.amount -= request.amount
    user.account_balance += net_usd
    
    # 4. Create Transaction record
    tx = Transaction(
        user_id=user.id,
        onramp_provider="internal_sell",
        onramp_order_id=f"sell_{uuid.uuid4().hex[:8]}",
        fiat_amount=net_usd,
        fiat_currency="USD",
        fiat_status="completed",
        target_denom=request.token_denom,
        target_token_symbol=holding.token_symbol,
        swap_status="confirmed", # For sells we simulate immediate confirmation in this build
        swap_amount_received=request.amount,
        swap_tx_hash=f"local_{uuid.uuid4().hex}"
    )
    db.add(tx)
    
    await db.commit()

    return SellExecuteResponse(
        transaction_id=str(tx.id),
        status="completed",
        token_symbol=holding.token_symbol,
        usd_received=net_usd,
        tx_hash=tx.swap_tx_hash
    )
