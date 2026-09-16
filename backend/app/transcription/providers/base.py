from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from backend.app.transcription.models import ModelCatalogItem, TranscriptionResultContract

class BaseASRProvider(ABC):
    @property
    @abstractmethod
    def provider_id(self) -> str:
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        pass

    @property
    @abstractmethod
    def supported_languages(self) -> List[str]:
        pass

    @abstractmethod
    def check_runtime(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def check_model(self, model_id: str, model_path: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def transcribe(
        self,
        audio_path: str,
        model_id: str,
        language: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> TranscriptionResultContract:
        pass

    @abstractmethod
    def health_check(self) -> bool:
        pass
