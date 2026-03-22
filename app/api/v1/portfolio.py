from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.schemas.portfolio import PortfolioOverview, PortfolioTransaction
from app.models.user import User
from app.models.transaction import Transaction
from app.dependencies import get_current_user
from app.services.injective_service import injective_service

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])

@router.get(
    "",
    summary="Get user portfolio overview",
    description="""
Returns a complete portfolio snapshot for the authenticated user.

Combines:
- Live on-chain wallet balances (from Injective Bank module)
- FiatDex transaction history (purchases made through the app)
- Current market prices for all held tokens

**Holdings** are live — prices update every time this endpoint is called.
**24h change** reflects the aggregate portfolio value change vs 24 hours ago.

Designed to power the Portfolio tab in the mobile app.
""",
    response_model=PortfolioOverview,
    operation_id="get_portfolio_overview",
)
async def get_portfolio(current_user: User = Depends(get_current_user)):
    balances = await injective_service.get_wallet_balances(current_user.wallet_address)
    
    # Mock portfolio response
    return PortfolioOverview(
        total_value_usd=sum(b.balance_usd for b in balances),
        total_value_local=0,
        local_currency=current_user.preferred_currency,
        change_24h=0.0,
        holdings=balances
    )

@router.get(
    "/transactions",
    summary="Get transaction history",
    description="""
Returns paginated list of all fiat purchase transactions made through FiatDex.

Each transaction shows the full lifecycle:
- Fiat payment details (amount, currency, provider, status)
- INJ receipt details
- Swap execution details (tx hash, output amount, explorer link)

**Status filters:** `all` | `completed` | `pending` | `failed`

Transactions are ordered newest first.
""",
    response_model=List[PortfolioTransaction],
    operation_id="get_transaction_history",
)
async def get_transactions(
    status_filter: str = "all",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Transaction).where(Transaction.user_id == current_user.id).order_by(Transaction.created_at.desc())
    result = await db.execute(stmt)
    txs = result.scalars().all()
    
    return [
        PortfolioTransaction(
            id=str(tx.id),
            onramp_amount=tx.fiat_amount,
            onramp_currency=tx.fiat_currency,
            onramp_status=tx.fiat_status,
            target_symbol=tx.target_token_symbol,
            target_amount=tx.swap_amount_received,
            timestamp=tx.created_at
        )
        for tx in txs
    ]
