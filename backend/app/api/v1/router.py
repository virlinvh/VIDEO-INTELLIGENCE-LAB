from fastapi import APIRouter
from backend.app.config import settings
from backend.app.schemas.common import HealthCheckResponse
from backend.app.schemas.storage import StorageOverviewResponse
from backend.app.services.storage_service import StorageService
from backend.app.db.session import engine
from backend.app.api.v1.jobs import router as jobs_router
from backend.app.api.v1.videos import router as videos_router
from backend.app.api.v1.comparisons import router as comparisons_router
from backend.app.api.v1.transcription import router as transcription_router
from sqlalchemy import text

api_router = APIRouter(prefix="/api/v1")

@api_router.get("/health", response_model=HealthCheckResponse, tags=["Health"])
async def health_check():
    db_ok = True
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    storage_ok = settings.storage_root.exists() and settings.data_root.exists()

    return HealthCheckResponse(
        status="ok" if db_ok and storage_ok else "degraded",
        app_name=settings.app_name,
        version=settings.version,
        environment=settings.environment,
        database_connected=db_ok,
        storage_directories_ready=storage_ok
    )

@api_router.get("/storage", response_model=StorageOverviewResponse, tags=["Storage"])
async def get_storage_overview():
    return StorageService.get_overview()

@api_router.get("/settings", tags=["Settings"])
async def get_settings_overview():
    return {
        "app_name": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
        "default_mode": settings.default_mode,
        "saved_videos_path": str(settings.saved_videos_path.resolve()),
        "max_concurrent_jobs": settings.max_concurrent_jobs,
        "wpm_window_seconds": settings.wpm_window_seconds,
        "scene_threshold": settings.scene_threshold
    }

api_router.include_router(jobs_router)
api_router.include_router(videos_router)
api_router.include_router(comparisons_router, prefix="/comparisons", tags=["Comparisons"])
api_router.include_router(transcription_router)
