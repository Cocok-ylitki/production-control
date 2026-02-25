from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.celery_app import celery_app
from src.core.database_sync import get_sync_session
from src.data.models import Batch
from src.storage.minio_service import upload_export
from src.utils.excel_generator import generate_batches_export_excel, generate_batches_export_csv


@celery_app.task
def export_batches_to_file(
    filters: dict,
    format: str = "excel",
):
    """
    Экспорт списка партий в файл (Excel или CSV).
    filters: is_closed (bool|None), date_from (YYYY-MM-DD|None), date_to (YYYY-MM-DD|None)
    """
    is_closed = filters.get("is_closed")
    date_from_s = filters.get("date_from")
    date_to_s = filters.get("date_to")
    date_from = None
    date_to = None
    if date_from_s:
        if isinstance(date_from_s, date):
            date_from = date_from_s
        else:
            date_from = datetime.strptime(str(date_from_s)[:10], "%Y-%m-%d").date()
    if date_to_s:
        if isinstance(date_to_s, date):
            date_to = date_to_s
        else:
            date_to = datetime.strptime(str(date_to_s)[:10], "%Y-%m-%d").date()

    with get_sync_session() as session:
        q = select(Batch).options(selectinload(Batch.work_center))
        if is_closed is not None:
            q = q.where(Batch.is_closed == is_closed)
        if date_from is not None:
            q = q.where(Batch.batch_date >= date_from)
        if date_to is not None:
            q = q.where(Batch.batch_date <= date_to)
        q = q.order_by(Batch.id.desc())
        result = session.execute(q)
        batches = list(result.scalars().all())

    if not batches:
        return {"success": True, "file_url": None, "total_batches": 0}

    fmt = (format or "excel").lower()
    if fmt == "csv":
        data = generate_batches_export_csv(batches)
        file_name = f"batches_export_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.csv"
        content_type = "text/csv"
    else:
        data = generate_batches_export_excel(batches)
        file_name = f"batches_export_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.xlsx"
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    file_url, _ = upload_export(file_name, data, content_type=content_type)
    return {
        "success": True,
        "file_url": file_url,
        "total_batches": len(batches),
    }
