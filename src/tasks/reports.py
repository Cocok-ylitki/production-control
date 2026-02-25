from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.celery_app import celery_app
from src.core.database_sync import get_sync_session
from src.data.models import Batch
from src.storage.minio_service import upload_report
from src.utils.excel_generator import generate_batch_report_excel
from src.utils.pdf_generator import generate_batch_report_pdf


def _load_batch(session, batch_id: int) -> Batch | None:
    result = session.execute(
        select(Batch)
        .where(Batch.id == batch_id)
        .options(
            selectinload(Batch.products),
            selectinload(Batch.work_center),
        )
    )
    return result.scalars().one_or_none()


@celery_app.task(bind=True, max_retries=3)
def generate_batch_report(
    self,
    batch_id: int,
    format: str = "excel",
    user_email: str | None = None,
):
    """
    Генерация детального отчёта по партии (Excel/PDF).
    Загружает файл в MinIO и возвращает URL.
    """
    with get_sync_session() as session:
        batch = _load_batch(session, batch_id)
        if batch is None:
            return {"success": False, "error": "Batch not found"}

        if format == "pdf":
            data = generate_batch_report_pdf(batch)
            file_name = f"batch_{batch_id}_report.pdf"
            content_type = "application/pdf"
        else:
            data = generate_batch_report_excel(batch)
            file_name = f"batch_{batch_id}_report.xlsx"
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    file_url, file_size = upload_report(file_name, data, content_type=content_type)
    expires_at = (datetime.utcnow() + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")

    from src.tasks.webhook_events import payload_report_generated
    from src.tasks.webhooks import notify_webhook_event

    payload = payload_report_generated(
        batch_id=batch_id,
        report_type=format,
        file_url=file_url,
        expires_at=expires_at,
    )
    notify_webhook_event.delay(payload)

    return {
        "success": True,
        "file_url": file_url,
        "file_name": file_name,
        "file_size": file_size,
        "expires_at": expires_at,
    }
