---
name: agent-cron
description: Scheduled task execution service — create, manage, and monitor cron tasks that run shell commands/scripts via MCP tools.
version: 0.4.0
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
> ✅ **正确**：通过 MCP tools（`mcp_acs_*` 前缀，Agent 内部直接调用）
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

agent-cron-server 必须运行中。使用前先通过 MCP tool `mcp_acs_get_service_health` 检查服务状态。

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

## MCP Server 配置

> **MCP 在 Hermes/OpenClaw config.yaml 中注册的 server 名称为 `acs`。**
>
> 注册后工具前缀为 **`mcp_acs_*`**（如 `mcp_acs_create_cron_task`）。
>
> 配置方式：
> ```yaml
> mcpServers:
>   acs:
>     transport: streamable-http
>     url: http://localhost:8900/mcp/
> ```

### ⚠️ 首次加载时：校验工具名称

加载本 skill 后，**必须先确认实际注册的 MCP 工具名称是否与本文档一致**：

1. 列出当前可用的 MCP 工具，找到以 `create_cron_task` 结尾的工具
2. 确认其完整前缀（可能是 `mcp_acs_`、`mcp_agent_cron_` 或其他）
3. 如果前缀**不是** `mcp_acs_`，则将本文档中所有 `mcp_acs_` 替换为实际前缀

**为什么要做这步？** 不同 agent 框架或不同配置中的 server 名称可能不同，导致工具前缀不一致。直接使用本文档中的名称调用会失败。以实际注册的工具名称为准。

### Hermes/OpenClaw 内部调用

Agent 运行时已自动连接 MCP Server，直接使用 `mcp_acs_*` 前缀调用即可：
- `mcp_acs_get_service_health` — 健康检查
- `mcp_acs_create_cron_task` — 创建任务
- `mcp_acs_list_cron_tasks` — 列出任务
- 等等（完整列表见下方 Tools Reference）

### mcporter CLI（调试/手动测试）

当 Agent 需要通过 terminal 调用 MCP tools（如子任务、调试时），使用 mcporter：

```bash
MCPORTER="npx mcporter call --allow-http --http-url http://localhost:8900/mcp/"

# 健康检查
$MCPORTER get_service_health

# 列出任务
$MCPORTER list_cron_tasks

# 创建任务（key=value 语法）
$MCPORTER create_cron_task name="daily-report" command="python3 /path/to/report.py" cron_expression="0 9 * * *" owner_agent="hermes"

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

> **Agent 内部调用时需加 `mcp_acs_` 前缀**，如 `mcp_acs_create_cron_task`。mcporter CLI 直接用原始名称。

| Tool（Agent 内部名称） | 说明 | 关键参数 |
|------|------|----------|
| `mcp_acs_get_service_health` | 服务健康检查 | 无 |
| `mcp_acs_create_cron_task` | 创建定时任务 | name, command, cron_expression, owner_agent (必填) |
| `mcp_acs_list_cron_tasks` | 列出任务 | enabled, owner_agent, tag (可选筛选) |
| `mcp_acs_get_cron_task` | 查看任务详情 | task_id |
| `mcp_acs_update_cron_task` | 更新任务配置 | task_id + 要更新的字段 |
| `mcp_acs_delete_cron_task` | 删除任务及历史 | task_id |
| `mcp_acs_trigger_cron_task` | 手动立即触发 | task_id |
| `mcp_acs_enable_cron_task` | 启用任务 | task_id |
| `mcp_acs_disable_cron_task` | 禁用任务（保留配置） | task_id |
| `mcp_acs_list_executions` | 查看执行记录 | task_id, status, limit (可选) |
| `mcp_acs_get_execution` | 查看执行详情 | execution_id |
| `mcp_acs_get_execution_log` | 查看 stdout/stderr | execution_id |

### mcp_acs_create_cron_task 完整参数

**必填**: `name`, `command`, `cron_expression`, `owner_agent`

**可选**:
- `description` — 任务描述
- `shell` — 是否 shell 模式（默认 true）
- `working_dir` — 工作目录
- `env_vars` — 环境变量，如 `{"KEY": "value"}`
- `timezone` — 时区（默认 `Asia/Shanghai`）
- `timeout` — 超时秒数（默认 3600）
- `max_retries` — 最大重试次数
- `callback_url` — 执行完成后回调通知地址（POST JSON）
- `callback_prompt` — 回调处理指令，告诉回调端如何处理该任务的结果
- `tags` — 标签列表，如 `["report", "daily"]`

## Procedure

### 1. Check Service

```
→ mcp_acs_get_service_health()
← "Service: OK\nScheduler: running\nActive jobs: 3"
```

### 2. Create a Scheduled Task

```
→ mcp_acs_create_cron_task(
    name="daily-report",
    command="python3 /path/to/report.py",
    cron_expression="0 9 * * *",
    owner_agent="hermes",
    description="Generate daily report",
    timezone="Asia/Shanghai",
    timeout=300
  )
