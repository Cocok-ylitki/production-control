from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.data.models import Batch, Product, WorkCenter


class AnalyticsService:
    def __init__(self, session: AsyncSession):
        self._session = session

    def _ts(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    async def get_dashboard_statistics(self) -> dict[str, Any]:
        """
        Расширенная статистика дашборда: summary, today, by_shift, top_work_centers, cached_at.
        """
        # Summary
        total_batches = (await self._session.execute(select(func.count(Batch.id)))).scalar() or 0
        active_batches = (
            await self._session.execute(
                select(func.count(Batch.id)).where(Batch.is_closed.is_(False))
            )
        ).scalar() or 0
        closed_batches = total_batches - active_batches
        total_products = (await self._session.execute(select(func.count(Product.id)))).scalar() or 0
        aggregated_products = (
            await self._session.execute(
                select(func.count(Product.id)).where(Product.is_aggregated.is_(True))
            )
        ).scalar() or 0
        aggregation_rate = (
            round(100.0 * aggregated_products / total_products, 2) if total_products else 0.0
        )
        summary = {
            "total_batches": total_batches,
            "active_batches": active_batches,
            "closed_batches": closed_batches,
            "total_products": total_products,
            "aggregated_products": aggregated_products,
            "aggregation_rate": aggregation_rate,
        }

        # Today (по дате created_at / closed_at / aggregated_at в UTC)
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        batches_created_today = (
            await self._session.execute(
                select(func.count(Batch.id)).where(Batch.created_at >= today_start)
            )
        ).scalar() or 0
        batches_closed_today = (
            await self._session.execute(
                select(func.count(Batch.id)).where(
                    Batch.closed_at >= today_start,
                    Batch.closed_at.isnot(None),
                )
            )
        ).scalar() or 0
        products_added_today = (
            await self._session.execute(
                select(func.count(Product.id)).where(Product.created_at >= today_start)
            )
        ).scalar() or 0
        products_aggregated_today = (
            await self._session.execute(
                select(func.count(Product.id)).where(
                    Product.aggregated_at >= today_start,
                    Product.aggregated_at.isnot(None),
                )
            )
        ).scalar() or 0
        today = {
            "batches_created": batches_created_today,
            "batches_closed": batches_closed_today,
            "products_added": products_added_today,
            "products_aggregated": products_aggregated_today,
        }

        # By shift (группировка по Batch.shift)
        shift_stmt = (
            select(
                Batch.shift,
                func.count(Batch.id).label("batches"),
                func.count(Product.id).label("products"),
                func.sum(func.cast(Product.is_aggregated, type_=func.Integer())).label("aggregated"),
            )
            .outerjoin(Product, Batch.id == Product.batch_id)
            .group_by(Batch.shift)
        )
        shift_result = await self._session.execute(shift_stmt)
        by_shift = {}
        for row in shift_result.all():
            shift_name = row.shift or "—"
            by_shift[shift_name] = {
                "batches": int(row.batches or 0),
                "products": int(row.products or 0),
                "aggregated": int(row.aggregated or 0),
            }

        # Top work centers: один запрос с подзапросом/группировкой по WorkCenter
        wc_subq = (
            select(
                Batch.work_center_id,
                func.count(Batch.id).label("batches_count"),
                func.count(Product.id).label("products_count"),
                func.sum(func.cast(Product.is_aggregated, type_=func.Integer())).label("agg"),
            )
            .outerjoin(Product, Product.batch_id == Batch.id)
            .group_by(Batch.work_center_id)
        ).subquery()
        wc_stmt = (
            select(
                WorkCenter.identifier,
                WorkCenter.name,
                wc_subq.c.batches_count,
                wc_subq.c.products_count,
                wc_subq.c.agg,
            )
            .join(wc_subq, wc_subq.c.work_center_id == WorkCenter.id)
            .order_by(wc_subq.c.batches_count.desc())
            .limit(10)
        )
        wc_result = await self._session.execute(wc_stmt)
        top_work_centers = []
        for row in wc_result.all():
            products_count = row.products_count or 0
            aggregated = row.agg or 0
            rate = round(100.0 * aggregated / products_count, 1) if products_count else 0.0
            top_work_centers.append({
                "id": row.identifier,
                "name": row.name,
                "batches_count": row.batches_count,
                "products_count": products_count,
                "aggregation_rate": rate,
            })

        return {
            "summary": summary,
            "today": today,
            "by_shift": by_shift,
            "top_work_centers": top_work_centers,
            "cached_at": self._ts(),
        }

    async def get_batch_statistics(self, batch_id: int) -> dict[str, Any] | None:
        """
        Расширенная статистика по партии: batch_info, production_stats, timeline, team_performance.
        """
        result = await self._session.execute(
            select(Batch)
            .where(Batch.id == batch_id)
            .options(selectinload(Batch.products), selectinload(Batch.work_center))
        )
        batch = result.scalars().one_or_none()
        if batch is None:
            return None

        total = len(batch.products)
        aggregated = sum(1 for p in batch.products if p.is_aggregated)
        remaining = total - aggregated
        rate = round(100.0 * aggregated / total, 2) if total else 0.0

        batch_info = {
            "id": batch.id,
            "batch_number": batch.batch_number,
            "batch_date": str(batch.batch_date),
            "is_closed": batch.is_closed,
        }
        production_stats = {
            "total_products": total,
            "aggregated": aggregated,
            "remaining": remaining,
            "aggregation_rate": rate,
        }

        # Timeline
        shift_duration_hours = 0.0
        elapsed_hours = 0.0
        products_per_hour = 0.0
        estimated_completion = None
        if batch.shift_start and batch.shift_end:
            try:
                delta = batch.shift_end - batch.shift_start
                shift_duration_hours = delta.total_seconds() / 3600
            except Exception:
                pass
            now = datetime.now(timezone.utc)
            if batch.shift_start.tzinfo is None:
                start = batch.shift_start.replace(tzinfo=timezone.utc)
            else:
                start = batch.shift_start
            if start <= now:
                elapsed = (now - start).total_seconds() / 3600
                elapsed_hours = round(elapsed, 2)
                if aggregated and elapsed_hours > 0:
                    products_per_hour = round(aggregated / elapsed_hours, 2)
                if not batch.is_closed and remaining and products_per_hour > 0:
                    from datetime import timedelta
                    hours_left = remaining / products_per_hour
                    est = now + timedelta(hours=hours_left)
                    estimated_completion = est.strftime("%Y-%m-%dT%H:%M:%SZ")
        timeline = {
            "shift_duration_hours": shift_duration_hours,
            "elapsed_hours": elapsed_hours,
            "products_per_hour": products_per_hour,
            "estimated_completion": estimated_completion,
        }

        # Team performance
        efficiency_score = round(products_per_hour / (shift_duration_hours or 1) * 10, 1) if shift_duration_hours else 0
        team_performance = {
            "team": batch.team,
            "avg_products_per_hour": products_per_hour,
            "efficiency_score": min(100.0, efficiency_score),
        }

        return {
            "batch_info": batch_info,
            "production_stats": production_stats,
            "timeline": timeline,
            "team_performance": team_performance,
        }

    async def compare_batches(self, batch_ids: list[int]) -> dict[str, Any]:
        """Сравнение партий: comparison (массив по batch_id) и average."""
        if not batch_ids:
            return {"comparison": [], "average": {"aggregation_rate": 0.0, "products_per_hour": 0.0}}

        comparison = []
        for batch_id in batch_ids:
            result = await self._session.execute(
                select(Batch)
                .where(Batch.id == batch_id)
                .options(selectinload(Batch.products))
            )
            batch = result.scalars().one_or_none()
            if batch is None:
                continue
            total = len(batch.products)
            aggregated = sum(1 for p in batch.products if p.is_aggregated)
            rate = round(100.0 * aggregated / total, 2) if total else 0.0
            duration_hours = 0.0
            if batch.shift_start and batch.shift_end:
                try:
                    duration_hours = (batch.shift_end - batch.shift_start).total_seconds() / 3600
                except Exception:
                    pass
            products_per_hour = round(aggregated / duration_hours, 2) if duration_hours else 0.0
            comparison.append({
                "batch_id": batch.id,
                "batch_number": batch.batch_number,
                "total_products": total,
                "aggregated": aggregated,
                "rate": rate,
                "duration_hours": duration_hours,
                "products_per_hour": products_per_hour,
            })

        if not comparison:
            return {"comparison": [], "average": {"aggregation_rate": 0.0, "products_per_hour": 0.0}}

        avg_rate = round(sum(c["rate"] for c in comparison) / len(comparison), 2)
        rates_ph = [c["products_per_hour"] for c in comparison if c["products_per_hour"]]
        avg_ph = round(sum(rates_ph) / len(rates_ph), 2) if rates_ph else 0.0
        return {
            "comparison": comparison,
            "average": {"aggregation_rate": avg_rate, "products_per_hour": avg_ph},
        }
