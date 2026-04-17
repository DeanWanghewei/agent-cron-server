from fastapi import APIRouter

from app.api.executions import router as executions_router
from app.api.health import router as health_router
from app.api.tasks import router as tasks_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(tasks_router)
api_router.include_router(executions_router)

# Health check at root level (not under /api/v1)
root_router = APIRouter()
root_router.include_router(health_router)
