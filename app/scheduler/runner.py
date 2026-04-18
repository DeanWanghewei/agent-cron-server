import asyncio
import logging
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.config import settings
from app.database import async_session
from app.models.execution import ExecutionRecord
from app.models.log import ExecutionLog
from app.models.task import CronTask

logger = logging.getLogger(__name__)


def _log_file_paths(task_id: int, execution_id: int) -> tuple[Path, Path]:
    """Build date-based log file paths: data/logs/2026-04-17/task_1_3_stdout.log"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    day_dir = Path(settings.LOG_DIR) / today
    day_dir.mkdir(parents=True, exist_ok=True)
    prefix = f"task_{task_id}_{execution_id}"
    return day_dir / f"{prefix}_stdout.log", day_dir / f"{prefix}_stderr.log"


def _write_log_file(path: Path, content: str, max_size: int) -> None:
    if len(content) > max_size:
        content = content[:max_size] + "\n... [truncated]"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", errors="replace")


def cleanup_expired_logs() -> int:
    """Delete date directories older than LOG_RETENTION_DAYS. Returns count of removed dirs."""
    retention = settings.LOG_RETENTION_DAYS
    if retention <= 0:
        return 0

    log_dir = Path(settings.LOG_DIR)
    if not log_dir.exists():
        return 0

    cutoff = datetime.now(timezone.utc).date() - timedelta(days=retention)
    removed = 0

    for entry in sorted(log_dir.iterdir()):
        if not entry.is_dir():
            continue
        # Dir name format: 2026-04-17
        try:
            dir_date = datetime.strptime(entry.name, "%Y-%m-%d").date()
        except ValueError:
            continue
        if dir_date < cutoff:
            shutil.rmtree(entry, ignore_errors=True)
            removed += 1
            logger.info("Cleaned up expired log directory: %s", entry.name)

    return removed


async def run_task(task_id: int, trigger_type: str = "cron") -> None:
    """Execute a task: create execution record, run subprocess, capture output."""
    async with async_session() as db:
        task = await db.get(CronTask, task_id)
        if task is None:
            logger.error("Task %d not found", task_id)
            return

        # Create execution record
        record = ExecutionRecord(
            task_id=task.id,
            task_name=task.name,
            status="running",
            trigger_type=trigger_type,
            started_at=datetime.utcnow(),
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)

        # Build date-based log paths
        stdout_path, stderr_path = _log_file_paths(task.id, record.id)

        # Create log entry with file paths
        log = ExecutionLog(
            execution_id=record.id,
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
        )
        db.add(log)
        await db.commit()

        try:
            stdout, stderr, exit_code = await _execute_command(
                command=task.command,
                shell=task.shell,
                working_dir=task.working_dir,
                env_vars=task.env_vars,
                timeout=task.timeout or settings.DEFAULT_TASK_TIMEOUT,
            )

            _write_log_file(stdout_path, stdout, settings.LOG_MAX_SIZE)
            _write_log_file(stderr_path, stderr, settings.LOG_MAX_SIZE)

            record.exit_code = exit_code
            # Status reflects process execution, not business logic.
            # A non-zero exit code is still a successful execution —
            # the exit_code field carries the actual result for callers to interpret.
            record.status = "success"

        except asyncio.TimeoutError:
            _write_log_file(stderr_path, f"Task timed out after {task.timeout} seconds", settings.LOG_MAX_SIZE)
            record.status = "timeout"
            record.error_message = "Timeout"

        except Exception as e:
            _write_log_file(stderr_path, str(e), settings.LOG_MAX_SIZE)
            record.status = "failed"
            record.error_message = str(e)[:500]

        finally:
            record.finished_at = datetime.utcnow()
            if record.started_at and record.finished_at:
                delta = record.finished_at - record.started_at
                record.duration_ms = int(delta.total_seconds() * 1000)
            await db.commit()


async def _execute_command(
    command: str,
    shell: bool = True,
    working_dir: str | None = None,
    env_vars: dict | None = None,
    timeout: int = 3600,
) -> tuple[str, str, int]:
    """Run a command via subprocess and return (stdout, stderr, exit_code)."""
    env = os.environ.copy()
    if env_vars:
        env.update({k: str(v) for k, v in env_vars.items()})

    if shell:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_dir,
            env=env,
        )
    else:
        proc = await asyncio.create_subprocess_exec(
            *command.split(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_dir,
            env=env,
        )

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise

    stdout = stdout_bytes.decode("utf-8", errors="replace")
    stderr = stderr_bytes.decode("utf-8", errors="replace")
    return stdout, stderr, proc.returncode or 0
