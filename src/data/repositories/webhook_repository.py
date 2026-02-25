from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models import WebhookDelivery, WebhookSubscription
from src.data.repositories.base_repository import BaseRepository


class WebhookSubscriptionRepository(BaseRepository[WebhookSubscription]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, WebhookSubscription)

    async def create(
        self,
        *,
        url: str,
        events: list[str],
        secret_key: str,
        retry_count: int = 3,
        timeout: int = 10,
    ) -> WebhookSubscription:
        sub = WebhookSubscription(
            url=url,
            events=events,
            secret_key=secret_key,
            retry_count=retry_count,
            timeout=timeout,
        )
        self._session.add(sub)
        await self._session.flush()
        return sub

    async def list_all(self) -> list[WebhookSubscription]:
        result = await self._session.execute(
            select(WebhookSubscription).order_by(WebhookSubscription.id)
        )
        return list(result.scalars().all())

    async def update_subscription(
        self,
        webhook_id: int,
        *,
        is_active: bool | None = None,
    ) -> WebhookSubscription | None:
        sub = await self.get_by_id(webhook_id)
        if sub is None:
            return None
        if is_active is not None:
            sub.is_active = is_active
        await self._session.flush()
        await self._session.refresh(sub)
        return sub

    async def delete_subscription(self, webhook_id: int) -> bool:
        sub = await self.get_by_id(webhook_id)
        if sub is None:
            return False
        await self._session.delete(sub)
        await self._session.flush()
        return True


class WebhookDeliveryRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_by_subscription(
        self,
        subscription_id: int,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[WebhookDelivery], int]:
        total_result = await self._session.execute(
            select(func.count(WebhookDelivery.id)).where(
                WebhookDelivery.subscription_id == subscription_id
            )
        )
        total = total_result.scalar() or 0
        result = await self._session.execute(
            select(WebhookDelivery)
            .where(WebhookDelivery.subscription_id == subscription_id)
            .order_by(WebhookDelivery.id.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list(result.scalars().all())
        return items, total
