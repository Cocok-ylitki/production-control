from datetime import datetime, timezone

from sqlalchemy import select, update

from src.celery_app import celery_app
from src.core.database_sync import get_sync_session
from src.data.models import Batch
from src.core.config import get_settings
from src.storage.minio_service import list_objects_older_than, delete_objects


@celery_app.task
def auto_close_expired_batches():
    """
    Закрывает партии, у которых shift_end < now().
    Запускается: каждый день в 01:00.
    """
    from src.tasks.webhooks import notify_batch_closed

    now = datetime.now(timezone.utc)
    batch_ids_to_notify = []
    with get_sync_session() as session:
        ids_result = session.execute(
            select(Batch.id).where(Batch.is_closed.is_(False), Batch.shift_end < now)
        )
        batch_ids_to_notify = [r[0] for r in ids_result.all()]
        if batch_ids_to_notify:
            session.execute(
                update(Batch)
                .where(Batch.id.in_(batch_ids_to_notify))
                .values(is_closed=True, closed_at=now)
            )
    for batch_id in batch_ids_to_notify:
        notify_batch_closed.delay(batch_id)
    return {"closed": len(batch_ids_to_notify)}


@celery_app.task
def cleanup_old_files():
    """
    Удаляет файлы старше 30 дней из MinIO (reports, imports, exports).
    Запускается: каждый день в 02:00.
    """
    settings = get_settings()
    to_delete = []
    for bucket in (
        settings.minio_bucket_reports,
        settings.minio_bucket_imports,
        settings.minio_bucket_exports,
    ):
        to_delete.extend(list_objects_older_than(bucket, prefix="", days=30))
    delete_objects(to_delete)
    return {"deleted": len(to_delete)}


@celery_app.task
def update_cached_statistics():
    """
    Обновляет кэшированную статистику в Redis.
    Запускается: каждые 5 минут.
    """
    from src.core.cache import set_cached_statistics

    with get_sync_session() as session:
        from sqlalchemy import func
        from src.data.models import Product

        total_batches = session.execute(select(func.count(Batch.id))).scalar() or 0
        closed_batches = session.execute(select(func.count(Batch.id)).where(Batch.is_closed == True)).scalar() or 0
        total_products = session.execute(select(func.count(Product.id))).scalar() or 0
        aggregated_products = session.execute(
            select(func.count(Product.id)).where(Product.is_aggregated == True)
        ).scalar() or 0

    stats = {
        "total_batches": total_batches,
        "closed_batches": closed_batches,
        "total_products": total_products,
        "aggregated_products": aggregated_products,
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }
    set_cached_statistics(stats)
    return stats
