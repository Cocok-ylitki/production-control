from typing import Any

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_batches: int
    active_batches: int
    closed_batches: int
    total_products: int
    aggregated_products: int
    aggregation_rate: float


class DashboardToday(BaseModel):
    batches_created: int
    batches_closed: int
    products_added: int
    products_aggregated: int


class DashboardByShift(BaseModel):
    batches: int
    products: int
    aggregated: int


class TopWorkCenter(BaseModel):
    id: str
    name: str
    batches_count: int
    products_count: int
    aggregation_rate: float


class DashboardStatsResponse(BaseModel):
    summary: DashboardSummary
    today: DashboardToday
    by_shift: dict[str, DashboardByShift]
    top_work_centers: list[TopWorkCenter]
    cached_at: str


class DashboardStatsResponseLegacy(BaseModel):
    total_batches: int
    active_batches: int
    total_products: int
    aggregated_products: int
    aggregation_rate: float
    cached_at: str


class BatchInfo(BaseModel):
    id: int
    batch_number: int
    batch_date: str
    is_closed: bool


class ProductionStats(BaseModel):
    total_products: int
    aggregated: int
    remaining: int
    aggregation_rate: float


class BatchTimeline(BaseModel):
    shift_duration_hours: float
    elapsed_hours: float
    products_per_hour: float
    estimated_completion: str | None


class TeamPerformance(BaseModel):
    team: str
    avg_products_per_hour: float
    efficiency_score: float


class BatchStatisticsResponse(BaseModel):
    batch_info: BatchInfo
    production_stats: ProductionStats
    timeline: BatchTimeline
    team_performance: TeamPerformance


class CompareBatchItem(BaseModel):
    batch_id: int
    batch_number: int
    total_products: int
    aggregated: int
    rate: float
    duration_hours: float
    products_per_hour: float


class CompareAverage(BaseModel):
    aggregation_rate: float
    products_per_hour: float


class CompareBatchesResponse(BaseModel):
    comparison: list[CompareBatchItem]
    average: CompareAverage


class CompareBatchesRequest(BaseModel):
    batch_ids: list[int]
