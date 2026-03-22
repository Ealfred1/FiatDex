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

        # 2. Verify INJ balance (poll for up to 60 seconds)
        # In a real scenario, we'd poll Injective node
        # await asyncio.sleep(5) # Simulation
        
        try:
            # 3. Execute spot swap
            # Note: We need the user's private key for automated swaps.
            # In a non-custodial setup, the user might sign a pre-authorization or 
            # we use a temporary session key if authorized.
            # For this build, we'll assume a 'system' or 'user-proxy' key is managed or 
            # we're simulating the broadcast.
            
            # price = await ... # Get current market price
            price = Decimal("1.0") # Placeholder
            
            swap_result = await injective_service.execute_spot_swap(
                private_key="...", # Injected or managed securely
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
            
            await session.commit()
            
            # 5. Trigger notification
            # from app.tasks.notification_tasks import send_notification_task
            # send_notification_task.delay(tx.user_id, "swap_confirmed", ...)
            
            return f"Swap executed for TX {transaction_id}"
            
        except Exception as e:
            tx.swap_status = "failed"
            await session.commit()
            return f"Swap failed for TX {transaction_id}: {str(e)}"

from datetime import datetime
