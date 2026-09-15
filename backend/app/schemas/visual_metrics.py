from datetime import datetime
from typing import Optional, List, Dict, Any
from backend.app.schemas.common import BaseSchema

class FrameResponse(BaseSchema):
    id: str
    visual_metrics_id: str
    video_id: str
    frame_number: int
    timestamp: float
    frame_type: str
    file_path: str
    file_size_bytes: int
    width: int
    height: int
    created_at: datetime
    image_url: str

class VisualSegmentItem(BaseSchema):
    sequence: int
    start_time: float
    end_time: float
    duration: float
    representative_frame_id: Optional[str] = None
    change_score: Optional[float] = None

class VisualActivityWindow(BaseSchema):
    window_index: int
    start_time: float
    end_time: float
    duration: float
    boundary_count: int
    change_density: float
    representative_frame_ids: List[str]

class OCREvidenceItem(BaseSchema):
    id: str
    timestamp: float
    detected_text: str
    confidence: float
    frame_id: Optional[str] = None

class VisualMetricsResponse(BaseSchema):
    id: str
    video_id: str
    algorithm_version: str
    scene_threshold: float
    analyzed_at: datetime

    # Aggregate Statistics
    scene_count: int
    avg_scene_duration: float
    median_scene_duration: float
    shortest_scene_duration: float
    longest_scene_duration: float
    scene_change_frequency: float

    # Structured Data
    scene_timestamps: List[float]
    visual_segments: List[VisualSegmentItem]
    segment_duration_distribution: Dict[str, int]
    visual_activity_timeline: List[VisualActivityWindow]
    technical_properties: Dict[str, Any]
    frames: List[FrameResponse]
    ocr_results: List[OCREvidenceItem]
    ocr_available: bool = False
