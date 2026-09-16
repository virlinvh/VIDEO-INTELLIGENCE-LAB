import json
import os
from typing import Dict, Any, List, Optional
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.config import settings
from backend.app.db.models.entities import AppSetting
from backend.app.transcription.models import (
    TranscriptionSettings,
    TranscriptionSettingsUpdate,
    TranscriptionSubsystemStatus,
    LanguageRoutingConfig,
    HardwareInfo,
    ModelStatus,
    AudioExtractionContract
)
from backend.app.transcription.registry import registry, format_bytes

SETTINGS_KEY = "transcription_settings"

class TranscriptionService:
    @staticmethod
    async def get_settings(db: AsyncSession) -> TranscriptionSettings:
        stmt = select(AppSetting).where(AppSetting.key == SETTINGS_KEY)
        res = await db.execute(stmt)
        record = res.scalar_one_or_none()
        if not record:
            # Default settings
            return TranscriptionSettings()
        try:
            data = json.loads(record.value)
            return TranscriptionSettings(**data)
        except Exception:
            return TranscriptionSettings()

    @staticmethod
    async def update_settings(db: AsyncSession, updates: TranscriptionSettingsUpdate) -> TranscriptionSettings:
        curr = await TranscriptionService.get_settings(db)
        data = curr.model_dump()

        # Validate that any newly assigned model is actually READY
        catalog = registry.list_catalog()
        model_status_map = {m.model_id: m.status for m in catalog}

        for k, v in updates.model_dump(exclude_unset=True).items():
            if k in ["default_model_english", "default_model_tamil", "default_model_malayalam"] and v is not None:
                if v not in model_status_map:
                    raise ValueError(f"Model ID '{v}' does not exist in catalog.")
                if model_status_map[v] != ModelStatus.READY:
                    raise ValueError(f"Cannot assign model '{v}' as active default: status is {model_status_map[v].value}.")
            data[k] = v

        new_settings = TranscriptionSettings(**data)

        stmt = select(AppSetting).where(AppSetting.key == SETTINGS_KEY)
        res = await db.execute(stmt)
        record = res.scalar_one_or_none()
        if not record:
            record = AppSetting(key=SETTINGS_KEY, value=json.dumps(new_settings.model_dump()))
            db.add(record)
        else:
            record.value = json.dumps(new_settings.model_dump())
        
        await db.commit()
        return new_settings

    @staticmethod
    def get_hardware_info() -> HardwareInfo:
        cores = os.cpu_count() or 4
        total_ram = 16.0
        avail_ram = 8.0

        # Attempt to read memory using Windows ctypes if available
        try:
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                total_ram = round(stat.ullTotalPhys / (1024**3), 1)
                avail_ram = round(stat.ullAvailPhys / (1024**3), 1)
        except Exception:
            pass

        return HardwareInfo(
            cpu_info=f"{cores}-core CPU",
            cpu_cores=cores,
            total_ram_gb=total_ram,
            available_ram_gb=avail_ram,
            gpu_name="Standard / DirectML Compatible",
            gpu_vram_gb=None,
            notes="Hardware specs detected via standard system APIs."
        )

    @staticmethod
    async def get_subsystem_status(db: AsyncSession) -> TranscriptionSubsystemStatus:
        app_settings = await TranscriptionService.get_settings(db)
        catalog = registry.list_catalog()
        installed_models = [m for m in catalog if m.status == ModelStatus.READY]

        # Calculate model storage size
        models_root = registry.get_models_root()
        total_models_size = 0
        if models_root.exists():
            for root, _, files in os.walk(models_root):
                for f in files:
                    if f != ".gitkeep":
                        total_models_size += os.path.getsize(os.path.join(root, f))

        # Language routes
        model_name_map = {m.model_id: m.display_name for m in catalog}
        model_status_map = {m.model_id: m.status for m in catalog}

        languages = [
            ("en", "English", app_settings.default_model_english),
            ("ta", "Tamil", app_settings.default_model_tamil),
            ("ml", "Malayalam", app_settings.default_model_malayalam),
        ]

        routes: List[LanguageRoutingConfig] = []
        configured_count = 0
        for code, name, mid in languages:
            if mid and mid in model_status_map and model_status_map[mid] == ModelStatus.READY:
                routes.append(LanguageRoutingConfig(
                    language_code=code,
                    language_name=name,
                    configured_model_id=mid,
                    configured_model_name=model_name_map.get(mid),
                    status="READY"
                ))
                configured_count += 1
            elif mid:
                routes.append(LanguageRoutingConfig(
                    language_code=code,
                    language_name=name,
                    configured_model_id=mid,
                    configured_model_name=model_name_map.get(mid),
                    status="MODEL_NOT_READY"
                ))
            else:
                routes.append(LanguageRoutingConfig(
                    language_code=code,
                    language_name=name,
                    configured_model_id=None,
                    configured_model_name=None,
                    status="NO_MODEL_CONFIGURED"
                ))

        overall_status = "READY" if len(installed_models) > 0 and app_settings.automatic_asr_fallback_enabled else "NOT_CONFIGURED"

        return TranscriptionSubsystemStatus(
            status=overall_status,
            automatic_fallback_enabled=app_settings.automatic_asr_fallback_enabled,
            installed_models_count=len(installed_models),
            total_catalog_models_count=len(catalog),
            languages_configured_count=configured_count,
            total_languages_count=3,
            model_storage_path=str(models_root.resolve()),
            model_storage_size_bytes=total_models_size,
            model_storage_size_human=format_bytes(total_models_size),
            hardware=TranscriptionService.get_hardware_info(),
            language_routes=routes
        )

    @staticmethod
    def get_audio_extraction_contract(job_id: str) -> AudioExtractionContract:
        target_dir = settings.temp_path / f"job_{job_id}" / "asr"
        target_dir.mkdir(parents=True, exist_ok=True)
        return AudioExtractionContract(
            format="wav",
            channels=1,
            sample_rate_hz=16000,
            codec="pcm_s16le",
            target_path=str((target_dir / "audio_16k_mono.wav").resolve())
        )
