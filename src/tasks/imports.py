from datetime import date, datetime

from sqlalchemy import select

from src.celery_app import celery_app
from src.core.database_sync import get_sync_session
from src.data.models import Batch, WorkCenter
from src.storage.minio_service import download_file
from src.utils.excel_parser import parse_batches_excel

REQUIRED_KEYS = [
    "НомерПартии",
    "ДатаПартии",
    "Номенклатура",
    "РабочийЦентр",
    "Смена",
    "Бригада",
    "КодЕКН",
    "ИдентификаторРЦ",
    "ПредставлениеЗаданияНаСмену",
    "ДатаВремяНачалаСмены",
    "ДатаВремяОкончанияСмены",
]


@celery_app.task(bind=True, max_retries=1)
def import_batches_from_file(
    self,
    file_url: str,
    user_id: int,
):
    """
    Импорт партий из Excel/CSV файла (file_url — ключ в MinIO: bucket/prefix/name).
    """
    try:
        data = download_file(file_url)
    except Exception as e:
        return {"success": False, "error": str(e)}

    rows_with_idx = parse_batches_excel(data)
    total_rows = len(rows_with_idx)
    created = 0
    skipped = 0
    errors: list[dict] = []

    with get_sync_session() as session:
        for idx, (row_dict, row_num) in enumerate(rows_with_idx):
            # Прогресс
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": idx + 1,
                    "total": total_rows,
                    "created": created,
                    "skipped": skipped,
                },
            )

            missing = [k for k in REQUIRED_KEYS if row_dict.get(k) is None or row_dict.get(k) == ""]
            if missing:
                errors.append({"row": row_num, "error": f"Missing fields: {', '.join(missing)}"})
                skipped += 1
                continue

            batch_number = row_dict["НомерПартии"]
            batch_date = row_dict["ДатаПартии"]
            if isinstance(batch_date, datetime):
                batch_date = batch_date.date()

            # Проверка дубликата
            existing = session.execute(
                select(Batch).where(
                    Batch.batch_number == batch_number,
                    Batch.batch_date == batch_date,
                )
            ).scalars().one_or_none()
            if existing:
                errors.append({"row": row_num, "error": "Duplicate batch number and date"})
                skipped += 1
                continue

            # Рабочий центр
            identifier = str(row_dict["ИдентификаторРЦ"]).strip()
            name = str(row_dict["РабочийЦентр"]).strip()
            wc = session.execute(select(WorkCenter).where(WorkCenter.identifier == identifier)).scalars().one_or_none()
            if wc is None:
                wc = WorkCenter(identifier=identifier, name=name)
                session.add(wc)
                session.flush()

            is_closed = row_dict.get("СтатусЗакрытия", False)
            batch = Batch(
                is_closed=is_closed,
                closed_at=datetime.utcnow() if is_closed else None,
                task_description=str(row_dict["ПредставлениеЗаданияНаСмену"]),
                work_center_id=wc.id,
                shift=str(row_dict["Смена"]),
                team=str(row_dict["Бригада"]),
                batch_number=batch_number,
                batch_date=batch_date,
                nomenclature=str(row_dict["Номенклатура"]),
                ekn_code=str(row_dict["КодЕКН"]),
                shift_start=row_dict["ДатаВремяНачалаСмены"],
                shift_end=row_dict["ДатаВремяОкончанияСмены"],
            )
            session.add(batch)
            created += 1
            session.flush()

    from src.tasks.webhook_events import payload_import_completed
    from src.tasks.webhooks import notify_webhook_event

    payload = payload_import_completed(
        total_rows=total_rows,
        created=created,
        skipped=skipped,
        errors=errors,
    )
    notify_webhook_event.delay(payload)

    return {
        "success": True,
        "total_rows": total_rows,
        "created": created,
        "skipped": skipped,
        "errors": errors,
    }
