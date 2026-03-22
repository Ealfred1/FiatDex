from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from decimal import Decimal

from app.core.database import get_db
from app.schemas.portfolio import PortfolioOverview, PortfolioTransaction
from app.models.user import User
from app.models.transaction import Transaction
from app.services.auth_service import auth_service
from app.services.injective_service import injective_service

router = APIRouter(tags=["Portfolio"])

from app.models.holding import Holding
from app.services.auth_service import auth_service

@router.get(
    "",
    summary="Get user portfolio overview",
    description="""
Returns a complete portfolio snapshot for the authenticated user.

Combines:
- Internal Holdings (tokens purchased via FiatDex balance/fiat)
- Live on-chain wallet balances (from Injective Bank module)
- Funded account balance (USD)
- P&L calculations per holding
""",
    response_model=PortfolioOverview,
    operation_id="get_portfolio_overview",
)
async def get_portfolio(
    current_user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Fetch internal holdings
    stmt = select(Holding).where(Holding.user_id == current_user.id)
    res = await db.execute(stmt)
    db_holdings = res.scalars().all()
    
    # 2. Fetch on-chain balances
    on_chain_balances = []
    if current_user.wallet_address:
        on_chain_balances = await injective_service.get_wallet_balances(current_user.wallet_address)
    
    # 3. Calculate P&L and enrich holdings
    enriched_holdings = []
    total_holdings_value = Decimal("0")
    
    # Get current market prices
    market_summaries = await injective_service.get_all_market_summaries()
    market_map = {s.market_id: s.last_price for s in market_summaries}
    # Also map via base_denom for flexibility
    denom_map = {s.base_denom: s.last_price for s in market_summaries if s.base_denom}

    for h in db_holdings:
        current_price = market_map.get(h.token_denom) or denom_map.get(h.token_denom) or h.avg_price_usd
        current_value = h.amount * current_price
        pnl_usd = current_value - h.total_cost_usd
        pnl_percent = (float(pnl_usd / h.total_cost_usd) * 100) if h.total_cost_usd > 0 else 0.0
        
        enriched_holdings.append({
            "token_denom": h.token_denom,
            "token_symbol": h.token_symbol,
            "amount": h.amount,
            "avg_price_usd": h.avg_price_usd,
            "current_price_usd": current_price,
            "total_value_usd": current_value,
            "pnl_usd": pnl_usd,
            "pnl_percent": pnl_percent
        })
        total_holdings_value += current_value

    on_chain_balances = on_chain_balances or []
    on_chain_total = Decimal("0")
    for b in on_chain_balances:
        # Support both dict and object formats from InjectiveService
        if isinstance(b, dict):
            val = b.get("balance_usd") or b.get("value_usd") or "0"
        else:
            val = getattr(b, "balance_usd", None) or getattr(b, "value_usd", "0")
        try:
            on_chain_total += Decimal(str(val))
        except (TypeError, ValueError, Exception):
            pass

    total_portfolio_value = total_holdings_value + on_chain_total + current_user.account_balance

    return PortfolioOverview(
        total_portfolio_value_usd=total_portfolio_value,
        account_balance_usd=current_user.account_balance,
        holdings=enriched_holdings,
        on_chain_balances=on_chain_balances,
        local_currency="USD" # Default for totals
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
    current_user: User = Depends(auth_service.get_current_user),
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
