"""Initial schema: work_centers, batches, products, webhook_subscriptions, webhook_deliveries

Revision ID: 001
Revises:
Create Date: 2024-01-30

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "work_centers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("identifier", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_work_centers_identifier", "work_centers", ["identifier"], unique=True)

    op.create_table(
        "batches",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("is_closed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("task_description", sa.String(2000), nullable=False),
        sa.Column("work_center_id", sa.Integer(), nullable=False),
        sa.Column("shift", sa.String(255), nullable=False),
        sa.Column("team", sa.String(255), nullable=False),
        sa.Column("batch_number", sa.Integer(), nullable=False),
        sa.Column("batch_date", sa.Date(), nullable=False),
        sa.Column("nomenclature", sa.String(500), nullable=False),
        sa.Column("ekn_code", sa.String(255), nullable=False),
        sa.Column("shift_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("shift_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["work_center_id"], ["work_centers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("batch_number", "batch_date", name="uq_batch_number_date"),
    )
    op.create_index("ix_batches_batch_date", "batches", ["batch_date"], unique=False)
    op.create_index("ix_batches_batch_number", "batches", ["batch_number"], unique=False)
    op.create_index("ix_batches_is_closed", "batches", ["is_closed"], unique=False)
    op.create_index("idx_batch_shift_times", "batches", ["shift_start", "shift_end"], unique=False)

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("unique_code", sa.String(255), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("is_aggregated", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("aggregated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["batches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_product_batch_aggregated", "products", ["batch_id", "is_aggregated"], unique=False)
    op.create_index("ix_products_batch_id", "products", ["batch_id"], unique=False)
    op.create_index("ix_products_unique_code", "products", ["unique_code"], unique=True)

    op.create_table(
        "webhook_subscriptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("events", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("secret_key", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("retry_count", sa.Integer(), server_default=sa.text("3"), nullable=False),
        sa.Column("timeout", sa.Integer(), server_default=sa.text("10"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(255), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["subscription_id"], ["webhook_subscriptions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("webhook_deliveries")
    op.drop_table("webhook_subscriptions")
    op.drop_index("ix_products_unique_code", table_name="products")
    op.drop_index("ix_products_batch_id", table_name="products")
    op.drop_index("idx_product_batch_aggregated", table_name="products")
    op.drop_table("products")
    op.drop_index("idx_batch_shift_times", table_name="batches")
    op.drop_index("ix_batches_is_closed", table_name="batches")
    op.drop_index("ix_batches_batch_number", table_name="batches")
    op.drop_index("ix_batches_batch_date", table_name="batches")
    op.drop_table("batches")
    op.drop_index("ix_work_centers_identifier", table_name="work_centers")
    op.drop_table("work_centers")
