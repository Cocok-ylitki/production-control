"""
Конфиг расписания Celery Beat.
Используется в src.celery_app через beat_schedule (задано там же).
Здесь — эталон для справки и при необходимости выноса в отдельный конфиг.
"""
from celery.schedules import crontab

beat_schedule = {
    # Закрытие просроченных партий - каждый день в 01:00
    "auto-close-expired-batches": {
        "task": "src.tasks.scheduled.auto_close_expired_batches",
        "schedule": crontab(hour=1, minute=0),
    },
    # Очистка старых файлов - каждый день в 02:00
    "cleanup-old-files": {
        "task": "src.tasks.scheduled.cleanup_old_files",
        "schedule": crontab(hour=2, minute=0),
    },
    # Обновление статистики - каждые 5 минут
    "update-statistics": {
        "task": "src.tasks.scheduled.update_cached_statistics",
        "schedule": crontab(minute="*/5"),
    },
    # Повторная отправка webhooks - каждые 15 минут
    "retry-failed-webhooks": {
        "task": "src.tasks.webhooks.retry_failed_webhooks",
        "schedule": crontab(minute="*/15"),
    },
}
