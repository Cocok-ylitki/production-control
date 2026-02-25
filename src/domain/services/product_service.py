from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError
from src.data.models import Product
from src.data.repositories.batch_repository import BatchRepository
from src.data.repositories.product_repository import ProductRepository
from src.utils.id_generator import generate_unique_code


class ProductService:
    def __init__(self, session: AsyncSession):
        self._session = session
        self._product_repo = ProductRepository(session)
        self._batch_repo = BatchRepository(session)

    async def add_products(self, batch_id: int, unique_codes: list[str] | None = None) -> list[Product]:
        batch = await self._batch_repo.get_by_id(batch_id)
        if batch is None:
            raise NotFoundError("Batch not found")
        if unique_codes:
            codes = unique_codes
        else:
            codes = [generate_unique_code()]
        products = [Product(batch_id=batch_id, unique_code=code) for code in codes]
        return await self._product_repo.create_many(products)

    async def aggregate_batch(self, batch_id: int) -> int:
        batch = await self._batch_repo.get_by_id(batch_id)
        if batch is None:
            raise NotFoundError("Batch not found")
        at = datetime.utcnow()
        return await self._product_repo.aggregate_by_batch(batch_id, at)
