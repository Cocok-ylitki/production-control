from datetime import date
from typing import List

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from src.api.v1.schemas.batch import (
    BatchCreateItem,
    BatchListItem,
    BatchListResponse,
    BatchResponse,
    BatchUpdate,
    ProductInBatchResponse,
)
from src.api.v1.schemas.task import (
    AggregateAsyncAcceptResponse,
    ExportAcceptResponse,
    ImportAcceptResponse,
    ReportAcceptResponse,
)
from src.core.dependencies import DbSession
from src.core.exceptions import NotFoundError
from src.domain.services.batch_service import BatchService

router = APIRouter(prefix="/batches", tags=["batches"])


@router.post("", status_code=201)
async def create_batches(body: List[BatchCreateItem], db: DbSession):
    if not body:
        raise HTTPException(400, "Request body must be a non-empty array")
    service = BatchService(db)
    batches = await service.create_batches(body)
    from src.tasks.webhook_events import payload_batch_created
    from src.tasks.webhooks import notify_webhook_event

    from src.core.cache import invalidate_on_batch_change

    for item, batch in zip(body, batches):
        payload = payload_batch_created(
            id=batch.id,
            batch_number=batch.batch_number,
            batch_date=str(batch.batch_date),
            nomenclature=batch.nomenclature,
            work_center=item.РабочийЦентр,
        )
        notify_webhook_event.delay(payload)
    await invalidate_on_batch_change(None)
    return [BatchListItem.model_validate(b) for b in batches]


@router.get("/{batch_id}/statistics")
async def get_batch_statistics(batch_id: int, db: DbSession):
    """Расширенная статистика по партии (то же, что GET /api/v1/analytics/batches/{id}/statistics)."""
    from src.api.v1.schemas.analytics import BatchStatisticsResponse
    from src.core.cache import cache_get, cache_set
    from src.domain.services.analytics_service import AnalyticsService

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
    await cache_set(f"batch_statistics:{batch_id}", stats, 300)
    return BatchStatisticsResponse.model_validate(stats)


@router.get("/{batch_id}", response_model=BatchResponse)
async def get_batch(batch_id: int, db: DbSession):
    from src.core.cache import cache_get, cache_set

    cached_data = await cache_get(f"batch_detail:{batch_id}")
    if cached_data is not None:
        return BatchResponse.model_validate(cached_data)
    service = BatchService(db)
    try:
        batch = await service.get_by_id(batch_id)
    except NotFoundError as e:
        raise HTTPException(404, e.message)
    response = BatchResponse(
        id=batch.id,
        is_closed=batch.is_closed,
        batch_number=batch.batch_number,
        batch_date=batch.batch_date,
        products=[ProductInBatchResponse.model_validate(p) for p in batch.products],
    )
    await cache_set(f"batch_detail:{batch_id}", response.model_dump(), 600)  # 10 мин
    return response


@router.patch("/{batch_id}", response_model=BatchListItem)
async def update_batch(batch_id: int, body: BatchUpdate, db: DbSession):
    service = BatchService(db)
    try:
        batch = await service.update_batch(batch_id, is_closed=body.is_closed)
    except NotFoundError as e:
        raise HTTPException(404, e.message)
    from src.tasks.webhook_events import payload_batch_updated
    from src.tasks.webhooks import notify_webhook_event, notify_batch_closed

    changes = {}
    if body.is_closed is not None:
        changes["is_closed"] = body.is_closed
    if changes:
        payload = payload_batch_updated(
            id=batch.id,
            batch_number=batch.batch_number,
            changes=changes,
        )
        notify_webhook_event.delay(payload)
    if batch.is_closed:
        notify_batch_closed.delay(batch_id)
    from src.core.cache import invalidate_on_batch_change

    await invalidate_on_batch_change(batch_id)
    return BatchListItem.model_validate(batch)


