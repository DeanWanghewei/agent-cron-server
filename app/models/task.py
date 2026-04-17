from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CronTask(Base):
    __tablename__ = "cron_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # What to run
    command: Mapped[str] = mapped_column(Text, nullable=False)
    shell: Mapped[bool] = mapped_column(Boolean, default=True)
    working_dir: Mapped[str | None] = mapped_column(String(512), nullable=True)
    env_vars: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # When to run
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Shanghai")

    # Control
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    timeout: Mapped[int] = mapped_column(Integer, default=3600)
    max_retries: Mapped[int] = mapped_column(Integer, default=0)

    # Multi-agent
    owner_agent: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Metadata
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    # Relationships
    executions: Mapped[list["ExecutionRecord"]] = relationship(
        "ExecutionRecord", back_populates="task", cascade="all, delete-orphan"
    )
