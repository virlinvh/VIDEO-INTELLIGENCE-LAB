from typing import List, Dict, Any, Optional
from pathlib import Path
from backend.app.transcription.providers.base import BaseASRProvider
from backend.app.transcription.models import TranscriptionResultContract

class QwenASRProvider(BaseASRProvider):
    @property
    def provider_id(self) -> str:
        return "qwen-asr"

    @property
    def display_name(self) -> str:
        return "Tamil Qwen ASR Specialist"

    @property
    def supported_languages(self) -> List[str]:
        return ["ta"]

    def check_runtime(self) -> Dict[str, Any]:
        return {
            "installed": False,
            "runtime_path": "runtimes/qwen-asr",
            "message": "Qwen ASR runtime not installed"
        }

    def check_model(self, model_id: str, model_path: str) -> Dict[str, Any]:
        p = Path(model_path)
        if not p.exists():
            return {"ready": False, "status": "NOT_INSTALLED", "detail": "Directory does not exist"}
        req_files = ["pytorch_model.bin", "config.json"]
        existing = [f for f in req_files if (p / f).exists()]
        if len(existing) == 0:
            return {"ready": False, "status": "NOT_INSTALLED", "detail": "Model weights not found"}
        if len(existing) < len(req_files):
            return {"ready": False, "status": "FILES_MISSING", "detail": "Incomplete model files"}
        return {"ready": True, "status": "READY", "detail": "Model files intact"}

    async def transcribe(
        self,
        audio_path: str,
        model_id: str,
        language: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> TranscriptionResultContract:
        raise NotImplementedError("Tamil Qwen ASR is not activated in Phase 4.5A (Architecture only).")

    def health_check(self) -> bool:
        return True
