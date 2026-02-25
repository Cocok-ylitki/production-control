from datetime import date, datetime
from io import BytesIO
from typing import TYPE_CHECKING

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

if TYPE_CHECKING:
    from src.data.models import Batch


def _format_dt(d: datetime | None) -> str:
    if d is None:
        return "-"
    return d.strftime("%Y-%m-%d %H:%M:%S") if hasattr(d, "strftime") else str(d)


def _format_date(d: date | None) -> str:
    if d is None:
        return "-"
    return d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)


def generate_batch_report_pdf(batch: "Batch") -> bytes:
    """Генерирует PDF-отчёт по партии."""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Информация о партии", styles["Heading1"]))
    story.append(Spacer(1, 0.5 * cm))
    info_data = [
        ["Номер партии", str(batch.batch_number)],
        ["Дата партии", _format_date(batch.batch_date)],
        ["Статус", "Закрыта" if batch.is_closed else "Открыта"],
        ["Рабочий центр", batch.work_center.name if batch.work_center else "-"],
        ["Смена", batch.shift],
        ["Бригада", batch.team],
        ["Номенклатура", batch.nomenclature],
        ["Начало смены", _format_dt(batch.shift_start)],
        ["Окончание смены", _format_dt(batch.shift_end)],
    ]
    t1 = Table(info_data, colWidths=[5 * cm, 10 * cm])
    t1.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.lightgrey)]))
    story.append(t1)
    story.append(Spacer(1, 1 * cm))

    story.append(Paragraph("Продукция", styles["Heading2"]))
    story.append(Spacer(1, 0.3 * cm))
    rows = [["ID", "Уникальный код", "Аггрегирована", "Дата аггрегации"]]
    for p in batch.products[:500]:  # ограничиваем для PDF
        rows.append([
            str(p.id),
            p.unique_code,
            "Да" if p.is_aggregated else "Нет",
            _format_dt(p.aggregated_at),
        ])
    if len(batch.products) > 500:
        rows.append(["...", f"и ещё {len(batch.products) - 500} записей", "", ""])
    t2 = Table(rows, colWidths=[2 * cm, 5 * cm, 3 * cm, 5 * cm])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
    ]))
    story.append(t2)
    story.append(Spacer(1, 1 * cm))

    total = len(batch.products)
    agg_count = sum(1 for p in batch.products if p.is_aggregated)
    pct = (100 * agg_count / total) if total else 0
    story.append(Paragraph("Статистика", styles["Heading2"]))
    story.append(Paragraph(
        f"Всего: {total}, Аггрегировано: {agg_count}, Осталось: {total - agg_count}, Выполнение: {pct:.0f}%",
        styles["Normal"],
    ))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()
