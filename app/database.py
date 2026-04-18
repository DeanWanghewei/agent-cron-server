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
    """Run Alembic upgrade in a sync context (called from thread pool).

    Handles the migration from pre-alembic databases: if tables already exist
    but no alembic_version record is found, stamps the current head before
    running upgrade to avoid 'table already exists' errors.
    """
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, inspect

    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", "alembic")
    alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

    # Detect pre-alembic database: tables exist but no alembic_version table
    sync_url = settings.DATABASE_URL.replace("+aiosqlite", "").replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_url)
    try:
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        has_alembic_version = "alembic_version" in existing_tables
        has_data_tables = bool(existing_tables - {"alembic_version"})

        if has_data_tables and not has_alembic_version:
            logger.info(
                "Detected pre-alembic database (%d tables, no alembic_version). "
                "Stamping current head before migration.",
                len(existing_tables),
            )
            command.stamp(alembic_cfg, "head")
    finally:
        engine.dispose()

    command.upgrade(alembic_cfg, "head")


async def init_db() -> None:
    """Run Alembic migrations on startup to bring DB to the latest schema."""
    import asyncio

    logger.info("Running database migrations...")
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _run_alembic_upgrade)
    logger.info("Database migrations complete.")
