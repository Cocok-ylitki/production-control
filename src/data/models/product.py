from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.models import Base

if TYPE_CHECKING:
    from src.data.models.batch import Batch


class Product(Base):
    """Продукция (единица учёта в партии)."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    unique_code: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"), nullable=False, index=True)

    # Агрегация
    is_aggregated: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", index=True
    )
    aggregated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Метаданные
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Связи
    batch: Mapped["Batch"] = relationship("Batch", back_populates="products")

    __table_args__ = (
        Index("idx_product_batch_aggregated", "batch_id", "is_aggregated"),
    )
