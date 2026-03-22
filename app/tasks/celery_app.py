from celery import Celery
from app.config import settings

celery_app = Celery(
    "fiatdex_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.swap_tasks", "app.tasks.price_tasks", "app.tasks.notification_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300, # 5 minutes
)

# Optional: Celery Beat configuration for periodic tasks
celery_app.conf.beat_schedule = {
    "refresh-price-cache-10s": {
        "task": "tasks.refresh_price_cache",
        "schedule": 10.0,
    },
    "check-price-alerts-60s": {
        "task": "tasks.check_price_alerts",
        "schedule": 60.0,
    },
}
