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
User=www-data
WorkingDirectory=/opt/agent-cron-server
ExecStart=/opt/agent-cron-server/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8900
Restart=always
RestartSec=5
Environment=ACS_LOG_RETENTION_DAYS=30

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable agent-cron-server
sudo systemctl start agent-cron-server
```

---

## REST API

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

### 示例

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

## MCP Server

agent-cron-server 通过 MCP（Model Context Protocol）暴露给 AI Agent。

### 连接地址

```
http://localhost:8900/mcp/
```

### 可用 Tools

| Tool | 说明 |
|------|------|
| `create_cron_task` | 创建定时任务 |
| `list_cron_tasks` | 列出任务 |
| `get_cron_task` | 获取任务详情 |
| `update_cron_task` | 更新任务 |
| `delete_cron_task` | 删除任务 |
| `trigger_cron_task` | 手动触发 |
| `enable_cron_task` | 启用任务 |
| `disable_cron_task` | 禁用任务 |
| `list_executions` | 查看执行记录 |
| `get_execution` | 获取执行详情 |
| `get_execution_log` | 获取执行日志 |
| `get_service_health` | 服务健康状态 |

---

## Skill 安装

agent-cron-server 附带一个兼容 Hermes 和 OpenClaw 的 Skill，让 Agent 能直接管理定时任务。

### Hermes Agent

**方式一：本地安装（开发）**

将 `skill/` 目录复制到 Hermes 的 skills 目录：

```bash
# 官方 skills 目录
cp -r skill/ ~/.hermes/skills/agent-cron/

# 或项目级 skills 目录
cp -r skill/ your-project/.agents/skills/agent-cron/
```

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
  agent-cron:
    transport: streamable-http
    url: http://localhost:8900/mcp/
```

### OpenClaw

**方式一：本地安装**

将 `skill/` 目录放到 OpenClaw 的 skills 目录：

```bash
# 用户级
cp -r skill/ ~/.openclaw/skills/agent-cron/

# 项目级
cp -r skill/ your-project/.agents/skills/agent-cron/

# 工作区级
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
  agent-cron:
    transport: streamable-http
    url: http://localhost:8900/mcp/
```

### Skill 加载优先级

| 优先级 | Hermes 路径 | OpenClaw 路径 |
|--------|-------------|---------------|
| 最高 | `skills/agent-cron/` | `skills/agent-cron/` |
| 高 | `.agents/skills/agent-cron/` | `.agents/skills/agent-cron/` |
| 中 | `~/.hermes/skills/agent-cron/` | `~/.openclaw/skills/agent-cron/` |
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
