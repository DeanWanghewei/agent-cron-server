from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import PaginatedResponse
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.scheduler.scheduler import add_job, remove_job, reschedule_job
from app.scheduler.runner import run_task
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _task_service(db: AsyncSession = Depends(get_db)) -> TaskService:
    return TaskService(db)


@router.post("", response_model=TaskRead, status_code=201)
async def create_task(data: TaskCreate, svc: TaskService = Depends(_task_service)):
    task = await svc.create_task(data)
    add_job(task)
    return task


@router.get("", response_model=PaginatedResponse[TaskRead])
async def list_tasks(
    page: int = 1,
    page_size: int = 20,
    enabled: bool | None = None,
    owner_agent: str | None = None,
    tag: str | None = None,
    svc: TaskService = Depends(_task_service),
):
    tasks, total = await svc.list_tasks(
        page=page, page_size=page_size, enabled=enabled,
        owner_agent=owner_agent, tag=tag,
    )
    total_pages = (total + page_size - 1) // page_size
    return PaginatedResponse(
        items=[TaskRead.model_validate(t) for t in tasks],
        total=total, page=page, page_size=page_size, total_pages=total_pages,
    )


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(task_id: int, svc: TaskService = Depends(_task_service)):
    task = await svc.get_task(task_id)
    if task is None:
        raise HTTPException(404, "Task not found")
    return task


@router.put("/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: int, data: TaskUpdate, svc: TaskService = Depends(_task_service),
):
    task = await svc.update_task(task_id, data)
    if task is None:
        raise HTTPException(404, "Task not found")
    reschedule_job(task)
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: int, svc: TaskService = Depends(_task_service)):
    removed = await svc.delete_task(task_id)
    if not removed:
        raise HTTPException(404, "Task not found")
    remove_job(task_id)


@router.post("/{task_id}/trigger", response_model=dict)
async def trigger_task(task_id: int, svc: TaskService = Depends(_task_service)):
    task = await svc.get_task(task_id)
    if task is None:
        raise HTTPException(404, "Task not found")
    import asyncio
    asyncio.create_task(run_task(task_id, "manual"))
    return {"message": "Task triggered", "task_id": task_id}


@router.post("/{task_id}/enable", response_model=TaskRead)
async def enable_task(task_id: int, svc: TaskService = Depends(_task_service)):
    task = await svc.set_enabled(task_id, True)
    if task is None:
        raise HTTPException(404, "Task not found")
    add_job(task)
    return task


@router.post("/{task_id}/disable", response_model=TaskRead)
async def disable_task(task_id: int, svc: TaskService = Depends(_task_service)):
    task = await svc.set_enabled(task_id, False)
    if task is None:
        raise HTTPException(404, "Task not found")
    remove_job(task_id)
    return task
