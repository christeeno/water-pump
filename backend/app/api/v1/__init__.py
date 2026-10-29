from fastapi import APIRouter
from .health import router as health_router
from .telemetry import router as telemetry_router
from .devices import router as devices_router
from .alerts import router as alerts_router
from .settings import router as settings_router
from .commands import router as commands_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(telemetry_router)
api_router.include_router(devices_router)
api_router.include_router(alerts_router)
api_router.include_router(settings_router)
api_router.include_router(commands_router)

__all__ = ["api_router"]
