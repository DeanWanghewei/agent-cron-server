---
name: agent-cron
description: Scheduled task execution service — create, manage, and monitor cron tasks that run shell commands/scripts via MCP tools.
version: 0.2.0
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
---

# Agent Cron Server

定时任务调度服务，通过 MCP tools 管理定时执行的 shell 命令/脚本、查看执行记录和日志。

## ⛔ 核心规则：必须使用 MCP Tools，禁止 curl/API

> **本服务已配置为 MCP Server（streamable-http），所有操作必须通过 MCP tools 完成。**
>
> ✅ **正确**：通过 MCP tools（Hermes 内部 MCP client 或 mcporter CLI）
>
> ❌ **错误**：`curl http://localhost:8900/api/v1/...`、`urllib.request`、任何 HTTP API 调用
>
> MCP Server 地址：`http://localhost:8900/mcp/`

## When to Use

- 用户要求定时执行任务（如"每天早上9点运行这个脚本"）
- 用户想自动化周期性命令或脚本
- 用户提到 cron job、定时任务、周期执行
- 用户想查看某个已调度任务的执行状态或输出

## Prerequisites

agent-cron-server 必须运行中。使用前先通过 MCP tool `get_service_health` 检查服务状态。

如果服务未运行，优先通过 systemd 启动：

```bash
systemctl start agent-cron-server
sleep 2
```

若未注册 systemd，手动启动：

```bash
cd /path/to/agent-cron-server
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8900 &
sleep 2
```

## How to Call MCP Tools

### 方式一：Hermes/OpenClaw 内部 MCP Client（Agent 首选）

Agent 运行时已自动连接 MCP Server，可直接调用 tools。调用方式取决于 Agent 的内部集成：
- Hermes：tools 会自动注册为 `mcp_agent_cron_*` 前缀，直接在对话中调用即可
- OpenClaw：类似，通过 MCP client 自动发现

### 方式二：mcporter CLI（调试/手动测试）

当 Agent 需要通过 terminal 调用 MCP tools（如子任务、调试时），使用 mcporter：

```bash
MCPORTER="npx mcporter call --allow-http --http-url http://localhost:8900/mcp/"

# 健康检查
$MCPORTER get_service_health

# 列出任务
$MCPORTER list_cron_tasks

# 创建任务（key=value 语法）
$MCPORTER create_cron_task name="daily-report" command="python3 /path/to/report.py" cron_expression="0 9 * * *"

# 手动触发
$MCPORTER trigger_cron_task task_id=1

# 查看执行日志
$MCPORTER get_execution_log execution_id=1
```

JSON 输出（推荐用于脚本解析）：

```bash
$MCPORTER list_cron_tasks --output json
```

## MCP Tools Reference

| Tool | 说明 | 关键参数 |
|------|------|----------|
| `get_service_health` | 服务健康检查 | 无 |
| `create_cron_task` | 创建定时任务 | name, command, cron_expression (必填) |
| `list_cron_tasks` | 列出任务 | enabled, owner_agent, tag (可选筛选) |
| `get_cron_task` | 查看任务详情 | task_id |
| `update_cron_task` | 更新任务配置 | task_id + 要更新的字段 |
| `delete_cron_task` | 删除任务及历史 | task_id |
| `trigger_cron_task` | 手动立即触发 | task_id |
| `enable_cron_task` | 启用任务 | task_id |
| `disable_cron_task` | 禁用任务（保留配置） | task_id |
| `list_executions` | 查看执行记录 | task_id, status, limit (可选) |
| `get_execution` | 查看执行详情 | execution_id |
| `get_execution_log` | 查看 stdout/stderr | execution_id |

### create_cron_task 完整参数

**必填**: `name`, `command`, `cron_expression`

**可选**:
- `description` — 任务描述
- `shell` — 是否 shell 模式（默认 true）
- `working_dir` — 工作目录
- `env_vars` — 环境变量，如 `{"KEY": "value"}`
- `timezone` — 时区（默认 `Asia/Shanghai`）
- `timeout` — 超时秒数（默认 3600）
- `max_retries` — 最大重试次数
- `owner_agent` — 所属 agent 标识
- `tags` — 标签列表，如 `["report", "daily"]`

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

### 3. Monitor Execution

```
→ list_executions(task_id=1, limit=5)
← "Total: 3 records\n- [1] daily-report | success | manual | duration: 31ms ..."

→ get_execution(execution_id=1)
← "Execution #1\n  Task: daily-report (id=1)\n  Status: success\n  Duration: 31ms\n  ..."

→ get_execution_log(execution_id=1)
← "=== STDOUT ===\nReport generated successfully\n\n=== STDERR ===\n"
```

### 4. Manage Tasks

```
→ trigger_cron_task(task_id=1)        # 手动触发
→ disable_cron_task(task_id=1)        # 暂停调度（保留配置）
→ enable_cron_task(task_id=1)         # 恢复调度
→ update_cron_task(task_id=1, timeout=600)  # 修改配置
→ delete_cron_task(task_id=1)         # 删除任务及历史
```

## Cron Expression Format

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

## Pitfalls

- **⛔ 禁止 curl/API**：不要使用 `curl http://localhost:8900/api/v1/...`，不要用 Python `urllib`/`requests` 调 REST API。必须通过 MCP tools 交互（内部 MCP client 或 mcporter CLI）。
- **Server not running**: MCP tool 调用会报错。先 `get_service_health()` 检查，未运行则用 terminal 启动。
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
