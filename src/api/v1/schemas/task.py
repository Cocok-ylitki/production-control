from typing import Any

from pydantic import BaseModel


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: dict[str, Any] | None = None


class AggregateAsyncAcceptResponse(BaseModel):
    task_id: str
    status: str = "PENDING"
    message: str = "Aggregation task started"


class ReportAcceptResponse(BaseModel):
    task_id: str
    status: str = "PENDING"


class ImportAcceptResponse(BaseModel):
    task_id: str
    status: str = "PENDING"
    message: str = "File uploaded, import started"


class ExportAcceptResponse(BaseModel):
    task_id: str
