import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from backend.app.config import settings
from backend.app.transcription.models import ModelCatalogItem, ModelFamily, ModelStatus
from backend.app.transcription.providers import (
    BaseASRProvider, FasterWhisperProvider, IndicConformerProvider, QwenASRProvider
)

def format_bytes(size: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"

def is_path_contained(target_path: Path, root_path: Path) -> bool:
    try:
        target = target_path.resolve()
        root = root_path.resolve()
        return root == target or root in target.parents
    except Exception:
        return False

# Primary Production Model Catalog (Strictly English + Indic production engines)
CATALOG_DEFINITIONS: List[Dict] = [
    {
        "model_id": "whisper-large-v3-turbo",
        "provider_id": "faster-whisper",
        "family": ModelFamily.FASTER_WHISPER,
        "display_name": "Whisper Large V3 Turbo",
        "description": "Production engine for high-accuracy English transcription with ultra-fast GPU inference.",
        "supported_languages": ["en"],
        "is_multilingual": True,
        "recommended_use": "Production default for English video transcription.",
        "runtime_requirement": "Faster-Whisper Isolated Runtime (CTranslate2)",
        "expected_download_size": "~1.6 GB",
        "expected_installed_size": "~1.8 GB",
        "license_info": "MIT (OpenAI / Systran)",
        "source_repository": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
        "hardware_notes": "Runs with GPU acceleration (float16) on RTX 3060 6GB with automatic CPU int8 fallback.",
    },
    {
        "model_id": "indic-conformer-600m-multilingual",
        "provider_id": "indicconformer",
        "family": ModelFamily.INDIC_CONFORMER,
        "display_name": "AI4Bharat IndicConformer 600M",
        "description": "State-of-the-art hybrid CTC/RNNT model specialized for Tamil and Malayalam transcription with robust code-switching support.",
        "supported_languages": ["ta", "ml"],
        "is_multilingual": True,
        "recommended_use": "Production engine for Tamil and Malayalam transcription.",
        "runtime_requirement": "IndicConformer Dedicated Runtime (PyTorch / ONNX)",
        "expected_download_size": "~2.4 GB",
        "expected_installed_size": "~2.6 GB",
        "license_info": "MIT (AI4Bharat / IIT Madras)",
        "source_repository": "ai4bharat/indic-conformer-600m-multilingual",
        "hardware_notes": "Runs with CUDA / ONNX acceleration on RTX 3060 6GB with CPU fallback.",
    }
]


class ModelRegistry:
    def __init__(self):
        self.providers: Dict[str, BaseASRProvider] = {
            "faster-whisper": FasterWhisperProvider(),
            "indicconformer": IndicConformerProvider(),
            "qwen-asr": QwenASRProvider(),
        }

    def register_provider(self, provider: BaseASRProvider) -> None:
        self.providers[provider.provider_id] = provider

    def get_provider(self, provider_id: str) -> Optional[BaseASRProvider]:
        return self.providers.get(provider_id)

    def get_models_root(self) -> Path:
        return settings.models_path

    def get_downloads_staging_root(self) -> Path:
        return settings.models_path / ".downloads"

    def get_model_path(self, family: ModelFamily, model_id: str) -> Path:
        target = settings.models_path / family.value / model_id
        if not is_path_contained(target, settings.models_path):
            raise ValueError(f"Path traversal detected for model {model_id}")
        return target

    def inspect_model_filesystem(self, family: ModelFamily, model_id: str, provider_id: str) -> Tuple[ModelStatus, str, int, Optional[str]]:
        path = self.get_model_path(family, model_id)
        if not path.exists():
            return ModelStatus.NOT_INSTALLED, "Not installed locally.", 0, str(path)

        # Calculate actual directory size
        total_size = 0
        file_count = 0
        for root, _, files in os.walk(path):
            for f in files:
                if f == ".gitkeep":
                    continue
                fp = os.path.join(root, f)
                if os.path.isfile(fp):
                    total_size += os.path.getsize(fp)
                    file_count += 1

        provider = self.providers.get(provider_id)
        if provider:
            chk = provider.check_model(model_id, str(path))
            if chk.get("ready"):
                return ModelStatus.READY, f"Verified intact ({file_count} files).", total_size, str(path)
            elif chk.get("status") == "FILES_MISSING":
                return ModelStatus.FILES_MISSING, chk.get("detail", "Files missing."), total_size, str(path)
            else:
                return ModelStatus.NOT_INSTALLED, chk.get("detail", "Not installed."), total_size, str(path)

        if total_size == 0 or file_count == 0:
            return ModelStatus.NOT_INSTALLED, "Empty directory.", 0, str(path)
        return ModelStatus.READY, "Model files found.", total_size, str(path)

    def list_catalog(self) -> List[ModelCatalogItem]:
        items: List[ModelCatalogItem] = []
        for defn in CATALOG_DEFINITIONS:
            status, detail, size_b, local_p = self.inspect_model_filesystem(
                defn["family"], defn["model_id"], defn["provider_id"]
            )
            item = ModelCatalogItem(
                model_id=defn["model_id"],
                provider_id=defn["provider_id"],
                family=defn["family"],
                display_name=defn["display_name"],
                description=defn["description"],
                supported_languages=defn["supported_languages"],
                is_multilingual=defn["is_multilingual"],
                recommended_use=defn["recommended_use"],
                runtime_requirement=defn["runtime_requirement"],
                expected_download_size=defn["expected_download_size"],
                expected_installed_size=defn["expected_installed_size"],
                license_info=defn["license_info"],
                source_repository=defn["source_repository"],
                hardware_notes=defn["hardware_notes"],
                status=status,
                status_detail=detail,
                local_path=local_p,
                installed_size_bytes=size_b,
                installed_size_human=format_bytes(size_b),
                last_verified_at=datetime.utcnow() if status == ModelStatus.READY else None
            )
            items.append(item)
        return items

    def get_model(self, model_id: str) -> Optional[ModelCatalogItem]:
        catalog = self.list_catalog()
        for item in catalog:
            if item.model_id == model_id:
                return item
        return None

    def verify_model(self, model_id: str) -> ModelCatalogItem:
        model = self.get_model(model_id)
        if not model:
            raise ValueError(f"Model ID '{model_id}' is not in the registered catalog.")
        return model

registry = ModelRegistry()
