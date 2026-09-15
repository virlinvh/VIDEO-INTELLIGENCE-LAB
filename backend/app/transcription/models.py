from enum import Enum
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict

class ModelStatus(str, Enum):
    NOT_INSTALLED = "NOT_INSTALLED"
    DOWNLOADING = "DOWNLOADING"
    VERIFYING = "VERIFYING"
    READY = "READY"
    ERROR = "ERROR"
    INCOMPATIBLE = "INCOMPATIBLE"
    CORRUPTED = "CORRUPTED"
    FILES_MISSING = "FILES_MISSING"

class ModelFamily(str, Enum):
    FASTER_WHISPER = "faster-whisper"
    INDIC_CONFORMER = "indicconformer"
    QWEN_ASR = "qwen-asr"

class SupportedLanguage(str, Enum):
    ENGLISH = "en"
    TAMIL = "ta"
    MALAYALAM = "ml"
    AUTO = "auto"

class ModelCatalogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    model_id: str
    provider_id: str
    family: ModelFamily
    display_name: str
    description: str
    supported_languages: List[str]
    is_multilingual: bool = True
    recommended_use: str
    runtime_requirement: str
    expected_download_size: str = "Unknown"
    expected_installed_size: str = "Unknown"
    license_info: str = "Open Source"
    source_repository: str
    hardware_notes: str
    status: ModelStatus = ModelStatus.NOT_INSTALLED
    status_detail: Optional[str] = None
    local_path: Optional[str] = None
    installed_size_bytes: int = 0
    installed_size_human: str = "0 B"
    last_verified_at: Optional[datetime] = None

class LanguageRoutingConfig(BaseModel):
    language_code: str
    language_name: str
    configured_model_id: Optional[str] = None
    configured_model_name: Optional[str] = None
    status: str = "NO_MODEL_CONFIGURED"

class TranscriptionSettings(BaseModel):
    automatic_asr_fallback_enabled: bool = False
    default_language_mode: str = "auto"
    default_model_english: Optional[str] = None
    default_model_tamil: Optional[str] = None
    default_model_malayalam: Optional[str] = None
    allow_multilingual_fallback: bool = True

class TranscriptionSettingsUpdate(BaseModel):
    automatic_asr_fallback_enabled: Optional[bool] = None
    default_language_mode: Optional[str] = None
    default_model_english: Optional[str] = None
    default_model_tamil: Optional[str] = None
    default_model_malayalam: Optional[str] = None
    allow_multilingual_fallback: Optional[bool] = None

class TranscriptSegmentContract(BaseModel):
    sequence_index: int
    start_time: float
    end_time: float
    duration: float
    text: str
    word_count: int
    confidence: Optional[float] = None

class ProvenanceMetadata(BaseModel):
    source_type: str = "LOCAL_ASR"
    provider_id: Optional[str] = None
    model_id: Optional[str] = None
    model_version: Optional[str] = None
    runtime_version: Optional[str] = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    processing_duration_sec: float = 0.0
    configuration: Dict[str, Any] = Field(default_factory=dict)

class TranscriptionResultContract(BaseModel):
    full_text: str
    language: str
    detected_language: Optional[str] = None
    language_probability: Optional[float] = None
    duration_seconds: float
    segment_count: int
    segments: List[TranscriptSegmentContract]
    provenance: ProvenanceMetadata

class AudioExtractionContract(BaseModel):
    format: str = "wav"
    channels: int = 1
    sample_rate_hz: int = 16000
    codec: str = "pcm_s16le"
    target_path: str

class HardwareInfo(BaseModel):
    cpu_info: str
    cpu_cores: int
    total_ram_gb: float
    available_ram_gb: float
    gpu_name: Optional[str] = None
    gpu_vram_gb: Optional[float] = None
    notes: str

class TranscriptionSubsystemStatus(BaseModel):
    status: str
    automatic_fallback_enabled: bool
    installed_models_count: int
    total_catalog_models_count: int
    languages_configured_count: int
    total_languages_count: int = 3
    model_storage_path: str
    model_storage_size_bytes: int
    model_storage_size_human: str
    hardware: HardwareInfo
    language_routes: List[LanguageRoutingConfig]