← "Task created: id=1, name=daily-report, cron=0 9 * * *"
```

### 3. Monitor Execution

```
→ mcp_acs_list_executions(task_id=1, limit=5)
← "Total: 3 records\n- [1] daily-report | success | manual | duration: 31ms ..."

→ mcp_acs_get_execution(execution_id=1)
← "Execution #1\n  Task: daily-report (id=1)\n  Status: success\n  Duration: 31ms\n  ..."

→ mcp_acs_get_execution_log(execution_id=1)
← "=== STDOUT ===\nReport generated successfully\n\n=== STDERR ===\n"
```

### 4. Manage Tasks

```
→ mcp_acs_trigger_cron_task(task_id=1)        # 手动触发
→ mcp_acs_disable_cron_task(task_id=1)        # 暂停调度（保留配置）
→ mcp_acs_enable_cron_task(task_id=1)         # 恢复调度
→ mcp_acs_update_cron_task(task_id=1, timeout=600)  # 修改配置
→ mcp_acs_delete_cron_task(task_id=1)         # 删除任务及历史
```

## 日志记录机制

每次任务执行时，服务的调度器会捕获子进程的 **stdout** 和 **stderr**，分别存储到按日期归档的日志文件中（`data/logs/YYYY-MM-DD/task_{id}_{exec_id}_{stdout|stderr}.log`）。

### stdout 与 stderr 的正确使用

编写定时任务脚本时，应遵循 Unix 惯例区分 stdout 和 stderr：

| 流 | 用途 | 示例 |
|----|------|------|
| **stdout** | 正常输出：脚本结果、数据、处理摘要 | `print("Report: 42 items processed")` |
| **stderr** | 诊断信息：警告、错误、调试日志 | `print("Warning: file not found", file=sys.stderr)` |

### 脚本编写规范

**Python 脚本示例**：

```python
import sys

# 正常结果输出到 stdout
print("✅ Report generated: 42 items, total $12,340")

# 警告和错误输出到 stderr
if missing_files:
    print(f"⚠ Warning: {len(missing_files)} files skipped", file=sys.stderr)

# 发生错误时，错误信息写 stderr，然后用非零 exit code 退出
try:
    result = do_work()
except Exception as e:
    print(f"❌ Error: {e}", file=sys.stderr)
    sys.exit(1)
```

**Shell 脚本示例**：

```bash
# 正常输出 → stdout
echo "Backup completed: 120MB"

# 警告/错误 → stderr (>&2)
echo "Warning: disk usage at 85%" >&2

# 错误时非零退出
if ! curl -s "$URL" > /dev/null; then
  echo "Error: failed to reach $URL" >&2
  exit 1
