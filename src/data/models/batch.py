from datetime import date, datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.models import Base

if TYPE_CHECKING:
    from src.data.models.product import Product
    from src.data.models.work_center import WorkCenter


class Batch(Base):
    """Сменное задание / Партия."""

    __tablename__ = "batches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Статус
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Описание задания
    task_description: Mapped[str] = mapped_column(String(2000), nullable=False)
    work_center_id: Mapped[int] = mapped_column(ForeignKey("work_centers.id"), nullable=False)
    shift: Mapped[str] = mapped_column(String(255), nullable=False)
    team: Mapped[str] = mapped_column(String(255), nullable=False)

    # Идентификация партии
    batch_number: Mapped[int] = mapped_column(nullable=False, index=True)
    batch_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Продукция
    nomenclature: Mapped[str] = mapped_column(String(500), nullable=False)
    ekn_code: Mapped[str] = mapped_column(String(255), nullable=False)

    # Временные рамки
    shift_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    shift_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Метаданные
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Связи
    products: Mapped[List["Product"]] = relationship("Product", back_populates="batch")
    work_center: Mapped["WorkCenter"] = relationship("WorkCenter", back_populates="batches")

    __table_args__ = (
        UniqueConstraint("batch_number", "batch_date", name="uq_batch_number_date"),
        Index("idx_batch_closed", "is_closed"),
        Index("idx_batch_shift_times", "shift_start", "shift_end"),
    )
