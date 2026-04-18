import asyncio
import logging
from typing import Any

from fastmcp import FastMCP

from app.database import async_session
from app.models.task import CronTask
from app.scheduler.runner import run_task
from app.scheduler.scheduler import add_job, remove_job, reschedule_job
from app.services.execution_service import ExecutionService
from app.services.task_service import TaskService
from app.schemas.task import TaskCreate, TaskUpdate

logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="agent-cron-server",
    instructions=(
        "Scheduled task execution service for AI agents. "
        "Create, manage, and monitor cron tasks that run shell commands/scripts.\n\n"
        "IMPORTANT: These tools are the primary way to interact with this service. "
        "Do NOT use the REST API (curl/HTTP) when MCP tools are available. "
        "All task CRUD, execution monitoring, and health checks should go through these MCP tools."
    ),
)


@mcp.tool()
async def create_cron_task(
    name: str,
    command: str,
    cron_expression: str,
    description: str | None = None,
    shell: bool = True,
    working_dir: str | None = None,
    env_vars: dict[str, str] | None = None,
    timezone: str = "Asia/Shanghai",
    enabled: bool = True,
    timeout: int = 3600,
    max_retries: int = 0,
    callback_url: str | None = None,
    callback_prompt: str | None = None,
    owner_agent: str | None = None,
    tags: list[str] | None = None,
) -> str:
    """Create a new scheduled task that runs a shell command on a cron schedule.

    If callback_url is provided, the server will POST execution results (JSON) to
    that URL after each run. Payload includes task_id, execution_id, status,
    exit_code, duration_ms, stdout_summary, stderr_summary, callback_prompt, etc.

    callback_prompt is the per-task instruction for the callback handler (e.g. Hermes
    webhook Agent). It tells the Agent how to analyze and act on the execution result.
    """
    async with async_session() as db:
        svc = TaskService(db)
        task = await svc.create_task(TaskCreate(
            name=name, command=command, cron_expression=cron_expression,
            description=description, shell=shell, working_dir=working_dir,
            env_vars=env_vars, timezone=timezone, enabled=enabled,
            timeout=timeout, max_retries=max_retries,
            callback_url=callback_url, callback_prompt=callback_prompt,
            owner_agent=owner_agent, tags=tags,
        ))
        add_job(task)
        return f"Task created: id={task.id}, name={task.name}, cron={task.cron_expression}"


@mcp.tool()
async def list_cron_tasks(
    enabled: bool | None = None,
    owner_agent: str | None = None,
    tag: str | None = None,
) -> str:
    """List all scheduled tasks, optionally filtered by enabled status, owner agent, or tag."""
    async with async_session() as db:
        svc = TaskService(db)
        tasks, total = await svc.list_tasks(
            page=1, page_size=100, enabled=enabled,
            owner_agent=owner_agent, tag=tag,
        )
        if not tasks:
            return "No tasks found."
        lines = [f"Total: {total} tasks\n"]
        for t in tasks:
            status = "enabled" if t.enabled else "disabled"
            lines.append(
                f"- [{t.id}] {t.name} | {status} | cron: {t.cron_expression} | "
                f"command: {t.command[:80]} | agent: {t.owner_agent or 'any'}"
            )
        return "\n".join(lines)


@mcp.tool()
async def get_cron_task(task_id: int) -> str:
    """Get detailed information about a specific task by ID."""
    async with async_session() as db:
        svc = TaskService(db)
        task = await svc.get_task(task_id)
        if task is None:
            return f"Task {task_id} not found."
        return (
            f"Task #{task.id}\n"
            f"  Name: {task.name}\n"
            f"  Description: {task.description or 'N/A'}\n"
            f"  Command: {task.command}\n"
            f"  Shell: {task.shell}\n"
            f"  Working Dir: {task.working_dir or 'default'}\n"
            f"  Cron: {task.cron_expression}\n"
            f"  Timezone: {task.timezone}\n"
            f"  Enabled: {task.enabled}\n"
            f"  Timeout: {task.timeout}s\n"
            f"  Callback URL: {task.callback_url or 'none'}\n"
            f"  Callback Prompt: {task.callback_prompt or 'none'}\n"
            f"  Owner Agent: {task.owner_agent or 'any'}\n"
            f"  Tags: {task.tags or []}\n"
            f"  Created: {task.created_at}"
        )