fi
```

### 执行状态说明

| Status | 含义 |
|--------|------|
| `success` | 进程正常执行并退出（任何 exit code） |
| `timeout` | 进程超过 `timeout` 秒被强制终止 |
| `failed` | 进程启动失败或抛出未捕获异常 |

`exit_code` 字段记录进程的退出码。脚本可通过 `exit 0`/`exit 1` 等传递业务状态，但不会影响 execution 的 status 字段。

### 日志查看

```
→ mcp_acs_get_execution_log(execution_id=1)
← "=== STDOUT ===\nReport generated: 42 items\n\n=== STDERR ===\n"
```

- 日志按日期目录存储，超过 `LOG_RETENTION_DAYS`（默认 30 天）自动清理
- 单条日志上限 `LOG_MAX_SIZE`（默认 1MB），超出部分自动截断

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

- **⛔ 禁止 curl/API**：不要使用 `curl http://localhost:8900/api/v1/...`，不要用 Python `urllib`/`requests` 调 REST API。必须通过 MCP tools 交互。
- **工具名称前缀**：Agent 内部调用时必须使用 `mcp_acs_` 前缀（如 `mcp_acs_create_cron_task`），mcporter CLI 使用原始名称。
- **mcp_acs_update_cron_task 只传需要更新的字段**：FastMCP 会把所有参数（包括 None）传给工具函数，导致 Pydantic `model_dump(exclude_unset=True)` 失效、NOT NULL 冲突。已修复：只传非 None 字段给 `TaskUpdate`。但如果将来 schema 变动，注意此陷阱。
- **Callback 401 错误**：回调目标如果是 Hermes webhook，必须配置 `ACS_CALLBACK_SECRET` 并匹配 webhook 订阅的 secret，否则返回 401 Unauthorized。
- **Server not running**: MCP tool 调用会报错。先 `mcp_acs_get_service_health()` 检查，未运行则用 terminal 启动。
- **Cron expression**: 必须使用标准 5 字段格式，非法表达式会返回错误。
- **Command paths**: 使用绝对路径，避免子进程环境中 PATH 问题。
- **Timeout**: 长时间运行的脚本需设更大 `timeout`，超时状态为 "timeout"。
- **Timezone**: 默认 `Asia/Shanghai`，不同时区需显式指定。
- **Callback**: `callback_url` 必须是可访问的 HTTP(S) URL，服务会 POST JSON。回调失败不会影响任务执行结果。stdout/stderr 摘要限制 4096 字符。

## Callback 通知机制

创建任务时可指定 `callback_url`，任务执行完成后服务会向该 URL 发送 POST 请求，携带执行结果 JSON。

### 使用场景

- Agent 提交定时任务后，执行完成自动收到通知，无需轮询
- 与 OpenClaw Gateway 集成：POST 到 Gateway webhook 触发后续 agent 处理
- 与企业 IM 集成：POST 到 Webhook Bot 发送执行结果通知

### 创建带回调的任务

```
→ mcp_acs_create_cron_task(
    name="daily-report",
    command="python3 /path/to/report.py",
    cron_expression="0 9 * * *",
    owner_agent="hermes",
    callback_url="https://your-gateway.example.com/hooks/cron-done"
  )
```

### 回调 Payload 格式

任务执行完成后，服务向 `callback_url` 发送如下 JSON（`Content-Type: application/json`）：

```json
{
  "task_id": 1,
  "task_name": "daily-report",
  "execution_id": 42,
  "status": "success",
  "exit_code": 0,
  "duration_ms": 1230,
  "started_at": "2026-04-18T09:00:00",
  "finished_at": "2026-04-18T09:00:01",
  "trigger_type": "cron",
  "error_message": null,
  "stdout_summary": "Report generated: 42 items...",
  "stderr_summary": ""
}
```

| 字段 | 说明 |
|------|------|
| `task_id` | 任务 ID |
| `task_name` | 任务名称 |
| `execution_id` | 执行记录 ID |
| `status` | 执行状态：`success` / `timeout` / `failed` |
| `exit_code` | 进程退出码（`null` 表示启动失败） |
| `duration_ms` | 执行耗时毫秒数 |
| `started_at` | 开始时间（ISO 8601） |
| `finished_at` | 结束时间（ISO 8601） |
| `trigger_type` | 触发类型：`cron` / `manual` |
| `error_message` | 错误信息（仅 `timeout`/`failed`） |
| `stdout_summary` | stdout 输出（截断至 4096 字符） |
| `stderr_summary` | stderr 输出（截断至 4096 字符） |

