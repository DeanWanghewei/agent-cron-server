import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router, root_router
from app.config import settings
from app.database import init_db
from app.mcp_server.tools import mcp
from app.scheduler.scheduler import init_scheduler, shutdown_scheduler
from app.scheduler.runner import cleanup_expired_logs

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)


# MCP app needs its lifespan managed — create it before FastAPI so we can merge lifespans
mcp_app = mcp.http_app(path="/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s...", settings.APP_NAME)
    await init_db()
    removed = cleanup_expired_logs()
    if removed:
        logger.info("Cleaned up %d expired log directories", removed)
    await init_scheduler()
    logger.info("%s started on %s:%d", settings.APP_NAME, settings.HOST, settings.PORT)
    # Enter MCP StreamableHTTP session manager lifespan
    async with mcp_app.lifespan(mcp_app):
        yield
    logger.info("Shutting down %s...", settings.APP_NAME)
    await shutdown_scheduler()


app = FastAPI(
    title="Agent Cron Server",
    description="Scheduled task execution service for AI agents",
    version="0.1.0",
    lifespan=lifespan,
)

# REST API routes
app.include_router(api_router)
app.include_router(root_router)


# Root redirect to dashboard
@app.get("/")
async def root():
    return RedirectResponse(url="/dashboard/")


# MCP endpoint (streamable-http as primary, SSE as fallback)
app.mount(settings.MCP_MOUNT_PATH, mcp_app)

# Static dashboard UI — must be last mount (catches remaining paths)
static_dir = Path(__file__).parent / "static"
app.mount("/dashboard", StaticFiles(directory=str(static_dir), html=True), name="dashboard")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
