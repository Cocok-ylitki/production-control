from datetime import datetime, timezone

from sqlalchemy import select

from src.celery_app import celery_app
from src.core.database_sync import get_sync_session
from src.data.models import Batch, Product
from src.tasks.webhook_events import payload_product_aggregated
from src.tasks.webhooks import notify_webhook_event


@celery_app.task(bind=True, max_retries=3)
def aggregate_products_batch(
    self,
    batch_id: int,
    unique_codes: list[str],
    user_id: int | None = None,
):
    """
    Асинхронная массовая аггрегация продукции.
    Используется когда нужно аггрегировать >100 единиц продукции.
    """
    total = len(unique_codes)
    aggregated = 0
    errors: list[dict] = []
    at = datetime.now(timezone.utc)
    aggregated_at_str = at.strftime("%Y-%m-%dT%H:%M:%SZ")
    aggregated_for_webhooks: list[tuple[str, int]] = []  # (unique_code, batch_number)

    with get_sync_session() as session:
        batch = session.execute(select(Batch).where(Batch.id == batch_id)).scalars().one_or_none()
        batch_number = batch.batch_number if batch else 0
        for i, code in enumerate(unique_codes):
            result = session.execute(
                select(Product).where(
                    Product.batch_id == batch_id,
                    Product.unique_code == code,
                )
            )
            product = result.scalars().one_or_none()
            if product is None:
                errors.append({"code": code, "reason": "not found"})
                continue
            if product.is_aggregated:
                errors.append({"code": code, "reason": "already aggregated"})
                continue
            product.is_aggregated = True
            product.aggregated_at = at
            aggregated += 1
            aggregated_for_webhooks.append((code, batch_number))
            session.flush()

            current = i + 1
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": current,
                    "total": total,
                    "progress": int(100 * current / total) if total else 0,
                },
            )

    for unique_code, bnum in aggregated_for_webhooks:
        payload = payload_product_aggregated(
            unique_code=unique_code,
            batch_id=batch_id,
            batch_number=bnum,
            aggregated_at=aggregated_at_str,
        )
        notify_webhook_event.delay(payload)

    from src.core.cache import invalidate_on_aggregation_sync
    invalidate_on_aggregation_sync(batch_id)

    return {
        "success": True,
        "total": total,
        "aggregated": aggregated,
        "failed": len(errors),
        "errors": errors,
    }
