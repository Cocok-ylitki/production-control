from fastapi import APIRouter, HTTPException

from src.api.v1.schemas.task import TaskStatusResponse
from src.celery_app import celery_app

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    result = celery_app.AsyncResult(task_id)
    status = result.status
    payload = {"task_id": task_id, "status": status, "result": None}

    if status == "PROGRESS" and result.info:
        payload["result"] = result.info
    elif status == "SUCCESS" and result.result is not None:
        payload["result"] = result.result if isinstance(result.result, dict) else {"output": result.result}
    elif status == "FAILURE":
        payload["result"] = {"error": str(result.result) if result.result else "Task failed"}

    return TaskStatusResponse(**payload)
