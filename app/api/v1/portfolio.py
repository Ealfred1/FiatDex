from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from decimal import Decimal
from typing import List

from app.core.database import get_db
from app.models.user import User
from app.models.transaction import Transaction
from app.schemas.portfolio import Portfolio, Holding, TransactionSummary
from app.services.injective_service import injective_service
from app.services.price_service import price_service
from app.dependencies import get_current_user

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])

@router.get("", response_model=Portfolio)
async def get_portfolio(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Get user's total portfolio value and individual holdings.
    """
    balances = await injective_service.get_wallet_balances(current_user.wallet_address)
    
    holdings = []
    total_val_usd = Decimal(0)
    for b in balances:
        # In actual, we'd fetch price for each denom
        price_usd = await price_service.get_token_price_usd(b.denom) or Decimal(0)
        val_usd = b.balance * price_usd
        total_val_usd += val_usd
        
        holdings.append(Holding(
            denom=b.denom,
            symbol=b.symbol,
            amount=b.balance,
            value_usd=val_usd,
            value_local=val_usd * 1, # Placeholder
            change_24h_pct=0.0
        ))

    # Recent transactions
    stmt = select(Transaction).where(Transaction.user_id == current_user.id).order_by(desc(Transaction.created_at)).limit(5)
    result = await db.execute(stmt)
    txs = result.scalars().all()
    
    recent_txs = [
        TransactionSummary(
            id=tx.id,
            onramp_status=tx.fiat_status,
            swap_status=tx.swap_status,
            fiat_amount=tx.fiat_amount,
            fiat_currency=tx.fiat_currency,
            target_token_symbol=tx.target_token_symbol,
            created_at=tx.created_at
        ) for tx in txs
    ]

    return Portfolio(
        total_value_usd=total_val_usd,
        total_value_local=total_val_usd * 1,
        change_24h_pct=0.0,
        holdings=holdings,
        recent_transactions=recent_txs
    )

@router.get("/transactions", response_model=List[TransactionSummary])
async def get_transactions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all user transactions with pagination.
    """
    stmt = select(Transaction).where(Transaction.user_id == current_user.id).order_by(desc(Transaction.created_at)).offset(offset).limit(limit)
    result = await db.execute(stmt)
    txs = result.scalars().all()
    
    return [
        TransactionSummary(
            id=tx.id,
            onramp_status=tx.fiat_status,
            swap_status=tx.swap_status,
            fiat_amount=tx.fiat_amount,
            fiat_currency=tx.fiat_currency,
            target_token_symbol=tx.target_token_symbol,
            created_at=tx.created_at
        ) for tx in txs
    ]
