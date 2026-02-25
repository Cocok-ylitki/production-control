from fastapi import APIRouter, HTTPException

from src.api.v1.schemas.analytics import (
    BatchStatisticsResponse,
    CompareBatchesRequest,
    CompareBatchesResponse,
    DashboardStatsResponse,
)
from src.core.cache import cache_get, cache_set
from src.core.dependencies import DbSession
from src.domain.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])

DASHBOARD_TTL = 300
BATCH_STATISTICS_TTL = 300


@router.get("/dashboard", response_model=DashboardStatsResponse)
async def get_dashboard(db: DbSession):
    """
    Расширенная статистика дашборда (summary, today, by_shift, top_work_centers).
    Кэш TTL 5 минут.
    """
    data = await cache_get("dashboard_stats")
    if data is not None:
        try:
            return DashboardStatsResponse.model_validate(data)
        except Exception:
            pass

    service = AnalyticsService(db)
    stats = await service.get_dashboard_statistics()
    await cache_set("dashboard_stats", stats, DASHBOARD_TTL)
    return DashboardStatsResponse.model_validate(stats)


@router.get("/batches/{batch_id}/statistics", response_model=BatchStatisticsResponse)
async def get_batch_statistics(batch_id: int, db: DbSession):
    """Расширенная статистика по партии (batch_info, production_stats, timeline, team_performance)."""
    data = await cache_get(f"batch_statistics:{batch_id}")
    if data is not None:
        try:
            return BatchStatisticsResponse.model_validate(data)
        except Exception:
            pass

    service = AnalyticsService(db)
    stats = await service.get_batch_statistics(batch_id)
    if stats is None:
        raise HTTPException(404, "Batch not found")
    await cache_set(f"batch_statistics:{batch_id}", stats, BATCH_STATISTICS_TTL)
    return BatchStatisticsResponse.model_validate(stats)


@router.post("/compare-batches", response_model=CompareBatchesResponse)
async def compare_batches(body: CompareBatchesRequest, db: DbSession):
    """Сравнение нескольких партий по показателям и средним значениям."""
    service = AnalyticsService(db)
    result = await service.compare_batches(body.batch_ids)
    return CompareBatchesResponse.model_validate(result)
