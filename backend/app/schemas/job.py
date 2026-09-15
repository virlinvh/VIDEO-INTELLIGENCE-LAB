from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from backend.app.schemas.common import BaseSchema

class JobValidationItem(BaseModel):
    raw_url: str
    platform: str
    video_id: str
    canonical_url: str
    is_valid: bool
    error: Optional[str] = None
    is_duplicate_in_batch: bool = False
    already_in_library: bool = False

class JobBatchValidateRequest(BaseModel):
    raw_text: str

class JobBatchValidateResponse(BaseModel):
    total_urls: int
    valid_urls: int
    invalid_urls: int
    duplicates_in_batch: int
    items: List[JobValidationItem]

class JobSubmitItem(BaseModel):
    url: str
    processing_mode: Optional[str] = None  # None = use batch default

class JobSubmitRequest(BaseModel):
    urls: List[str]
    default_mode: str = "ANALYZE_ONLY"
    default_language: str = "en"
    overrides: Dict[str, str] = Field(default_factory=dict)
    language_overrides: Dict[str, str] = Field(default_factory=dict)
    reprocess_existing: bool = False

class JobStatusResponse(BaseSchema):
    id: str
    video_id: Optional[str] = None
    url: str
    processing_mode: str
    requested_transcript_language: str = "en"
    state: str
    progress_percent: int
    current_step: str
    warnings: List[str]
    error_details: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
