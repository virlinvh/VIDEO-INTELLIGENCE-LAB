from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict

class ComparisonCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    video_ids: List[str] = Field(..., min_length=2, max_length=10)
    notes: Optional[str] = None

class ComparisonUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    notes: Optional[str] = None

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
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    videos: List[ComparisonVideoItem]

class ComparisonAnalyzeRequest(BaseModel):
    video_ids: List[str] = Field(..., min_length=2, max_length=10)

class MetricMatrixCell(BaseModel):
    raw_value: Optional[Union[int, float, str]] = None
    display_value: str
    normalized_per_min: Optional[float] = None
    is_min: bool = False
    is_max: bool = False
    status: str = "AVAILABLE"  # "AVAILABLE", "NOT_ANALYZED", "UNAVAILABLE", "NOT_APPLICABLE"

class MetricMatrixRow(BaseModel):
    key: str
    label: str
    category: str  # "METADATA", "ENGAGEMENT", "SPEECH", "VISUAL", "VOCABULARY"
    unit: str
    values: Dict[str, MetricMatrixCell]  # video_id -> cell

class NormalizedTimelinePoint(BaseModel):
    decile: int  # 0 to 9 representing 0-10%, 10-20%, ..., 90-100%
    decile_label: str  # e.g. "0-10%"
    series: Dict[str, Dict[str, Any]]  # video_id -> { "wpm": float, "words": int, "scene_changes": int, "cuts_per_minute": float, "has_transcript": bool, "has_visuals": bool }

class TimelineEventItem(BaseModel):
    timestamp: float
    normalized_position_pct: float
    formatted_time: str
    duration_seconds: Optional[float] = None

class WordFrequencyItem(BaseModel):
    word: str
    count: int
    occurrences_per_thousand: float = 0.0

class NGramItem(BaseModel):
    ngram: str
    count: int

class VideoVocabularyProfile(BaseModel):
    video_id: str
    title: str
    total_words: int
    unique_words: int
    ttr: float
    top_words: List[WordFrequencyItem]
    signature_words: List[WordFrequencyItem]
    top_bigrams: List[NGramItem]
    top_trigrams: List[NGramItem]
    top_fourgrams: List[NGramItem]
    repeated_phrases: List[NGramItem]

class SharedVocabularyItem(BaseModel):
    word: str
    counts: Dict[str, int]
    total_count: int
    video_count: int
    occurrences_per_thousand_avg: float = 0.0

class SharedPhraseItem(BaseModel):
    phrase: str
    counts: Dict[str, int]
    total_count: int
    video_count: int

class OpeningClosingSnippet(BaseModel):
    video_id: str
    title: str
    duration_seconds: int
    first_sentence: Optional[str] = None
    first_3s_text: Optional[str] = None
    first_5s_text: Optional[str] = None
    first_10s_text: Optional[str] = None
    opening_text: Optional[str] = None
    opening_duration_sec: float = 0.0
    opening_word_count: int = 0
    opening_wpm: float = 0.0
    opening_questions: int = 0
    words_in_first_5s: int = 0
    words_in_first_10s: int = 0
    final_sentence: Optional[str] = None
    last_5s_text: Optional[str] = None
    last_10s_text: Optional[str] = None
    closing_text: Optional[str] = None
    closing_duration_sec: float = 0.0
    closing_word_count: int = 0
    closing_wpm: float = 0.0
    status: str = "AVAILABLE"

class KeyframeItem(BaseModel):
    position_pct: int
    label: str
    frame_id: Optional[str] = None
    timestamp: Optional[float] = None
    file_path: Optional[str] = None
    image_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    status: str = "AVAILABLE"  # "AVAILABLE", "NOT_ANALYZED"

class OCREvidenceItem(BaseModel):
    video_id: str
    video_title: str
    timestamp: float
    formatted_time: str
    detected_text: str
    confidence: float

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
    total_likes: Optional[int] = None
    mean_likes: Optional[float] = None
    total_comments: Optional[int] = None
    mean_comments: Optional[float] = None
    video_ids: List[str]

