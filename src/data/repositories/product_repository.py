from datetime import datetime
from typing import Sequence

from sqlalchemy import select, update

from src.data.models import Product
from src.data.repositories.base_repository import BaseRepository


class ProductRepository(BaseRepository[Product]):
    def __init__(self, session):
        super().__init__(session, Product)

    async def create_many(self, products: Sequence[Product]) -> list[Product]:
        for p in products:
            self._session.add(p)
        await self._session.flush()
        return list(products)

    def add(self, product: Product) -> None:
        self._session.add(product)

    async def aggregate_by_batch(self, batch_id: int, at: datetime) -> int:
        """Помечает всю продукцию партии как агрегированную. Возвращает количество обновлённых строк."""
        result = await self._session.execute(
            update(Product)
            .where(Product.batch_id == batch_id, Product.is_aggregated == False)
            .values(is_aggregated=True, aggregated_at=at)
        )
        return result.rowcount or 0
