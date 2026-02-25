from datetime import date, datetime
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.schemas.batch import BatchCreateItem
from src.core.exceptions import NotFoundError
from src.data.models import Batch
from src.data.repositories.batch_repository import BatchRepository
from src.data.repositories.work_center_repository import WorkCenterRepository


class BatchService:
    def __init__(self, session: AsyncSession):
        self._session = session
        self._batch_repo = BatchRepository(session)
        self._work_center_repo = WorkCenterRepository(session)

    async def create_batches(self, items: List[BatchCreateItem]) -> List[Batch]:
        batches: List[Batch] = []
        for item in items:
            wc = await self._work_center_repo.get_or_create(
                identifier=item.ИдентификаторРЦ,
                name=item.РабочийЦентр,
            )
            batch = Batch(
                is_closed=item.СтатусЗакрытия,
                closed_at=datetime.utcnow() if item.СтатусЗакрытия else None,
                task_description=item.ПредставлениеЗаданияНаСмену,
                work_center_id=wc.id,
                shift=item.Смена,
                team=item.Бригада,
                batch_number=item.НомерПартии,
                batch_date=item.ДатаПартии,
                nomenclature=item.Номенклатура,
                ekn_code=item.КодЕКН,
                shift_start=item.ДатаВремяНачалаСмены,
                shift_end=item.ДатаВремяОкончанияСмены,
            )
            self._batch_repo.add(batch)
            batches.append(batch)
        await self._session.flush()
        return batches

    async def get_by_id(self, batch_id: int) -> Batch:
        batch = await self._batch_repo.get_by_id_with_products(batch_id)
        if batch is None:
            raise NotFoundError("Batch not found")
        return batch

    async def update_batch(
        self,
        batch_id: int,
        *,
        is_closed: bool | None = None,
    ) -> Batch:
        batch = await self._batch_repo.get_by_id(batch_id)
        if batch is None:
            raise NotFoundError("Batch not found")
        if is_closed is not None:
            batch.is_closed = is_closed
            if is_closed:
                batch.closed_at = datetime.utcnow()
            else:
                batch.closed_at = None
        await self._session.flush()
        await self._session.refresh(batch)
        return batch

    async def list_batches(
        self,
        *,
        is_closed: bool | None = None,
        batch_number: int | None = None,
        batch_date: date | None = None,
        work_center_id: int | None = None,
        shift: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> List[Batch]:
        return await self._batch_repo.list_filtered(
            is_closed=is_closed,
            batch_number=batch_number,
            batch_date=batch_date,
            work_center_id=work_center_id,
            shift=shift,
            offset=offset,
            limit=limit,
        )
