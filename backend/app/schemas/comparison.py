from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict

class ComparisonCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    video_ids: List[str] = Field(..., min_length=2, max_length=10)

class ComparisonVideoItem(BaseModel):
    video_id: str
    title: str
    platform: str
    duration_seconds: int
    creator_name: Optional[str] = None
    thumbnail_url: Optional[str] = None

class ComparisonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    created_at: datetime
    videos: List[ComparisonVideoItem]

class ComparisonAnalyzeRequest(BaseModel):
    video_ids: List[str] = Field(..., min_length=2, max_length=10)

class MetricMatrixCell(BaseModel):
    raw_value: Optional[Union[int, float, str]] = None
    display_value: str
    normalized_per_min: Optional[float] = None
    is_min: bool = False
    is_max: bool = False
    status: str = "AVAILABLE"  # "AVAILABLE", "NOT_ANALYZED", "UNAVAILABLE"

class MetricMatrixRow(BaseModel):
    key: str
    label: str
    category: str  # "METADATA", "SPEECH", "VISUAL", "VOCABULARY"
    unit: str
    values: Dict[str, MetricMatrixCell]  # video_id -> cell

class NormalizedTimelinePoint(BaseModel):
    decile: int  # 0 to 9 representing 0-10%, 10-20%, ..., 90-100%
    decile_label: str  # e.g. "0-10%"
    series: Dict[str, Dict[str, Any]]  # video_id -> { "wpm": float, "words": int, "scene_changes": int, "has_transcript": bool, "has_visuals": bool }

class WordFrequencyItem(BaseModel):
    word: str
    count: int

class NGramItem(BaseModel):
    ngram: str
    count: int

class VideoVocabularyProfile(BaseModel):
    video_id: str
    title: str
    total_words: int
    unique_words: int
    ttr: float
    signature_words: List[WordFrequencyItem]
    top_bigrams: List[NGramItem]
    top_trigrams: List[NGramItem]

class SharedVocabularyItem(BaseModel):
    word: str
    counts: Dict[str, int]
    total_count: int
    video_count: int

class OpeningClosingSnippet(BaseModel):
    video_id: str
    title: str
    duration_seconds: int
    opening_text: Optional[str] = None
    opening_duration_sec: float = 0.0
    opening_word_count: int = 0
    opening_wpm: float = 0.0
    closing_text: Optional[str] = None
    closing_duration_sec: float = 0.0
    closing_word_count: int = 0
    closing_wpm: float = 0.0
    status: str = "AVAILABLE"

class CreatorAggregateMetrics(BaseModel):
    creator_id: Optional[str] = None
    creator_name: str
    platform: str
    sample_size_n: int
    mean_duration_seconds: float
    median_duration_seconds: float
    mean_wpm: Optional[float] = None
    mean_vocabulary_richness: Optional[float] = None
    mean_cut_rate_per_min: Optional[float] = None
    total_views: Optional[int] = None
    mean_views: Optional[float] = None
    video_ids: List[str]

class VideoComparisonSummary(BaseModel):
    id: str
    title: str
    platform: str
    duration_seconds: int
    creator_name: Optional[str] = None
    thumbnail_url: Optional[str] = None
    published_at: Optional[datetime] = None
    has_transcript: bool
    has_script_metrics: bool
    has_visual_metrics: bool

class MultiVideoComparisonResult(BaseModel):
    videos: List[VideoComparisonSummary]
    matrix: List[MetricMatrixRow]
    timeline_deciles: List[NormalizedTimelinePoint]
    shared_vocabulary: List[SharedVocabularyItem]
    video_vocabularies: Dict[str, VideoVocabularyProfile]
    openings_closings: List[OpeningClosingSnippet]
    creator_aggregates: List[CreatorAggregateMetrics]
    generated_at: datetime
