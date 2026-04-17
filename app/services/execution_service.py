import logging
from pathlib import Path
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.execution import ExecutionRecord
from app.models.log import ExecutionLog
from app.schemas.execution import ExecutionLogRead, ExecutionRecordRead

logger = logging.getLogger(__name__)


def _read_log_file(path: str | None) -> str:
    if not path:
        return ""
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""
    except Exception as e:
        logger.warning("Failed to read log file %s: %s", path, e)
        return ""


def _delete_log_file(path: str | None) -> None:
    if not path:
        return
    try:
        p = Path(path)
        if p.exists():
            p.unlink()
    except Exception as e:
        logger.warning("Failed to delete log file %s: %s", path, e)


class ExecutionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_executions(
        self,
        page: int = 1,
        page_size: int = 20,
        task_id: int | None = None,
        status: str | None = None,
        trigger_type: str | None = None,
    ) -> tuple[Sequence[ExecutionRecord], int]:
        query = select(ExecutionRecord)
        count_query = select(func.count()).select_from(ExecutionRecord)

        if task_id is not None:
            query = query.where(ExecutionRecord.task_id == task_id)
            count_query = count_query.where(ExecutionRecord.task_id == task_id)
        if status is not None:
            query = query.where(ExecutionRecord.status == status)
            count_query = count_query.where(ExecutionRecord.status == status)
        if trigger_type is not None:
            query = query.where(ExecutionRecord.trigger_type == trigger_type)
            count_query = count_query.where(ExecutionRecord.trigger_type == trigger_type)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        query = (
            query.order_by(ExecutionRecord.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        records = result.scalars().all()
        return records, total

    async def get_execution(self, execution_id: int) -> ExecutionRecord | None:
        return await self.db.get(ExecutionRecord, execution_id)

    async def get_execution_log(self, execution_id: int) -> ExecutionLogRead | None:
        query = select(ExecutionLog).where(ExecutionLog.execution_id == execution_id)
        result = await self.db.execute(query)
        log = result.scalar_one_or_none()
        if log is None:
            return None
        return ExecutionLogRead(
            id=log.id,
            execution_id=log.execution_id,
            stdout=_read_log_file(log.stdout_path),
            stderr=_read_log_file(log.stderr_path),
        )

    async def delete_execution(self, execution_id: int) -> bool:
        record = await self.get_execution(execution_id)
        if record is None:
            return False

        # Clean up log files
        query = select(ExecutionLog).where(ExecutionLog.execution_id == execution_id)
        result = await self.db.execute(query)
        log = result.scalar_one_or_none()
        if log:
            _delete_log_file(log.stdout_path)
            _delete_log_file(log.stderr_path)

        await self.db.delete(record)
        await self.db.commit()
        return True
