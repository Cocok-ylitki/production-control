from fastapi import APIRouter, HTTPException, Query

from src.api.v1.schemas.webhook import (
    WebhookCreate,
    WebhookDeliveryItem,
    WebhookDeliveryListResponse,
    WebhookListItem,
    WebhookListResponse,
    WebhookResponse,
    WebhookUpdate,
)
from src.core.dependencies import DbSession
from src.core.exceptions import NotFoundError
from src.data.repositories.webhook_repository import (
    WebhookDeliveryRepository,
    WebhookSubscriptionRepository,
)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("", status_code=201, response_model=WebhookResponse)
async def create_webhook(body: WebhookCreate, db: DbSession):
    repo = WebhookSubscriptionRepository(db)
    sub = await repo.create(
        url=body.url,
        events=body.events,
        secret_key=body.secret_key,
        retry_count=body.retry_count,
        timeout=body.timeout,
    )
    return WebhookResponse(
        id=sub.id,
        url=sub.url,
        events=sub.events,
        is_active=sub.is_active,
        created_at=sub.created_at,
    )


@router.get("", response_model=WebhookListResponse)
async def list_webhooks(db: DbSession):
    repo = WebhookSubscriptionRepository(db)
    items = await repo.list_all()
    return WebhookListResponse(
        items=[WebhookListItem.model_validate(s) for s in items],
        total=len(items),
    )


@router.patch("/{webhook_id}", response_model=WebhookListItem)
async def update_webhook(webhook_id: int, body: WebhookUpdate, db: DbSession):
    repo = WebhookSubscriptionRepository(db)
    sub = await repo.update_subscription(webhook_id, is_active=body.is_active)
    if sub is None:
        raise HTTPException(404, "Webhook subscription not found")
    return WebhookListItem.model_validate(sub)


@router.delete("/{webhook_id}", status_code=204)
async def delete_webhook(webhook_id: int, db: DbSession):
    repo = WebhookSubscriptionRepository(db)
    deleted = await repo.delete_subscription(webhook_id)
    if not deleted:
        raise HTTPException(404, "Webhook subscription not found")


@router.get("/{webhook_id}/deliveries", response_model=WebhookDeliveryListResponse)
async def list_webhook_deliveries(
    webhook_id: int,
    db: DbSession,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    sub_repo = WebhookSubscriptionRepository(db)
    sub = await sub_repo.get_by_id(webhook_id)
    if sub is None:
        raise HTTPException(404, "Webhook subscription not found")
    delivery_repo = WebhookDeliveryRepository(db)
    items, total = await delivery_repo.list_by_subscription(
        webhook_id, offset=offset, limit=limit
    )
    return WebhookDeliveryListResponse(
        items=[WebhookDeliveryItem.model_validate(d) for d in items],
        total=total,
    )
