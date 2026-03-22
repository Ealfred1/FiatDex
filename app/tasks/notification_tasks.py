import asyncio
from decimal import Decimal
from app.tasks.celery_app import celery_app
from app.services.notification_service import notification_service

@celery_app.task(name="tasks.send_price_alert")
def send_price_alert_task(expo_token, symbol, target, current, condition):
    asyncio.run(notification_service.send_price_alert(
        expo_token, symbol, Decimal(target), Decimal(current), condition
    ))

@celery_app.task(name="tasks.send_swap_confirmed")
def send_swap_confirmed_task(expo_token, symbol, amount, tx_hash):
    asyncio.run(notification_service.send_swap_confirmed(
        expo_token, symbol, Decimal(amount), tx_hash
    ))

@celery_app.task(name="tasks.send_swap_failed")
def send_swap_failed_task(expo_token, symbol, reason):
    asyncio.run(notification_service.send_swap_failed(
        expo_token, symbol, reason
    ))