class VideoComparisonSummary(BaseModel):
    id: str
    title: str
    platform: str
    duration_seconds: int
    creator_name: Optional[str] = None
    thumbnail_url: Optional[str] = None
    published_at: Optional[datetime] = None
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    like_view_ratio: Optional[float] = None
    comment_view_ratio: Optional[float] = None
    has_transcript: bool
    transcript_language: Optional[str] = None
    transcript_source: Optional[str] = None
    requested_language: Optional[str] = None
    asr_model: Optional[str] = None
    is_generated: Optional[bool] = None
    has_script_metrics: bool
    has_visual_metrics: bool

class MultiVideoComparisonResult(BaseModel):
    videos: List[VideoComparisonSummary]
    matrix: List[MetricMatrixRow]
    timeline_deciles: List[NormalizedTimelinePoint]
    timeline_events: Dict[str, List[TimelineEventItem]]
    shared_vocabulary: List[SharedVocabularyItem]
    shared_phrases: List[SharedPhraseItem]
    video_vocabularies: Dict[str, VideoVocabularyProfile]
    openings_closings: List[OpeningClosingSnippet]
    keyframe_gallery: Dict[str, List[KeyframeItem]]
    ocr_evidence: List[OCREvidenceItem]
    creator_aggregates: List[CreatorAggregateMetrics]
    has_mixed_languages: bool
    detected_languages: List[str]
    generated_at: datetime

from typing import Literal

class SegmentRangeRequest(BaseModel):
    type: Literal["ENTIRE", "ABSOLUTE", "RELATIVE", "OPENING", "CLOSING"] = "ENTIRE"
    start_seconds: Optional[float] = None
    end_seconds: Optional[float] = None
    start_percent: Optional[float] = None
    end_percent: Optional[float] = None
    duration_seconds: Optional[float] = None

class SegmentComparisonRequest(BaseModel):
    video_ids: List[str] = Field(..., min_length=2, max_length=10)
    range: SegmentRangeRequest = Field(default_factory=SegmentRangeRequest)

class TranscriptSegmentItem(BaseModel):
    id: str
    sequence_index: int
    start_time: float
    end_time: float
    duration: float
    text: str
    word_count: int
    formatted_start_time: str

class SegmentScriptMetrics(BaseModel):
    word_count: int = 0
    segment_count: int = 0
    sentence_count: int = 0
    unique_words: int = 0
    lexical_diversity: float = 0.0  # TTR %
    average_sentence_length: float = 0.0
    question_count: int = 0
    exclamation_count: int = 0
    filler_count: int = 0
    transition_count: int = 0
    repeated_phrase_count: int = 0
    range_wpm: Optional[float] = None
    effective_duration_seconds: Optional[float] = None

class VideoSegmentComparisonItem(BaseModel):
    video_id: str
    title: str
    creator_name: Optional[str] = None
    platform: str
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[float] = None
    requested_transcript_language: Optional[str] = None
    actual_transcript_language: Optional[str] = None
    transcript_source: Optional[str] = None
    asr_model: Optional[str] = None
    has_transcript: bool
    requested_range_label: str
    effective_start_seconds: Optional[float] = None
    effective_end_seconds: Optional[float] = None
    effective_duration_seconds: Optional[float] = None
    segments: List[TranscriptSegmentItem] = Field(default_factory=list)
    full_text: Optional[str] = None
    word_count: int = 0
    segment_count: int = 0
    metrics: Optional[SegmentScriptMetrics] = None
    availability: str = "AVAILABLE"  # "AVAILABLE", "NOT_AVAILABLE", "NO_TRANSCRIPT", "EMPTY_RANGE"
    warning: Optional[str] = None

class SegmentComparisonResponse(BaseModel):
    range_definition: SegmentRangeRequest
    videos: List[VideoSegmentComparisonItem]
    total_videos: int
    has_mixed_languages: bool = False
    detected_languages: List[str] = Field(default_factory=list)
    compared_at: datetime

