import logging
from pathlib import Path
from typing import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.execution import ExecutionRecord
from app.models.log import ExecutionLog
from app.models.task import CronTask
from app.schemas.task import TaskCreate, TaskUpdate

logger = logging.getLogger(__name__)


class TaskService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_task(self, data: TaskCreate) -> CronTask:
        task = CronTask(**data.model_dump())
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def get_task(self, task_id: int) -> CronTask | None:
        return await self.db.get(CronTask, task_id)

    async def list_tasks(
        self,
        page: int = 1,
        page_size: int = 20,
        enabled: bool | None = None,
        owner_agent: str | None = None,
        tag: str | None = None,
    ) -> tuple[Sequence[CronTask], int]:
        query = select(CronTask)
        count_query = select(func.count()).select_from(CronTask)

        if enabled is not None:
            query = query.where(CronTask.enabled == enabled)
            count_query = count_query.where(CronTask.enabled == enabled)
        if owner_agent is not None:
            query = query.where(CronTask.owner_agent == owner_agent)
            count_query = count_query.where(CronTask.owner_agent == owner_agent)
        if tag is not None:
            query = query.where(CronTask.tags.contains([tag]))
            count_query = count_query.where(CronTask.tags.contains([tag]))

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        query = (
            query.order_by(CronTask.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        tasks = result.scalars().all()
        return tasks, total

    async def update_task(self, task_id: int, data: TaskUpdate) -> CronTask | None:
        task = await self.get_task(task_id)
        if task is None:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(task, field, value)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def delete_task(self, task_id: int) -> bool:
        task = await self.get_task(task_id)
        if task is None:
            return False

        # Clean up log files before cascade delete
        log_query = (
            select(ExecutionLog.stdout_path, ExecutionLog.stderr_path)
            .join(ExecutionRecord, ExecutionLog.execution_id == ExecutionRecord.id)
            .where(ExecutionRecord.task_id == task_id)
        )
        result = await self.db.execute(log_query)
        for row in result.fetchall():
            for path_str in row:
                if path_str:
                    try:
                        p = Path(path_str)
                        if p.exists():
                            p.unlink()
                    except Exception as e:
                        logger.warning("Failed to delete log file %s: %s", path_str, e)

        await self.db.delete(task)
        await self.db.commit()
        return True

    async def set_enabled(self, task_id: int, enabled: bool) -> CronTask | None:
        task = await self.get_task(task_id)
        if task is None:
            return None
        task.enabled = enabled
        await self.db.commit()
        await self.db.refresh(task)
        return task
