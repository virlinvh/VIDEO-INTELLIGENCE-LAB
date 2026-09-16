from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from backend.app.schemas.common import BaseSchema

class CreatorSummary(BaseSchema):
    id: str
    platform: str
    platform_creator_id: Optional[str] = None
    name: str
    handle: Optional[str] = None
    url: Optional[str] = None

class VideoSummary(BaseSchema):
    id: str
    platform: str
    platform_video_id: str
    original_url: str
    title: str
    duration_seconds: int
    creator: Optional[CreatorSummary] = None
    processing_status: str
    media_state: str
    published_at: Optional[datetime] = None
    created_at: datetime
    thumbnail_url: Optional[str] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    has_transcript: bool = False

class TranscriptSegmentSchema(BaseSchema):
    sequence_index: int
    start_time: float
    end_time: float
    duration: float
    text: str
    word_count: int

class TranscriptResponse(BaseSchema):
    id: str
    video_id: str
    language: str
    requested_language: Optional[str] = "en"
    source_type: str
    caption_source: Optional[str] = None
    caption_language_code: Optional[str] = None
    asr_model: Optional[str] = None
    is_generated: bool
    full_text: str
    segment_count: int
    segments: List[TranscriptSegmentSchema]

class VideoDetailResponse(BaseSchema):
    id: str
    platform: str
    platform_video_id: str
    original_url: str
    title: str
    duration_seconds: int
    creator: Optional[CreatorSummary] = None
    processing_status: str
    media_state: str
    published_at: Optional[datetime] = None
    created_at: datetime
    
    # Metadata
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    chapters: Optional[List[Dict[str, Any]]] = None
    hashtags: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    technical_details: Optional[Dict[str, Any]] = None
    has_transcript: bool = False
    has_raw_data: bool = False
