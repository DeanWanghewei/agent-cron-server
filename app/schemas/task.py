from datetime import datetime

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = None
    command: str
    shell: bool = True
    working_dir: str | None = Field(None, max_length=512)
    env_vars: dict[str, str] | None = None
    cron_expression: str = Field(..., max_length=100)
    timezone: str = "Asia/Shanghai"
    enabled: bool = True
    timeout: int = 3600
    max_retries: int = 0
    owner_agent: str | None = Field(None, max_length=100)
    tags: list[str] | None = None


class TaskUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    command: str | None = None
    shell: bool | None = None
    working_dir: str | None = Field(None, max_length=512)
    env_vars: dict[str, str] | None = None
    cron_expression: str | None = Field(None, max_length=100)
    timezone: str | None = None
    enabled: bool | None = None
    timeout: int | None = None
    max_retries: int | None = None
    owner_agent: str | None = Field(None, max_length=100)
    tags: list[str] | None = None


class TaskRead(BaseModel):
    id: int
    name: str
    description: str | None
    command: str
    shell: bool
    working_dir: str | None
    env_vars: dict | None
    cron_expression: str
    timezone: str
    enabled: bool
    timeout: int
    max_retries: int
    owner_agent: str | None
    tags: list | None
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}
