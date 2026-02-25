"""
Форматы payload для webhook-событий.
Все payload: { "event": str, "data": dict, "timestamp": "ISO8601Z" }
"""
from datetime import datetime, timezone


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def payload_batch_created(
    *,
    id: int,
    batch_number: int,
    batch_date: str,
    nomenclature: str,
    work_center: str,
) -> dict:
    return {
        "event": "batch_created",
        "data": {
            "id": id,
            "batch_number": batch_number,
            "batch_date": batch_date,
            "nomenclature": nomenclature,
            "work_center": work_center,
        },
        "timestamp": _ts(),
    }


def payload_batch_updated(
    *,
    id: int,
    batch_number: int,
    changes: dict,
) -> dict:
    return {
        "event": "batch_updated",
        "data": {
            "id": id,
            "batch_number": batch_number,
            "changes": changes,
        },
        "timestamp": _ts(),
    }


def payload_batch_closed(
    *,
    id: int,
    batch_number: int,
    closed_at: str,
    total_products: int,
    aggregated: int,
    aggregation_rate: float,
) -> dict:
    return {
        "event": "batch_closed",
        "data": {
            "id": id,
            "batch_number": batch_number,
            "closed_at": closed_at,
            "statistics": {
                "total_products": total_products,
                "aggregated": aggregated,
                "aggregation_rate": round(aggregation_rate, 1),
            },
        },
        "timestamp": _ts(),
    }


def payload_product_aggregated(
    *,
    unique_code: str,
    batch_id: int,
    batch_number: int,
    aggregated_at: str,
) -> dict:
    return {
        "event": "product_aggregated",
        "data": {
            "unique_code": unique_code,
            "batch_id": batch_id,
            "batch_number": batch_number,
            "aggregated_at": aggregated_at,
        },
        "timestamp": _ts(),
    }


def payload_report_generated(
    *,
    batch_id: int,
    report_type: str,
    file_url: str,
    expires_at: str,
) -> dict:
    return {
        "event": "report_generated",
        "data": {
            "batch_id": batch_id,
            "report_type": report_type,
            "file_url": file_url,
            "expires_at": expires_at,
        },
        "timestamp": _ts(),
    }


def payload_import_completed(
    *,
    total_rows: int,
    created: int,
    skipped: int,
    errors: list[dict],
) -> dict:
    return {
        "event": "import_completed",
        "data": {
            "total_rows": total_rows,
            "created": created,
            "skipped": skipped,
            "errors": errors,
        },
        "timestamp": _ts(),
    }
