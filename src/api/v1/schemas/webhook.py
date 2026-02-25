from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class WebhookCreate(BaseModel):
    url: str = Field(..., max_length=2048)
    events: List[str] = Field(..., min_length=1)
    secret_key: str = Field(..., max_length=255)
    retry_count: int = Field(default=3, ge=1, le=10)
    timeout: int = Field(default=10, ge=1, le=120)


class WebhookUpdate(BaseModel):
    is_active: bool | None = None


class WebhookResponse(BaseModel):
    id: int
    url: str
    events: List[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class WebhookListItem(BaseModel):
    id: int
    url: str
    events: List[str]
    is_active: bool

    model_config = {"from_attributes": True}


class WebhookListResponse(BaseModel):
    items: List[WebhookListItem]
    total: int


class WebhookDeliveryItem(BaseModel):
    id: int
    event_type: str
    status: str
    attempts: int
    response_status: int | None
    error_message: str | None
    created_at: datetime
    delivered_at: datetime | None

    model_config = {"from_attributes": True}


class WebhookDeliveryListResponse(BaseModel):
    items: List[WebhookDeliveryItem]
    total: int
