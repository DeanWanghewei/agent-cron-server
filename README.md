# Agent Cron Server

定时任务调度服务，为 AI Agent（hermes-agent / openclaw）提供 cron 任务管理能力。

通过 REST API 和 MCP Server 暴露服务，支持创建/管理定时任务、执行脚本、查看执行记录和日志。内置 Web UI Dashboard。

---

## 功能特性

- 定时任务 CRUD（创建/查询/更新/删除）
- 标准 5 字段 cron 表达式调度（APScheduler）
- Shell 命令/脚本执行，支持环境变量和工作目录
- 执行记录和日志查看（stdout/stderr 分离存储到文件）
- MCP Server（StreamableHTTP）供 AI Agent 直接调用
- REST API 供第三方集成
- Web UI Dashboard（支持暗黑/浅色/系统主题）
- 日志按日期目录存储，支持自动过期清理
- SQLite（开发）/ PostgreSQL（生产）可插拔数据库

---

## 快速开始

### 安装

```bash
# 克隆项目
git clone <repo-url> agent-cron-server
cd agent-cron-server

# 创建虚拟环境（推荐）
python -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -e .

# 开发依赖（可选）
pip install -e ".[dev]"
```

### 配置

```bash
# 复制配置文件
cp .env.example .env

# 按需编辑
vim .env
```

配置项（均可通过环境变量 `ACS_` 前缀覆盖）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ACS_DATABASE_URL` | `sqlite+aiosqlite:///./data/cron.db` | 数据库连接串 |
| `ACS_HOST` | `0.0.0.0` | 监听地址 |
| `ACS_PORT` | `8900` | 监听端口 |
| `ACS_DEBUG` | `false` | 调试模式 |
| `ACS_LOG_LEVEL` | `INFO` | 日志级别 |
| `ACS_SCHEDULER_TIMEZONE` | `Asia/Shanghai` | 调度器时区 |
| `ACS_DEFAULT_TASK_TIMEOUT` | `3600` | 任务默认超时（秒） |
| `ACS_LOG_MAX_SIZE` | `10485760` | 单次日志最大尺寸（字节） |
| `ACS_LOG_DIR` | `data/logs` | 日志文件存储目录 |
| `ACS_LOG_RETENTION_DAYS` | `30` | 日志保留天数（0=永不清理） |
| `ACS_MCP_MOUNT_PATH` | `/mcp` | MCP Server 挂载路径 |
| `ACS_CALLBACK_SECRET` | _(空)_ | 回调 HMAC-SHA256 签名密钥 |

### 启动

```bash
# 方式一：启动脚本
bash scripts/start.sh

# 方式二：直接运行
uvicorn app.main:app --host 0.0.0.0 --port 8900

# 方式三：开发模式（自动重载）
uvicorn app.main:app --host 0.0.0.0 --port 8900 --reload
```

启动后访问：
- Web Dashboard: http://localhost:8900/dashboard/
- REST API: http://localhost:8900/api/v1/
- MCP Server: http://localhost:8900/mcp/
- 健康检查: http://localhost:8900/health

---

## 部署

### Docker 部署（推荐）

创建 `Dockerfile`：

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -e .

RUN mkdir -p /app/data/logs

EXPOSE 8900

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8900"]
```

构建并运行：

```bash
docker build -t agent-cron-server .

docker run -d \
  --name cron-server \
  -p 8900:8900 \
  -v $(pwd)/data:/app/data \
  -e ACS_DATABASE_URL=sqlite+aiosqlite:///./data/cron.db \
  agent-cron-server
```

### Docker Compose

```yaml
version: "3.8"
services:
  cron-server:
    build: .
    ports:
      - "8900:8900"
    volumes:
      - ./data:/app/data
    environment:
      - ACS_DATABASE_URL=sqlite+aiosqlite:///./data/cron.db
      - ACS_LOG_RETENTION_DAYS=30
      - ACS_SCHEDULER_TIMEZONE=Asia/Shanghai
    restart: unless-stopped
```

### PostgreSQL 生产部署

```yaml
version: "3.8"
services:
  cron-server:
    build: .
    ports:
      - "8900:8900"
    volumes:
      - ./data/logs:/app/data/logs
    environment:
      - ACS_DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/cron
      - ACS_LOG_RETENTION_DAYS=30
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: cron
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

### Systemd（Linux 裸机部署）

创建 `/etc/systemd/system/agent-cron-server.service`：

