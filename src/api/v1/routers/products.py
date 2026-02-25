from fastapi import APIRouter, HTTPException

from src.api.v1.schemas.product import ProductCreate, ProductResponse
from src.core.dependencies import DbSession
from src.core.exceptions import NotFoundError
from src.domain.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["products"])


@router.post("", status_code=201)
async def create_products(body: ProductCreate, db: DbSession):
    service = ProductService(db)
    try:
        products = await service.add_products(
            batch_id=body.batch_id,
            unique_codes=body.unique_codes if body.unique_codes else None,
        )
    except NotFoundError as e:
        raise HTTPException(404, e.message)
    if len(products) == 1:
        return ProductResponse.model_validate(products[0])
    return [ProductResponse.model_validate(p) for p in products]
