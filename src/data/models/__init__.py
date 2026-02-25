from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей."""

    pass


from src.data.models.work_center import WorkCenter
from src.data.models.batch import Batch
from src.data.models.product import Product
from src.data.models.webhook import WebhookSubscription, WebhookDelivery

__all__ = [
    "Base",
    "WorkCenter",
    "Batch",
    "Product",
    "WebhookSubscription",
    "WebhookDelivery",
]
