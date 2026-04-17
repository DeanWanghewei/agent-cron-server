---
name: agent-cron
description: Scheduled task execution service — create, manage, and monitor cron tasks that run shell commands/scripts via MCP tools.
version: 0.1.0
author: agent-cron-server
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [cron, scheduler, automation, tasks, scheduling]
    related_skills: []
  openclaw:
    os:
      - darwin
      - linux
    requires:
      bins:
        - python3
required_environment_variables:
  - name: ACS_PORT
    prompt: "Port for the cron server (default: 8900)"
    help: "The HTTP port the agent-cron-server will listen on"
    required_for: "Server startup"
  - name: ACS_DATABASE_URL
    prompt: "Database URL (default: sqlite+aiosqlite:///./data/cron.db)"
    help: "SQLite or PostgreSQL connection string"
    required_for: "Persistent task storage"
---

# Agent Cron Server

定时任务调度服务，通过 MCP tools 管理定时执行的 shell 命令/脚本、查看执行记录和日志。

## When to Use

- 用户要求定时执行任务（如"每天早上9点运行这个脚本"）
- 用户想自动化周期性命令或脚本
- 用户提到 cron job、定时任务、周期执行
- 用户想查看某个已调度任务的执行状态或输出

## Prerequisites

agent-cron-server 必须运行中。使用前先通过 `get_service_health` 检查服务状态。

如果服务未运行，用 terminal 启动：

```bash
cd /path/to/agent-cron-server
pip install -e . 2>/dev/null
bash scripts/start.sh &
sleep 2
```

默认地址 `http://localhost:8900`，MCP Server 挂载在 `/mcp/`。

## MCP Tools Reference

本服务通过 MCP Server 暴露以下 tools，**直接调用即可，无需 HTTP 请求**：

| Tool | 说明 |
|------|------|
| `create_cron_task` | 创建定时任务 |
| `list_cron_tasks` | 列出任务（可按 enabled/owner_agent/tag 筛选） |
| `get_cron_task` | 查看任务详情 |
| `update_cron_task` | 更新任务配置 |
| `delete_cron_task` | 删除任务及所有执行历史 |
| `trigger_cron_task` | 手动立即触发任务 |
| `enable_cron_task` | 启用任务 |
| `disable_cron_task` | 禁用任务（保留配置） |
| `list_executions` | 查看执行记录（可按 task_id/status 筛选） |
| `get_execution` | 查看执行详情 |
| `get_execution_log` | 查看 stdout/stderr 输出 |
| `get_service_health` | 服务健康检查 |

## Procedure

### 1. Check Service

```
→ get_service_health()
← "Service: OK\nScheduler: running\nActive jobs: 3"
```

### 2. Create a Scheduled Task

```
→ create_cron_task(
    name="daily-report",
    command="python3 /path/to/report.py",
    cron_expression="0 9 * * *",
    description="Generate daily report",
    timezone="Asia/Shanghai",
    timeout=300
  )
← "Task created: id=1, name=daily-report, cron=0 9 * * *"
```

**必填参数**: `name`, `command`, `cron_expression`

**可选参数**:
- `description` — 任务描述
- `shell` — 是否 shell 模式（默认 true）
- `working_dir` — 工作目录
- `env_vars` — 环境变量，如 `{"KEY": "value"}`
- `timezone` — 时区（默认 `Asia/Shanghai`）
- `timeout` — 超时秒数（默认 3600）
- `max_retries` — 最大重试次数
- `owner_agent` — 所属 agent 标识
- `tags` — 标签列表，如 `["report", "daily"]`

### 3. Cron Expression Format

标准 5 字段 cron 表达式：

```
┌───────────── minute (0-59)
│ ┌───────────── hour (0-23)
│ │ ┌───────────── day of month (1-31)
│ │ │ ┌───────────── month (1-12)
│ │ │ │ ┌───────────── day of week (0-6, 0=Sunday)
│ │ │ │ │
* * * * *
```

常用示例：
- `*/5 * * * *` — 每 5 分钟
- `0 9 * * *` — 每天上午 9 点
- `0 9 * * 1-5` — 工作日上午 9 点
- `30 */2 * * *` — 每 2 小时的第 30 分钟

### 4. Monitor Execution

```
→ list_executions(task_id=1, limit=5)
← "Total: 3 records\n- [1] daily-report | success | manual | duration: 31ms ..."

→ get_execution(execution_id=1)
← "Execution #1\n  Task: daily-report (id=1)\n  Status: success\n  Duration: 31ms\n  ..."

→ get_execution_log(execution_id=1)
← "=== STDOUT ===\nReport generated successfully\n\n=== STDERR ===\n"
```

### 5. Manage Tasks

```
→ trigger_cron_task(task_id=1)        # 手动触发
→ disable_cron_task(task_id=1)        # 暂停调度（保留配置）
→ enable_cron_task(task_id=1)         # 恢复调度
→ update_cron_task(task_id=1, timeout=600)  # 修改配置
→ delete_cron_task(task_id=1)         # 删除任务及历史
```

## Common Workflows

### Schedule a Python script daily

```
→ create_cron_task(
    name="daily-cleanup",
    command="python3 /home/user/scripts/cleanup.py",
    cron_expression="0 2 * * *",
    working_dir="/home/user/scripts",
    timeout=600
  )
```

### Schedule with environment variables

```
→ create_cron_task(
    name="backup-db",
    command="pg_dump $DB_NAME > /backups/$(date +%Y%m%d).sql",
    cron_expression="0 3 * * 0",
    env_vars={"DB_NAME": "mydb", "PGPASSWORD": "secret"}
  )
```

### Check last execution and get output

```
→ list_executions(task_id=1, limit=1)
  # get the execution_id from result
→ get_execution_log(execution_id=3)
```

### List tasks by tag or owner

```
→ list_cron_tasks(tag="daily")
→ list_cron_tasks(owner_agent="hermes-agent")
→ list_cron_tasks(enabled=true)
```

## Pitfalls

- **Server not running**: 调用 tool 会报错。先 `get_service_health()` 检查，未运行则用 terminal 启动。
- **Cron expression**: 必须使用标准 5 字段格式，非法表达式会返回错误。
- **Command paths**: 使用绝对路径，避免子进程环境中 PATH 问题。
- **Timeout**: 长时间运行的脚本需设更大 `timeout`，超时状态为 "timeout"。
- **Timezone**: 默认 `Asia/Shanghai`，不同时区需显式指定。

## Verification

创建任务后验证是否正常工作：

```
→ get_service_health()                        # 1. 检查服务
→ trigger_cron_task(task_id=1)                # 2. 手动触发测试
→ list_executions(task_id=1, limit=1)         # 3. 查看执行结果
→ get_execution_log(execution_id=...)         # 4. 查看输出日志
```