### Hermes Webhook 回调集成

ACS 回调 → Hermes gateway webhook → Agent 分析处理 → 微信推送 的完整链路。

> **⚠️ 关键原则：回调不是转发器！**
> Agent 收到回调后应**真正分析数据**（用 read_file 读文件、用 send_message 推送），
> 而不是简单模板匹配转发。脚本已自行推送的任务应静默，只有需要 Agent 处理的任务才触发分析。
> 否则 callback 就没有存在的意义——脚本可以直接调用渠道发送。

#### 1. 创建 Hermes Webhook 订阅

**⚠️ 重要：用 shell 变量传入 prompt，不要用 `read_file` 读取后传入（会带行号前缀 `     1|`）**

Prompt 模板文件位于 `skill/templates/acs-callback-prompt.txt`，修改任务规则时编辑该文件即可。

```bash
# 直接引用模板文件（prompt 内容在 skill/templates/acs-callback-prompt.txt 中维护）
PROMPT=$(cat skill/templates/acs-callback-prompt.txt)
hermes webhook subscribe acs-callback \
  --prompt "$PROMPT" \
  --secret "<your-secret>" \
  --deliver weixin \
  --description "Agent-Cron-Server 任务回调（智能分析）"
```

#### Prompt 设计原则

1. **区分"已推送"和"需分析"的任务**：脚本已自行调用 send_message 的任务，callback 只需静默或确认
2. **指导 Agent 用工具**：需要分析的任务，明确告诉 Agent 用 `read_file` 读数据文件、用 `send_message` 推送
3. **明确"不发消息"条件**：正常静默任务要写清楚不发消息，避免 Agent 每次都发无意义确认
4. **异常必须通知**：exit_code 异常、超时、失败都要通知

> Hermes gateway 的 webhook handler 调用 `handle_message(event)`，
> Agent **拥有完整工具调用能力**（read_file, send_message, terminal 等），
> prompt 应充分利用这一点让 Agent 真正处理数据。

#### 2. 配置 HMAC 签名

Hermes webhook 要求 HMAC-SHA256 签名验证。ACS 已内置签名支持：

`.env` 中设置 secret（与 Hermes webhook 订阅的 secret 一致）：
```
ACS_CALLBACK_SECRET=<hermes-webhook-secret>
```

签名通过 `X-Webhook-Signature` header 传递，Hermes 使用 Generic HMAC 模式验证。

#### 3. 给任务设置 callback_url

```
→ mcp_acs_update_cron_task(task_id=4, callback_url="http://localhost:8644/webhooks/acs-callback")
```

#### 4. 触发测试

```
→ mcp_acs_trigger_cron_task(task_id=4)
# 检查日志确认回调成功
# 期望: "Callback sent to ... HTTP 202"
```

### 注意事项

- 回调超时 10 秒，失败只记录 warning 日志，不影响任务执行
- stdout/stderr 摘要最多 4096 字符，完整日志通过 `mcp_acs_get_execution_log` 获取
- `callback_url` 可通过 `mcp_acs_update_cron_task` 随时修改或清除
- **HMAC 签名必须配置**，否则 Hermes gateway 返回 401 Unauthorized
- Hermes webhook secret 在 `hermes webhook subscribe` 时生成，查看用 `hermes webhook list`
- **更新 webhook prompt 时**：先 `hermes webhook remove acs-callback` 再重新 subscribe，不要尝试原地修改

## Verification

创建任务后验证是否正常工作：

```
→ mcp_acs_get_service_health()                        # 1. 检查服务
→ mcp_acs_trigger_cron_task(task_id=1)                # 2. 手动触发测试
→ mcp_acs_list_executions(task_id=1, limit=1)         # 3. 查看执行结果
→ mcp_acs_get_execution_log(execution_id=...)         # 4. 查看输出日志
```
