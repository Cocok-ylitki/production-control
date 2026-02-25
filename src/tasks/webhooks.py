import json
from datetime import datetime, timezone

import requests
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.celery_app import celery_app
from src.core.database_sync import get_sync_session
from src.data.models import WebhookDelivery, WebhookSubscription
from src.utils.hmac_utils import sign_payload


def dispatch_webhook_event(payload: dict) -> None:
    """
    Находит подписки на event из payload, создаёт WebhookDelivery и отправляет запросы.
    payload: { "event": str, "data": ..., "timestamp": str }
    """
    event_type = payload.get("event")
    if not event_type:
        return
    with get_sync_session() as session:
        result = session.execute(
            select(WebhookSubscription).where(
                WebhookSubscription.is_active == True,
                WebhookSubscription.events.contains([event_type]),
            )
        )
        subscriptions = list(result.scalars().all())
        for sub in subscriptions:
            delivery = WebhookDelivery(
                subscription_id=sub.id,
                event_type=event_type,
                payload=payload,
                status="pending",
                attempts=0,
            )
            session.add(delivery)
            session.flush()
            session.refresh(delivery)
            sub_for_send = sub
            delivery_for_send = delivery
            # отправить в том же цикле (subscription уже в session)
            status_code, body, err = _send_webhook_sync(delivery_for_send, sub_for_send)
            delivery_for_send.attempts = 1
            delivery_for_send.last_attempt_at = datetime.now(timezone.utc)
            delivery_for_send.response_status = status_code
            delivery_for_send.response_body = body
            delivery_for_send.error_message = err
            if status_code and 200 <= status_code < 300:
                delivery_for_send.status = "success"
                delivery_for_send.delivered_at = datetime.now(timezone.utc)
            else:
                delivery_for_send.status = "failed"
            session.flush()


def _send_webhook_sync(
    delivery: WebhookDelivery,
    subscription: WebhookSubscription,
) -> tuple[int | None, str | None, str | None]:
    """Отправляет один webhook (subscription передаётся явно для использования вне session)."""
    url = subscription.url
    payload = delivery.payload
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    signature = sign_payload(subscription.secret_key, body)
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": signature,
    }
    try:
        resp = requests.post(
            url,
            data=body,
            headers=headers,
            timeout=subscription.timeout,
        )
        return resp.status_code, (resp.text[:2000] if resp.text else None), None
    except Exception as e:
        return None, None, str(e)[:500]


def _send_webhook(delivery: WebhookDelivery) -> tuple[int | None, str | None, str | None]:
    """
    Отправляет один webhook. Возвращает (response_status, response_body, error_message).
    """
    sub = delivery.subscription
    url = sub.url
    payload = delivery.payload
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    signature = sign_payload(sub.secret_key, body)
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": signature,
    }
    try:
        resp = requests.post(
            url,
            data=body,
            headers=headers,
            timeout=sub.timeout,
        )
        return resp.status_code, (resp.text[:2000] if resp.text else None), None
    except Exception as e:
        return None, None, str(e)[:500]


@celery_app.task
def retry_failed_webhooks():
    """
    Повторная отправка неудачных webhook delivery.
    Запускается: каждые 15 минут.
    """
    from sqlalchemy.orm import selectinload

    with get_sync_session() as session:
        result = session.execute(
            select(WebhookDelivery)
            .join(WebhookSubscription, WebhookDelivery.subscription_id == WebhookSubscription.id)
            .where(
                WebhookDelivery.status == "failed",
                WebhookDelivery.attempts < WebhookSubscription.retry_count,
                WebhookSubscription.is_active == True,
            )
            .options(selectinload(WebhookDelivery.subscription))
        )
        deliveries = list(result.scalars().unique().all())

        retried = 0
        now = datetime.now(timezone.utc)
        for d in deliveries:
            sub = d.subscription
            if d.attempts >= sub.retry_count or not sub.is_active:
                continue
            # Exponential backoff: следующая попытка не раньше чем через 60*2^attempts сек (макс 1 час)
            backoff_seconds = min(3600, 60 * (2 ** d.attempts))
            if d.last_attempt_at:
                from datetime import timedelta
                next_retry = d.last_attempt_at.replace(tzinfo=timezone.utc) if not d.last_attempt_at.tzinfo else d.last_attempt_at
                if (now - next_retry).total_seconds() < backoff_seconds:
                    continue

            status_code, body, err = _send_webhook(d)
            d.attempts += 1
            d.last_attempt_at = now
            d.response_status = status_code
            d.response_body = body
            d.error_message = err
            if status_code and 200 <= status_code < 300:
                d.status = "success"
                d.delivered_at = now
            else:
                d.status = "failed"
            session.flush()
            retried += 1

    return {"retried": retried}


@celery_app.task
def notify_webhook_event(payload: dict) -> None:
    """
    Ставит в очередь отправку webhook по событию.
    payload: { "event": str, "data": ..., "timestamp": str }
    """
    dispatch_webhook_event(payload)


@celery_app.task
def notify_batch_closed(batch_id: int) -> None:
    """Загружает партию с продукцией, считает статистику и отправляет событие batch_closed."""
    from sqlalchemy.orm import selectinload
    from src.data.models import Batch
    from src.tasks.webhook_events import payload_batch_closed

    with get_sync_session() as session:
        batch = session.execute(
            select(Batch)
            .where(Batch.id == batch_id)
            .options(selectinload(Batch.products))
        ).scalars().one_or_none()
        if not batch or not batch.is_closed or not batch.closed_at:
            return
        total = len(batch.products)
        aggregated = sum(1 for p in batch.products if p.is_aggregated)
        rate = (100.0 * aggregated / total) if total else 0.0
        closed_at_str = (
            batch.closed_at.strftime("%Y-%m-%dT%H:%M:%SZ")
            if getattr(batch.closed_at, "tzinfo", None)
            else (batch.closed_at.isoformat() + "Z")
        )
        payload = payload_batch_closed(
            id=batch_id,
            batch_number=batch.batch_number,
            closed_at=closed_at_str,
            total_products=total,
            aggregated=aggregated,
            aggregation_rate=rate,
        )
    dispatch_webhook_event(payload)