```ini
[Unit]
Description=Agent Cron Server
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/agent-cron-server
ExecStart=/opt/agent-cron-server/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8900
Restart=always
RestartSec=5
EnvironmentFile=/opt/agent-cron-server/.env

[Install]
WantedBy=multi-user.target
```

> 💡 以上示例以 root 用户运行。如需以非 root 用户运行，添加 `User=your-user` 并确保该用户对 `data/` 目录有读写权限。

```bash
sudo systemctl daemon-reload
sudo systemctl enable agent-cron-server
sudo systemctl start agent-cron-server
```

---

## 与 AI Agent 交互（MCP — 推荐方式）

> **⚠️ 重要：AI Agent 应通过 MCP Tools 与本服务交互，不要使用 REST API。**
>
> 本服务已在 Hermes/OpenClaw 的 `config.yaml` 中配置为 MCP Server：
> ```yaml
> mcpServers:
>   mcp_acs:
>     transport: streamable-http
>     url: http://localhost:8900/mcp/
> ```
>
> 注册后工具前缀为 **`mcp_acs_*`**（如 `mcp_acs_create_cron_task`）。Agent 可直接调用，**无需 curl、无需 HTTP 请求**：

### MCP Tools 一览

| Tool | 说明 |
|------|------|
| `create_cron_task` | 创建定时任务 |
| `list_cron_tasks` | 列出任务（可按 enabled/owner_agent/tag 筛选） |
| `get_cron_task` | 获取任务详情 |
| `update_cron_task` | 更新任务 |
| `delete_cron_task` | 删除任务及所有执行历史 |
| `trigger_cron_task` | 手动触发 |
| `enable_cron_task` | 启用任务 |
| `disable_cron_task` | 禁用任务 |
| `list_executions` | 查看执行记录（可按 task_id/status 筛选） |
| `get_execution` | 获取执行详情 |
| `get_execution_log` | 获取执行日志（stdout/stderr） |
| `get_service_health` | 服务健康状态 |

### MCP 调用示例（mcporter CLI）

```bash
# 健康检查
mcporter call --allow-http --http-url http://localhost:8900/mcp/ get_service_health

# 列出所有任务
mcporter call --allow-http --http-url http://localhost:8900/mcp/ list_cron_tasks

# 创建任务
mcporter call --allow-http --http-url http://localhost:8900/mcp/ create_cron_task \
  name="daily-backup" \
  command="/opt/scripts/backup.sh" \
  cron_expression="0 2 * * *"

# 手动触发
mcporter call --allow-http --http-url http://localhost:8900/mcp/ trigger_cron_task task_id=1

# 查看执行日志
mcporter call --allow-http --http-url http://localhost:8900/mcp/ get_execution_log execution_id=1
```

> Hermes/OpenClaw 的 AI Agent 会自动通过内部 MCP client 调用这些 tools，
> 无需手动使用 mcporter。以上 CLI 示例仅用于调试和手动测试。

---

## 任务执行回调（Callback）

任务执行完成后可自动回调指定 URL，将执行结果以 JSON POST 方式推送。适用于：
- 接入 AI Agent（如 Hermes）的 webhook，任务完成后自动通知
- 对接企业 IM（飞书、钉钉）、监控系统等
- 触发下游工作流

### 开启回调

**1. 为任务设置 `callback_url`**

通过 MCP 或 REST API 更新任务：

```bash
# MCP 方式（推荐）
mcporter call --allow-http --http-url http://localhost:8900/mcp/ update_cron_task \
  task_id=1 callback_url="http://localhost:8644/webhooks/my-callback"

# REST API 方式
curl -X PUT localhost:8900/api/v1/tasks/1 \
  -H 'Content-Type: application/json' \
  -d '{"callback_url": "http://localhost:8644/webhooks/my-callback"}'
```

**2. （可选）配置 HMAC 签名密钥**

如果你的回调端点需要签名验证（推荐），在 `.env` 中配置：

```bash
ACS_CALLBACK_SECRET=your-hmac-secret-here
```

配置后，回调请求会自动携带 `X-Webhook-Signature` 头（HMAC-SHA256），格式为 hex 摘要。

> ⚠️ 不配置密钥则回调请求不带签名。如果你的回调端点强制验签，未配置密钥会导致 `401 Unauthorized`。

**3. 验证端接收**

回调端点需要接受 `POST` 请求，请求体为 JSON：

