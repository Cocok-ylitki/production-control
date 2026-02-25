from sqlalchemy import select

from src.data.models import WorkCenter
from src.data.repositories.base_repository import BaseRepository


class WorkCenterRepository(BaseRepository[WorkCenter]):
    def __init__(self, session):
        super().__init__(session, WorkCenter)

    async def get_by_identifier(self, identifier: str) -> WorkCenter | None:
        result = await self._session.execute(
            select(WorkCenter).where(WorkCenter.identifier == identifier)
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, identifier: str, name: str) -> WorkCenter:
        wc = await self.get_by_identifier(identifier)
        if wc is not None:
            return wc
        wc = WorkCenter(identifier=identifier, name=name)
        self._session.add(wc)
        await self._session.flush()
        return wc
