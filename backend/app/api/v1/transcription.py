from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db_session
from backend.app.transcription.models import (
    TranscriptionSubsystemStatus,
    TranscriptionSettings,
    TranscriptionSettingsUpdate,
    ModelCatalogItem,
    LanguageRoutingConfig,
)
from backend.app.transcription.service import TranscriptionService
from backend.app.transcription.registry import registry

router = APIRouter(prefix="/transcription", tags=["Transcription"])

@router.get("/status", response_model=TranscriptionSubsystemStatus)
async def get_transcription_status(
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get live transcription subsystem status, storage footprint, and language routes.
    """
    return await TranscriptionService.get_subsystem_status(db)

@router.get("/settings", response_model=TranscriptionSettings)
async def get_transcription_settings(
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get current transcription settings.
    """
    return await TranscriptionService.get_settings(db)

@router.patch("/settings", response_model=TranscriptionSettings)
async def update_transcription_settings(
    updates: TranscriptionSettingsUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Update transcription settings. Validates that newly assigned default models are READY.
    """
    try:
        return await TranscriptionService.update_settings(db, updates)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/models", response_model=List[ModelCatalogItem])
async def list_models():
    """
    List all catalog models with authoritative live filesystem status.
    """
    return registry.list_catalog()

@router.get("/models/{model_id}", response_model=ModelCatalogItem)
async def get_model_details(model_id: str):
    """
    Get detailed specification and status for a specific model.
    """
    model = registry.get_model(model_id)
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Model '{model_id}' not found.")
    return model

@router.post("/models/{model_id}/verify", response_model=ModelCatalogItem)
async def verify_model(model_id: str):
    """
    Authoritatively verify the filesystem integrity of a model.
    """
    try:
        return registry.verify_model(model_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/languages", response_model=List[LanguageRoutingConfig])
async def list_language_routes(
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get language routing matrix and active model assignments.
    """
    status_obj = await TranscriptionService.get_subsystem_status(db)
    return status_obj.language_routes

# Track active in-memory download states
_active_downloads = {}

@router.post("/models/{model_id}/download")
async def download_model(model_id: str):
    """
    Trigger transactional download of a model into project storage.
    """
    model = registry.get_model(model_id)
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Model '{model_id}' not found.")

    provider = registry.get_provider(model.provider_id)
    if not provider:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Provider '{model.provider_id}' not found.")

    if model_id in _active_downloads and _active_downloads[model_id].get("status") in ["DOWNLOADING", "VERIFYING", "FINALIZING"]:
        return _active_downloads[model_id]

    staging_dir = registry.get_downloads_staging_root() / model_id
    target_dir = registry.get_model_path(model.family, model_id)

    async def run_download_bg():
        _active_downloads[model_id] = {"status": "DOWNLOADING", "message": "Download initiated...", "progress": 0}
        try:
            async def progress_cb(data):
                _active_downloads[model_id] = data

            res = await provider.download_model(
                repo_id=model.source_repository,
                staging_dir=staging_dir,
                target_dir=target_dir,
                progress_callback=progress_cb
            )
            _active_downloads[model_id] = res
        except Exception as e:
            _active_downloads[model_id] = {"status": "ERROR", "message": str(e)}

    import asyncio
    asyncio.create_task(run_download_bg())
    return {"status": "DOWNLOADING", "message": "Download task started in background."}

@router.get("/models/{model_id}/progress")
async def get_model_download_progress(model_id: str):
    """
    Get download or verification progress for a model.
    """
    if model_id in _active_downloads:
        return _active_downloads[model_id]
    model = registry.get_model(model_id)
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Model '{model_id}' not found.")
    return {"status": model.status.value, "message": model.status_detail}