```json
{
  "task_id": 1,
  "task_name": "daily-backup",
  "execution_id": 42,
  "status": "success",
  "exit_code": 0,
  "duration_ms": 1234,
  "started_at": "2026-04-18T09:00:00+08:00",
  "finished_at": "2026-04-18T09:00:01+08:00",
  "trigger_type": "cron",
  "error_message": null,
  "stdout_summary": "...(前 4096 字符)",
  "stderr_summary": "",
  "callback_prompt": "脚本已完成，请检查执行结果并通知用户。"
}
```

> 💡 `callback_prompt` 是可选字段，来自任务的 `callback_prompt` 属性。如果任务未设置，值为 `null`。详见下方「Hermes Webhook 集成」。

签名验证伪代码：

```python
import hmac, hashlib
expected = hmac.new(SECRET.encode(), request_body, hashlib.sha256).hexdigest()
assert request.headers["X-Webhook-Signature"] == expected
```

### 与 Hermes Webhook 集成

如果回调目标是 Hermes Agent 的 webhook 订阅：

```bash
# 1. 创建 Hermes webhook 订阅
#    prompt 中可使用 {dot.notation} 引用 payload 字段
#    {callback_prompt} 会被替换为任务级别的指令
hermes webhook subscribe my-callback \
  --prompt "{callback_prompt}\n\n## 执行结果\n- 任务: {task_name}（ID: {task_id}）\n- 状态: {status}（退出码: {exit_code}）\n- 耗时: {duration_ms}ms\n\n## 执行输出\n{stdout_summary}" \
  --deliver weixin

# 2. 记下输出的 Secret 和 URL

# 3. 在 .env 中配置相同的密钥
echo "ACS_CALLBACK_SECRET=<hermes输出的secret>" >> .env

# 4. 重启服务
sudo systemctl restart agent-cron-server
```

> 💡 Hermes webhook 支持 GitHub（`X-Hub-Signature-256`）、GitLab（`X-Gitlab-Token`）和通用（`X-Webhook-Signature`）三种签名格式，ACS 使用通用格式。

#### Per-Task Callback Prompt（推荐）

每个任务可以设置专属的 `callback_prompt`，告诉回调端（如 Hermes Agent）如何处理该任务的执行结果：

```bash
# 创建时指定
mcporter call --allow-http --http-url http://localhost:8900/mcp/ create_cron_task \
  name="news-fetch" \
  command="/opt/scripts/fetch_news.sh" \
  cron_expression="0 8 * * *" \
  callback_url="http://localhost:8644/webhooks/my-callback" \
  callback_prompt="脚本只采集写JSON不推送。用read_file读/data/app/news/今天JSON，挑AI/科技5-8条，用send_message发微信。"

# 更新已有任务的 callback_prompt
mcporter call --allow-http --http-url http://localhost:8900/mcp/ update_cron_task \
  task_id=1 \
  callback_prompt="脚本已自行推送微信。正常完成不发消息。仅异常时通知。"
```

**设计思路：**

- **不需要 Agent 分析的任务**（如脚本自行推送微信）：设为 `正常完成不发消息，仅异常通知`
- **需要 Agent 处理的任务**（如采集数据待分析）：设为具体指令，如 `用read_file读数据，筛选后send_message推送`
- Webhook 订阅的 prompt 模板用 `{callback_prompt}` 占位，ACS 会在 payload 中传入任务级别的 prompt
- 这样一个 webhook 订阅就能服务所有任务，由每个任务自己决定 Agent 该做什么

---

## REST API（备选，非 AI Agent 场景）

> **提示**：如果你是 AI Agent，请使用上方的 MCP Tools，不要使用 REST API。

REST API 主要供第三方系统集成、脚本、Web UI 等非 Agent 场景使用。

所有接口前缀 `/api/v1`。

### 任务管理

```
POST   /tasks                     创建任务
GET    /tasks                     任务列表（分页）
GET    /tasks/{id}                任务详情
PUT    /tasks/{id}                更新任务
DELETE /tasks/{id}                删除任务
POST   /tasks/{id}/trigger        手动触发
POST   /tasks/{id}/enable         启用
POST   /tasks/{id}/disable        禁用
```

### 执行记录

```
GET    /executions                执行列表（分页）
GET    /executions/{id}           执行详情
GET    /executions/{id}/log       执行日志（stdout/stderr）
DELETE /executions/{id}           删除记录
```

### REST API 示例

