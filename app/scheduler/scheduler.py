import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.config import settings
from app.database import async_session
from app.models.task import CronTask
from app.scheduler.runner import run_task

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        raise RuntimeError("Scheduler not initialized")
    return _scheduler


async def init_scheduler() -> AsyncIOScheduler:
    """Initialize scheduler and register all enabled tasks from database."""
    global _scheduler

    _scheduler = AsyncIOScheduler(timezone=settings.SCHEDULER_TIMEZONE)

    # Load enabled tasks from database
    async with async_session() as db:
        result = await db.execute(select(CronTask).where(CronTask.enabled == True))
        tasks = result.scalars().all()

        for task in tasks:
            _register_job(_scheduler, task)
            logger.info("Registered task: %s (cron: %s)", task.name, task.cron_expression)

    _scheduler.start()
    logger.info("Scheduler started with %d tasks", len(tasks))
    return _scheduler


async def shutdown_scheduler() -> None:
    """Gracefully shutdown the scheduler."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped")


def _register_job(scheduler: AsyncIOScheduler, task: CronTask) -> None:
    """Register a single task with the scheduler."""
    job_id = str(task.id)
    trigger = CronTrigger.from_crontab(
        task.cron_expression, timezone=task.timezone or settings.SCHEDULER_TIMEZONE
    )
    scheduler.add_job(
        run_task,
        trigger=trigger,
        args=[task.id, "cron"],
        id=job_id,
        misfire_grace_time=settings.SCHEDULER_MISFIRE_GRACE_TIME,
        coalesce=settings.SCHEDULER_COALESCE,
        replace_existing=True,
    )


def add_job(task: CronTask) -> None:
    """Add a task to the scheduler."""
    if task.enabled:
        _register_job(get_scheduler(), task)
        logger.info("Added job for task: %s", task.name)


def remove_job(task_id: int) -> None:
    """Remove a task from the scheduler."""
    scheduler = get_scheduler()
    job_id = str(task_id)
    try:
        scheduler.remove_job(job_id)
        logger.info("Removed job for task_id: %d", task_id)
    except Exception:
        pass  # Job may not exist


def reschedule_job(task: CronTask) -> None:
    """Reschedule a task (update cron expression etc.)."""
    if task.enabled:
        remove_job(task.id)
        add_job(task)
    else:
        remove_job(task.id)
