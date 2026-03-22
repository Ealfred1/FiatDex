from decimal import Decimal
from uuid import UUID
import asyncio
from sqlalchemy import select

from app.tasks.celery_app import celery_app
from app.services.injective_service import injective_service
from app.core.database import AsyncSessionLocal
from app.models.transaction import Transaction

# To avoid circular imports, we'd typically use a factory or internal imports
# or move some logic to a more central place. 

from app.models.holding import Holding

@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    name="tasks.execute_swap"
)
def execute_swap_task(
    self,
    transaction_id: str,
    inj_amount: str,
    target_market_id: str,
    wallet_address: str,
    slippage_tolerance: float,
):
    """
    Celery task for background swap execution.
    Runs asynchronously after fiat onramp completes.
    """
    # Use asyncio.run to execute async code in synchronous Celery worker
    return asyncio.run(_execute_swap_async(
        transaction_id, inj_amount, target_market_id, wallet_address, slippage_tolerance
    ))

async def _execute_swap_async(
    transaction_id: str,
    inj_amount: str,
    target_market_id: str,
    wallet_address: str,
    slippage_tolerance: float,
):
    async with AsyncSessionLocal() as session:
        # 1. Load transaction from DB
        stmt = select(Transaction).where(Transaction.id == UUID(transaction_id))
        result = await session.execute(stmt)
        tx = result.scalar_one_or_none()
        
        if not tx:
            return f"Transaction {transaction_id} not found"

        try:
            # 3. Execute spot swap
            # (Simulation/Placeholder logic)
            price = Decimal("1.0") # Placeholder
            
            swap_result = await injective_service.execute_spot_swap(
                private_key="...", 
                market_id=target_market_id,
                quantity=Decimal(inj_amount),
                price=price,
                slippage_tolerance=slippage_tolerance
            )
            
            # 4. Update transaction
            tx.swap_tx_hash = swap_result["tx_hash"]
            tx.swap_status = "confirmed"
            tx.swap_amount_received = swap_result["filled_quantity"]
            tx.inj_amount = Decimal(inj_amount)
            tx.inj_received_at = datetime.utcnow()
            
            # 5. Update Holdings
            await _update_user_holding(
                session, 
                tx.user_id, 
                tx.target_denom, 
                tx.target_token_symbol, 
                tx.swap_amount_received, 
                price # Using execution price
            )
            
            await session.commit()
            return f"Swap executed for TX {transaction_id}"
            
        except Exception as e:
            tx.swap_status = "failed"
            await session.commit()
            return f"Swap failed for TX {transaction_id}: {str(e)}"

async def _update_user_holding(session, user_id, denom, symbol, amount, price_usd):
    stmt = select(Holding).where(
        Holding.user_id == user_id,
        Holding.token_denom == denom
    )
    res = await session.execute(stmt)
    holding = res.scalar_one_or_none()
    
    if not holding:
        holding = Holding(
            user_id=user_id,
            token_denom=denom,
            token_symbol=symbol,
            amount=amount,
            avg_price_usd=price_usd,
            total_cost_usd=amount * price_usd
        )
        session.add(holding)
    else:
        new_total_cost = holding.total_cost_usd + (amount * price_usd)
        new_amount = holding.amount + amount
        if new_amount > 0:
            holding.avg_price_usd = new_total_cost / new_amount
        holding.total_cost_usd = new_total_cost
        holding.amount = new_amount

from datetime import datetime
