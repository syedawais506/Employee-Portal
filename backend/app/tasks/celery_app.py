from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "employee_portal",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.email_tasks", "app.tasks.webhook_tasks", "app.tasks.digest_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "run-daily-digest": {
            "task": "run_daily_digest",
            "schedule": crontab(hour=8, minute=0),
        },
    },
)
