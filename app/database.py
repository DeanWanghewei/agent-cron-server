import logging
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session


def _run_alembic_upgrade() -> None:
    """Run Alembic upgrade in a sync context (called from thread pool)."""
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", "alembic")
    alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    command.upgrade(alembic_cfg, "head")


async def init_db() -> None:
    """Run Alembic migrations on startup to bring DB to the latest schema."""
    import asyncio

    logger.info("Running database migrations...")
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _run_alembic_upgrade)
    logger.info("Database migrations complete.")
