from datetime import date, datetime
from typing import List

from pydantic import BaseModel, Field


# --- Request: создание партий (тело от внешней системы) ---
class BatchCreateItem(BaseModel):
    СтатусЗакрытия: bool = False
    ПредставлениеЗаданияНаСмену: str
    РабочийЦентр: str
    Смена: str
    Бригада: str
    НомерПартии: int
    ДатаПартии: date
    Номенклатура: str
    КодЕКН: str
    ИдентификаторРЦ: str
    ДатаВремяНачалаСмены: datetime
    ДатаВремяОкончанияСмены: datetime


class BatchUpdate(BaseModel):
    is_closed: bool | None = None


class ProductInBatchResponse(BaseModel):
    id: int
    unique_code: str
    is_aggregated: bool
    aggregated_at: datetime | None

    model_config = {"from_attributes": True}


class BatchResponse(BaseModel):
    id: int
    is_closed: bool
    batch_number: int
    batch_date: date
    products: List[ProductInBatchResponse]

    model_config = {"from_attributes": True}


class BatchListItem(BaseModel):
    id: int
    is_closed: bool
    closed_at: datetime | None
    task_description: str
    work_center_id: int
    shift: str
    team: str
    batch_number: int
    batch_date: date
    nomenclature: str
    ekn_code: str
    shift_start: datetime
    shift_end: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BatchListResponse(BaseModel):
    items: List[BatchListItem]
    offset: int
    limit: int
