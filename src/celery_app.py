from celery import Celery
from celery.schedules import crontab

from src.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "production_control",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "src.tasks.aggregation",
        "src.tasks.reports",
        "src.tasks.imports",
        "src.tasks.exports",
        "src.tasks.scheduled",
        "src.tasks.webhooks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    result_extended=True,
    beat_schedule={
        "auto-close-expired-batches": {
            "task": "src.tasks.scheduled.auto_close_expired_batches",
            "schedule": crontab(hour=1, minute=0),
        },
        "cleanup-old-files": {
            "task": "src.tasks.scheduled.cleanup_old_files",
            "schedule": crontab(hour=2, minute=0),
        },
        "update-statistics": {
            "task": "src.tasks.scheduled.update_cached_statistics",
            "schedule": crontab(minute="*/5"),
        },
        "retry-failed-webhooks": {
            "task": "src.tasks.webhooks.retry_failed_webhooks",
            "schedule": crontab(minute="*/15"),
        },
    },
)
