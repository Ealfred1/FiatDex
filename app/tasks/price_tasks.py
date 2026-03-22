import asyncio
import logging
from sqlalchemy import select
from datetime import datetime, timezone
from app.tasks.celery_app import celery_app
from app.services.injective_service import injective_service
from app.services.price_service import price_service
from app.core.database import AsyncSessionLocal
from app.models.alert import PriceAlert
from app.models.user import User

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.refresh_price_cache")
def refresh_price_cache():
    """
    Runs periodically to refresh token prices in Redis.
    """
    logger.info("Refreshing price cache")
    asyncio.run(injective_service.get_all_market_summaries())
    logger.info("Price cache refreshed")

@celery_app.task(name="tasks.check_price_alerts")
def check_price_alerts():
    """
    Check all active price alerts and trigger notifications.
    """
    asyncio.run(_check_alerts_async())

async def _check_alerts_async():
    async with AsyncSessionLocal() as session:
        # 1. Fetch all active alerts
        stmt = select(PriceAlert).where(PriceAlert.is_active == True)
        result = await session.execute(stmt)
        alerts = result.scalars().all()
        logger.info(f"Checking {len(alerts)} active price alerts")
        
        for alert in alerts:
            current_price = await price_service.get_token_price_usd(alert.token_denom)
            if not current_price:
                continue

            triggered = False
            if alert.condition == "above" and current_price >= alert.target_price_usd:
                triggered = True
            elif alert.condition == "below" and current_price <= alert.target_price_usd:
                triggered = True

            if triggered:
                logger.info(f"Price alert triggered: {alert.token_symbol} {alert.condition} ${alert.target_price_usd} (now ${current_price})")
                # 2. Mark as triggered
                alert.is_active = False
                alert.triggered_at = datetime.now(timezone.utc)
                await session.commit()

                # 3. Get user push token
                user_stmt = select(User).where(User.id == alert.user_id)
                user_res = await session.execute(user_stmt)
                user = user_res.scalar_one_or_none()
                
                if user and user.expo_push_token:
                    from app.tasks.notification_tasks import send_price_alert_task
                    send_price_alert_task.delay(
                        user.expo_push_token,
                        alert.token_symbol,
                        str(alert.target_price_usd),
                        str(current_price),
                        alert.condition
                    )
