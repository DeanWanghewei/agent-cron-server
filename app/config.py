from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "agent-cron-server"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/cron.db"
    DB_ECHO: bool = False

    # Scheduler
    SCHEDULER_TIMEZONE: str = "Asia/Shanghai"
    SCHEDULER_MISFIRE_GRACE_TIME: int = 60
    SCHEDULER_COALESCE: bool = True

    # Runner
    DEFAULT_TASK_TIMEOUT: int = 3600
    LOG_MAX_SIZE: int = 10 * 1024 * 1024  # 10MB per execution log
    LOG_DIR: str = "data/logs"             # Directory for execution log files
    LOG_RETENTION_DAYS: int = 30           # Auto-delete logs older than N days (0=never)

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8900

    # MCP
    MCP_MOUNT_PATH: str = "/mcp"

    model_config = {"env_file": ".env", "env_prefix": "ACS_"}


settings = Settings()
