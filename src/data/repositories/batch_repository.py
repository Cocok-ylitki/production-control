from datetime import date
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.data.models import Batch
from src.data.repositories.base_repository import BaseRepository


class BatchRepository(BaseRepository[Batch]):
    def __init__(self, session):
        super().__init__(session, Batch)

    async def get_by_id_with_products(self, batch_id: int) -> Batch | None:
        result = await self._session.execute(
            select(Batch)
            .where(Batch.id == batch_id)
            .options(selectinload(Batch.products))
        )
        return result.scalar_one_or_none()

    async def create_many(self, batches: Sequence[Batch]) -> list[Batch]:
        for b in batches:
            self._session.add(b)
        await self._session.flush()
        return list(batches)

    def add(self, batch: Batch) -> None:
        self._session.add(batch)

    async def list_filtered(
        self,
        *,
        is_closed: bool | None = None,
        batch_number: int | None = None,
        batch_date: date | None = None,
        work_center_id: int | None = None,
        shift: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Batch]:
        q = select(Batch).options(selectinload(Batch.products))
        if is_closed is not None:
            q = q.where(Batch.is_closed == is_closed)
        if batch_number is not None:
            q = q.where(Batch.batch_number == batch_number)
        if batch_date is not None:
            q = q.where(Batch.batch_date == batch_date)
        if work_center_id is not None:
            q = q.where(Batch.work_center_id == work_center_id)
        if shift is not None:
            q = q.where(Batch.shift == shift)
        q = q.offset(offset).limit(limit).order_by(Batch.id.desc())
        result = await self._session.execute(q)
        return list(result.scalars().all())
