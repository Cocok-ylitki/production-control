from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    batch_id: int
    unique_codes: List[str] | None = Field(default=None, description="Коды; если пусто — создаётся одна запись с сгенерированным кодом")


class ProductResponse(BaseModel):
    id: int
    unique_code: str
    batch_id: int
    is_aggregated: bool
    aggregated_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AggregateResponse(BaseModel):
    batch_id: int
    aggregated_count: int
