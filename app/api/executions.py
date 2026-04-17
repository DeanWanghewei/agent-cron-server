from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import PaginatedResponse
from app.schemas.execution import ExecutionLogRead, ExecutionRecordRead
from app.services.execution_service import ExecutionService

router = APIRouter(prefix="/executions", tags=["executions"])


def _exec_service(db: AsyncSession = Depends(get_db)) -> ExecutionService:
    return ExecutionService(db)


@router.get("", response_model=PaginatedResponse[ExecutionRecordRead])
async def list_executions(
    page: int = 1,
    page_size: int = 20,
    task_id: int | None = None,
    status: str | None = None,
    trigger_type: str | None = None,
    svc: ExecutionService = Depends(_exec_service),
):
    records, total = await svc.list_executions(
        page=page, page_size=page_size, task_id=task_id,
        status=status, trigger_type=trigger_type,
    )
    total_pages = (total + page_size - 1) // page_size
    return PaginatedResponse(
        items=[ExecutionRecordRead.model_validate(r) for r in records],
        total=total, page=page, page_size=page_size, total_pages=total_pages,
    )


@router.get("/{execution_id}", response_model=ExecutionRecordRead)
async def get_execution(execution_id: int, svc: ExecutionService = Depends(_exec_service)):
    record = await svc.get_execution(execution_id)
    if record is None:
        raise HTTPException(404, "Execution not found")
    return record


@router.get("/{execution_id}/log", response_model=ExecutionLogRead)
async def get_execution_log(execution_id: int, svc: ExecutionService = Depends(_exec_service)):
    log = await svc.get_execution_log(execution_id)
    if log is None:
        raise HTTPException(404, "Log not found")
    return ExecutionLogRead.model_validate(log)


@router.delete("/{execution_id}", status_code=204)
async def delete_execution(execution_id: int, svc: ExecutionService = Depends(_exec_service)):
    removed = await svc.delete_execution(execution_id)
    if not removed:
        raise HTTPException(404, "Execution not found")