@mcp.tool()
async def update_cron_task(
    task_id: int,
    name: str | None = None,
    command: str | None = None,
    cron_expression: str | None = None,
    description: str | None = None,
    shell: bool | None = None,
    working_dir: str | None = None,
    env_vars: dict[str, str] | None = None,
    timezone: str | None = None,
    enabled: bool | None = None,
    timeout: int | None = None,
    max_retries: int | None = None,
    callback_url: str | None = None,
    callback_prompt: str | None = None,
    owner_agent: str | None = None,
    tags: list[str] | None = None,
) -> str:
    """Update an existing scheduled task."""
    # Only include fields that were explicitly provided (not None)
    updates = {
        k: v for k, v in {
            "name": name, "command": command, "cron_expression": cron_expression,
            "description": description, "shell": shell, "working_dir": working_dir,
            "env_vars": env_vars, "timezone": timezone, "enabled": enabled,
            "timeout": timeout, "max_retries": max_retries,
            "callback_url": callback_url, "callback_prompt": callback_prompt,
            "owner_agent": owner_agent, "tags": tags,
        }.items() if v is not None
    }
    async with async_session() as db:
        svc = TaskService(db)
        task = await svc.update_task(task_id, TaskUpdate(**updates))
        if task is None:
            return f"Task {task_id} not found."
        reschedule_job(task)
        return f"Task {task_id} updated successfully."


@mcp.tool()
async def delete_cron_task(task_id: int) -> str:
    """Delete a scheduled task and all its execution history."""
    async with async_session() as db:
        svc = TaskService(db)
        removed = await svc.delete_task(task_id)
        if not removed:
            return f"Task {task_id} not found."
        remove_job(task_id)
        return f"Task {task_id} deleted."


@mcp.tool()
async def trigger_cron_task(task_id: int) -> str:
    """Manually trigger a task to run immediately."""
    async with async_session() as db:
        svc = TaskService(db)
        task = await svc.get_task(task_id)
        if task is None:
            return f"Task {task_id} not found."
        asyncio.create_task(run_task(task_id, "manual"))
        return f"Task '{task.name}' (id={task_id}) triggered."


@mcp.tool()
async def enable_cron_task(task_id: int) -> str:
    """Enable a disabled task."""
    async with async_session() as db:
        svc = TaskService(db)
        task = await svc.set_enabled(task_id, True)
        if task is None:
            return f"Task {task_id} not found."
        add_job(task)
        return f"Task '{task.name}' enabled."


@mcp.tool()
async def disable_cron_task(task_id: int) -> str:
    """Disable an enabled task."""
    async with async_session() as db:
        svc = TaskService(db)
        task = await svc.set_enabled(task_id, False)
        if task is None:
            return f"Task {task_id} not found."
        remove_job(task_id)
        return f"Task '{task.name}' disabled."


@mcp.tool()
async def list_executions(
    task_id: int | None = None,
    status: str | None = None,
    limit: int = 20,
) -> str:
    """List execution records, optionally filtered by task_id and status."""
    async with async_session() as db:
        svc = ExecutionService(db)
        records, total = await svc.list_executions(
            page=1, page_size=min(limit, 50), task_id=task_id, status=status,
        )
        if not records:
            return "No execution records found."
        lines = [f"Total: {total} records\n"]
        for r in records:
            duration = f"{r.duration_ms}ms" if r.duration_ms else "N/A"
            lines.append(
                f"- [{r.id}] {r.task_name} | {r.status} | {r.trigger_type} | "
                f"duration: {duration} | exit: {r.exit_code} | {r.started_at}"
            )
        return "\n".join(lines)


@mcp.tool()
async def get_execution(execution_id: int) -> str:
    """Get detailed information about a specific execution record."""
    async with async_session() as db:
        svc = ExecutionService(db)
        record = await svc.get_execution(execution_id)
        if record is None:
            return f"Execution {execution_id} not found."
        duration = f"{record.duration_ms}ms" if record.duration_ms else "N/A"
        return (
            f"Execution #{record.id}\n"
            f"  Task: {record.task_name} (id={record.task_id})\n"
            f"  Status: {record.status}\n"
            f"  Trigger: {record.trigger_type}\n"
            f"  Started: {record.started_at}\n"
            f"  Finished: {record.finished_at}\n"
            f"  Duration: {duration}\n"
            f"  Exit Code: {record.exit_code}\n"
            f"  Error: {record.error_message or 'None'}"
        )


@mcp.tool()
async def get_execution_log(execution_id: int) -> str:
    """Get the stdout and stderr output of a specific execution."""
    async with async_session() as db:
        svc = ExecutionService(db)
        log = await svc.get_execution_log(execution_id)
        if log is None:
            return f"Log for execution {execution_id} not found."
        output = f"=== STDOUT ===\n{log.stdout}\n\n=== STDERR ===\n{log.stderr}"
        return output


@mcp.tool()
async def get_service_health() -> str:
    """Check the health status of the cron server."""
    from app.scheduler.scheduler import get_scheduler
    try:
        scheduler = get_scheduler()
        running = scheduler.running
        jobs = scheduler.get_jobs()
        return f"Service: OK\nScheduler: {'running' if running else 'stopped'}\nActive jobs: {len(jobs)}"
    except Exception as e:
        return f"Service: ERROR - {e}"