@router.get("", response_model=BatchListResponse)
async def list_batches(
    db: DbSession,
    is_closed: bool | None = None,
    batch_number: int | None = None,
    batch_date: date | None = None,
    work_center_id: int | None = None,
    shift: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    from src.core.cache import cache_get, cache_set

    cache_key = f"batches_list:{is_closed}:{batch_number}:{batch_date}:{work_center_id}:{shift}:{offset}:{limit}"
    cached_data = await cache_get(cache_key)
    if cached_data is not None:
        return BatchListResponse.model_validate(cached_data)
    service = BatchService(db)
    items = await service.list_batches(
        is_closed=is_closed,
        batch_number=batch_number,
        batch_date=batch_date,
        work_center_id=work_center_id,
        shift=shift,
        offset=offset,
        limit=limit,
    )
    response = BatchListResponse(
        items=[BatchListItem.model_validate(b) for b in items],
        offset=offset,
        limit=limit,
    )
    await cache_set(cache_key, response.model_dump(), 60)  # 1 мин
    return response


@router.post("/import", status_code=202)
async def import_batches(
    file: UploadFile = File(...),
    user_id: int = Form(0, description="ID пользователя для уведомления о результате"),
):
    """Импорт партий из Excel. Файл загружается в MinIO, импорт выполняется в фоне. Статус: GET /api/v1/tasks/{task_id}."""
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(400, "File must be Excel (.xlsx, .xls)")
    from src.storage.minio_service import upload_import_file
    from src.tasks.imports import import_batches_from_file

    content = await file.read()
    object_key = upload_import_file(file.filename, content)
    task = import_batches_from_file.delay(file_url=object_key, user_id=user_id)
    return ImportAcceptResponse(
        task_id=task.id,
        status="PENDING",
        message="File uploaded, import started",
    )


@router.post("/export", status_code=202)
async def export_batches(body: dict):
    """Экспорт партий в Excel/CSV по фильтрам. Статус: GET /api/v1/tasks/{task_id}."""
    fmt = (body.get("format") or "excel").lower()
    if fmt not in ("excel", "csv"):
        raise HTTPException(400, "format must be 'excel' or 'csv'")
    filters = body.get("filters") or {}
    from src.tasks.exports import export_batches_to_file

    task = export_batches_to_file.delay(filters=filters, format=fmt)
    return ExportAcceptResponse(task_id=task.id)


@router.post("/{batch_id}/aggregate")
async def aggregate_batch(batch_id: int, db: DbSession):
    from src.api.v1.schemas.product import AggregateResponse
    from src.core.cache import invalidate_on_aggregation
    from src.domain.services.product_service import ProductService

    service = ProductService(db)
    try:
        count = await service.aggregate_batch(batch_id)
    except NotFoundError as e:
        raise HTTPException(404, e.message)
    await invalidate_on_aggregation(batch_id)
    return AggregateResponse(batch_id=batch_id, aggregated_count=count)


# --- Асинхронные задачи (Celery) ---


class AggregateAsyncBody:
    unique_codes: List[str]


@router.post("/{batch_id}/aggregate-async", status_code=202)
async def aggregate_batch_async(batch_id: int, body: dict, db: DbSession):
    """Запускает массовую аггрегацию по списку unique_codes. Статус: GET /api/v1/tasks/{task_id}."""
    unique_codes = body.get("unique_codes") or []
    if not unique_codes:
        raise HTTPException(400, "unique_codes is required and must be non-empty")
    service = BatchService(db)
    try:
        await service.get_by_id(batch_id)
    except NotFoundError as e:
        raise HTTPException(404, e.message)
    from src.tasks.aggregation import aggregate_products_batch

    task = aggregate_products_batch.delay(batch_id=batch_id, unique_codes=unique_codes)
    return AggregateAsyncAcceptResponse(
        task_id=task.id,
        status="PENDING",
        message="Aggregation task started",
    )


class ReportBody:
    format: str = "excel"
    email: str | None = None


@router.post("/{batch_id}/reports", status_code=202)
async def create_batch_report(batch_id: int, body: dict, db: DbSession):
    """Генерация отчёта по партии (excel/pdf). Статус: GET /api/v1/tasks/{task_id}."""
    report_format = (body.get("format") or "excel").lower()
    if report_format not in ("excel", "pdf"):
        raise HTTPException(400, "format must be 'excel' or 'pdf'")
    service = BatchService(db)
    try:
        await service.get_by_id(batch_id)
    except NotFoundError as e:
        raise HTTPException(404, e.message)
    from src.tasks.reports import generate_batch_report

    task = generate_batch_report.delay(
        batch_id=batch_id,
        format=report_format,
        user_email=body.get("email"),
    )
    return ReportAcceptResponse(task_id=task.id, status="PENDING")