```bash
# 创建任务
curl -X POST localhost:8900/api/v1/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "daily-backup",
    "command": "/opt/scripts/backup.sh",
    "cron_expression": "0 2 * * *",
    "timezone": "Asia/Shanghai",
    "timeout": 600
  }'

# 手动触发
curl -X POST localhost:8900/api/v1/tasks/1/trigger

# 查看执行日志
curl localhost:8900/api/v1/executions/1/log
```

---

## Skill 安装

agent-cron-server 附带一个兼容 Hermes 和 OpenClaw 的 Skill，让 Agent 能直接管理定时任务。

### Hermes Agent

**方式一：本地安装（开发）**

将 `skill/` 目录的内容复制到 Hermes 的 skills 目录：

```bash
# 确保 acs 目录不存在，避免 cp 产生嵌套
rm -rf ~/.hermes/skills/acs
cp -r skill/ ~/.hermes/skills/acs/

# 或项目级 skills 目录
rm -rf your-project/.agents/skills/acs
cp -r skill/ your-project/.agents/skills/acs/
```

> ⚠️ 如果目标目录已存在，`cp -r skill/ target/` 会把整个 `skill/` 作为子目录拷进去（变成 `target/skill/SKILL.md`），导致无法识别。务必先删除目标目录或使用 `cp -r skill/* target/`。

**方式二：Skills Hub 发布**

```bash
# 发布到 GitHub 仓库
hermes skills publish skill/ --to github --repo your-org/agent-cron-skills

# 用户安装
hermes skills install your-org/agent-cron-skills
```

**方式三：配置 MCP 直连（推荐，无需 Skill 文件）**

在 `~/.hermes/config.yaml` 或项目 `.agents/config.yaml` 中添加：

```yaml
mcpServers:
  mcp_acs:
    transport: streamable-http
    url: http://localhost:8900/mcp/
```

### OpenClaw

**方式一：本地安装**

将 `skill/` 目录的内容放到 OpenClaw 的 skills 目录：

```bash
# 用户级（确保目标目录不存在，避免嵌套）
rm -rf ~/.openclaw/skills/agent-cron
cp -r skill/ ~/.openclaw/skills/agent-cron/

# 项目级
rm -rf your-project/.agents/skills/agent-cron
cp -r skill/ your-project/.agents/skills/agent-cron/

# 工作区级
rm -rf your-project/skills/agent-cron
cp -r skill/ your-project/skills/agent-cron/
```

**方式二：ClawHub 发布**

```bash
openclaw skills publish skill/
```

**方式三：配置 MCP 直连**

在 OpenClaw 配置中添加 MCP Server：

```yaml
mcpServers:
  mcp_acs:
    transport: streamable-http
    url: http://localhost:8900/mcp/
```

### Skill 加载优先级

| 优先级 | Hermes 路径 | OpenClaw 路径 |
|--------|-------------|---------------|
| 最高 | `skills/acs/` | `skills/acs/` |
| 高 | `.agents/skills/acs/` | `.agents/skills/acs/` |
| 中 | `~/.hermes/skills/acs/` | `~/.openclaw/skills/acs/` |
| 低 | Bundled skills | Bundled skills |

---

## 日志存储

执行日志按日期目录存储在磁盘，数据库仅保存文件路径。

```
data/logs/
└── 2026-04-17/
    ├── task_1_1_stdout.log
    ├── task_1_1_stderr.log
    └── task_2_3_stdout.log
```

- **手动清理**：`rm -rf data/logs/2026-04-*` 按月删除
- **自动清理**：启动时根据 `ACS_LOG_RETENTION_DAYS` 自动删除过期目录
- **禁用自动清理**：`ACS_LOG_RETENTION_DAYS=0`

---

## 项目结构

```
agent-cron-server/
├── app/
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # 配置（ACS_ 前缀）
│   ├── database.py             # 异步数据库
│   ├── models/                 # ORM 模型
│   │   ├── task.py             # CronTask
│   │   ├── execution.py        # ExecutionRecord
│   │   └── log.py              # ExecutionLog（文件路径）
│   ├── schemas/                # Pydantic 模型
│   ├── api/                    # REST API 路由
│   ├── services/               # 业务逻辑层
│   ├── scheduler/              # APScheduler + Runner
│   ├── mcp_server/             # MCP Tools（FastMCP）
│   └── static/                 # Web UI Dashboard
├── skill/                      # Hermes/OpenClaw Skill
│   ├── SKILL.md
│   └── scripts/cron.sh
├── scripts/start.sh
├── data/                       # SQLite + 日志文件
├── pyproject.toml
└── .env.example
```

---

## License

MIT
