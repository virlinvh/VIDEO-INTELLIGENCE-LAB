from datetime import datetime
from typing import Optional, List, Any, Dict
from sqlalchemy import String, Integer, Float, BigInteger, Boolean, DateTime, Text, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, generate_uuid, utc_now

class Creator(Base):
    __tablename__ = "creators"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    platform: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    platform_creator_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    handle: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    videos: Mapped[List["Video"]] = relationship("Video", back_populates="creator", cascade="all, delete-orphan")


class Video(Base):
    __tablename__ = "videos"
    __table_args__ = (UniqueConstraint("platform", "platform_video_id", name="uq_platform_video_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    platform: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    platform_video_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    original_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    creator_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("creators.id", ondelete="SET NULL"), nullable=True)
    processing_status: Mapped[str] = mapped_column(String(50), default="QUEUED", index=True)
    media_state: Mapped[str] = mapped_column(String(50), default="NOT_DOWNLOADED", index=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    creator: Mapped[Optional["Creator"]] = relationship("Creator", back_populates="videos")
    metadata_rel: Mapped[Optional["VideoMetadata"]] = relationship("VideoMetadata", back_populates="video", uselist=False, cascade="all, delete-orphan")
    transcript: Mapped[Optional["Transcript"]] = relationship("Transcript", back_populates="video", uselist=False, cascade="all, delete-orphan")
    script_metrics: Mapped[Optional["ScriptMetrics"]] = relationship("ScriptMetrics", back_populates="video", uselist=False, cascade="all, delete-orphan")
    visual_metrics: Mapped[Optional["VisualMetrics"]] = relationship("VisualMetrics", back_populates="video", uselist=False, cascade="all, delete-orphan")
    media_files: Mapped[List["MediaFile"]] = relationship("MediaFile", back_populates="video", cascade="all, delete-orphan")
    artifacts: Mapped[List["Artifact"]] = relationship("Artifact", back_populates="video", cascade="all, delete-orphan")
    jobs: Mapped[List["ExtractionJob"]] = relationship("ExtractionJob", back_populates="video", cascade="all, delete-orphan")


class VideoMetadata(Base):
    __tablename__ = "video_metadata"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    video_id: Mapped[str] = mapped_column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    chapters: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, default=list)
    hashtags: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    categories: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    view_count: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    like_count: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    comment_count: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    technical_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict)
    raw_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict)
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    video: Mapped["Video"] = relationship("Video", back_populates="metadata_rel")


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    video_id: Mapped[str] = mapped_column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, unique=True)
    language: Mapped[str] = mapped_column(String(50), default="en")
    requested_language: Mapped[Optional[str]] = mapped_column(String(20), default="en")
    source_type: Mapped[str] = mapped_column(String(50), default="native")
    caption_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    caption_language_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    asr_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    full_text: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    video: Mapped["Video"] = relationship("Video", back_populates="transcript")
    segments: Mapped[List["TranscriptSegment"]] = relationship("TranscriptSegment", back_populates="transcript", cascade="all, delete-orphan")


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    transcript_id: Mapped[str] = mapped_column(String(36), ForeignKey("transcripts.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    duration: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, default=0)

    transcript: Mapped["Transcript"] = relationship("Transcript", back_populates="segments")


class ScriptMetrics(Base):
    __tablename__ = "script_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    video_id: Mapped[str] = mapped_column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, unique=True)
    calculation_version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    
    # Core Word & Lexical Metrics
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    unique_words: Mapped[int] = mapped_column(Integer, default=0)
    lexical_diversity_ttr: Mapped[float] = mapped_column(Float, default=0.0)
    root_ttr: Mapped[float] = mapped_column(Float, default=0.0)

    # Sentence Structure Metrics
    sentence_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_sentence_length: Mapped[float] = mapped_column(Float, default=0.0)
    median_sentence_length: Mapped[float] = mapped_column(Float, default=0.0)
    min_sentence_length: Mapped[int] = mapped_column(Integer, default=0)
    max_sentence_length: Mapped[int] = mapped_column(Integer, default=0)
    sentence_length_distribution: Mapped[Dict[str, int]] = mapped_column(JSON, default=dict)

    # Speaking Rate & Timeline Metrics
    total_spoken_duration: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_wpm: Mapped[float] = mapped_column(Float, default=0.0)
    pace_timeline: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)

    # Punctuation & Speech Pattern Detections
    question_count: Mapped[int] = mapped_column(Integer, default=0)
    exclamation_count: Mapped[int] = mapped_column(Integer, default=0)
    question_evidence: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    exclamation_evidence: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)

    # Frequency & N-Gram Intelligence
    word_frequencies: Mapped[Dict[str, int]] = mapped_column(JSON, default=dict)
    word_frequencies_filtered: Mapped[Dict[str, int]] = mapped_column(JSON, default=dict)
    phrase_frequencies: Mapped[Dict[str, Dict[str, int]]] = mapped_column(JSON, default=dict)
    repeated_phrases: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)

    # Dictionary Rule Matching
    filler_word_counts: Mapped[Dict[str, int]] = mapped_column(JSON, default=dict)
    transition_phrase_counts: Mapped[Dict[str, int]] = mapped_column(JSON, default=dict)
    filler_evidence: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    transition_evidence: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)

    # Temporal Extracts
    opening_extracts: Mapped[Dict[str, str]] = mapped_column(JSON, default=dict)
    closing_extracts: Mapped[Dict[str, str]] = mapped_column(JSON, default=dict)

    video: Mapped["Video"] = relationship("Video", back_populates="script_metrics")


class VisualMetrics(Base):
    __tablename__ = "visual_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    video_id: Mapped[str] = mapped_column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, unique=True)
    algorithm_version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    scene_threshold: Mapped[float] = mapped_column(Float, default=0.3)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    # Core Segment Metrics
    scene_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_scene_duration: Mapped[float] = mapped_column(Float, default=0.0)
    median_scene_duration: Mapped[float] = mapped_column(Float, default=0.0)
    shortest_scene_duration: Mapped[float] = mapped_column(Float, default=0.0)
    longest_scene_duration: Mapped[float] = mapped_column(Float, default=0.0)
    scene_change_frequency: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Structured Data
    scene_timestamps: Mapped[List[float]] = mapped_column(JSON, default=list)
    visual_segments: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    segment_duration_distribution: Mapped[Dict[str, int]] = mapped_column(JSON, default=dict)
    visual_activity_timeline: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    technical_properties: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    video: Mapped["Video"] = relationship("Video", back_populates="visual_metrics")
    frames: Mapped[List["Frame"]] = relationship("Frame", back_populates="visual_metrics", cascade="all, delete-orphan")
    ocr_results: Mapped[List["OCRResult"]] = relationship("OCRResult", back_populates="visual_metrics", cascade="all, delete-orphan")


class Frame(Base):
    __tablename__ = "frames"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    visual_metrics_id: Mapped[str] = mapped_column(String(36), ForeignKey("visual_metrics.id", ondelete="CASCADE"), nullable=False, index=True)
    video_id: Mapped[str] = mapped_column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    frame_number: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[float] = mapped_column(Float, nullable=False)
    frame_type: Mapped[str] = mapped_column(String(50), default="representative")
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    visual_metrics: Mapped["VisualMetrics"] = relationship("VisualMetrics", back_populates="frames")


class OCRResult(Base):
    __tablename__ = "ocr_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    visual_metrics_id: Mapped[str] = mapped_column(String(36), ForeignKey("visual_metrics.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp: Mapped[float] = mapped_column(Float, nullable=False)
    detected_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    bounding_box: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    visual_metrics: Mapped["VisualMetrics"] = relationship("VisualMetrics", back_populates="ocr_results")


class MediaFile(Base):
    __tablename__ = "media_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    video_id: Mapped[str] = mapped_column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    media_state: Mapped[str] = mapped_column(String(50), default="NOT_DOWNLOADED", index=True)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    format: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    resolution: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    video_codec: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    audio_codec: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    downloaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    video: Mapped["Video"] = relationship("Video", back_populates="media_files")


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    video_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=True, index=True)
    job_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    artifact_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    relative_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    is_regeneratable: Mapped[bool] = mapped_column(Boolean, default=True)
    retention_state: Mapped[str] = mapped_column(String(50), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    video: Mapped[Optional["Video"]] = relationship("Video", back_populates="artifacts")


class ExtractionJob(Base):
    __tablename__ = "extraction_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    video_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("videos.id", ondelete="SET NULL"), nullable=True, index=True)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    processing_mode: Mapped[str] = mapped_column(String(50), default="ANALYZE_ONLY")
    requested_transcript_language: Mapped[str] = mapped_column(String(20), default="en")
    state: Mapped[str] = mapped_column(String(50), default="QUEUED", index=True)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    current_step: Mapped[str] = mapped_column(String(255), default="Enqueued")
    warnings: Mapped[List[str]] = mapped_column(JSON, default=list)
    error_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    video: Mapped[Optional["Video"]] = relationship("Video", back_populates="jobs")


class Comparison(Base):
    __tablename__ = "comparisons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    items: Mapped[List["ComparisonVideo"]] = relationship("ComparisonVideo", back_populates="comparison", cascade="all, delete-orphan")


class ComparisonVideo(Base):
    __tablename__ = "comparison_videos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    comparison_id: Mapped[str] = mapped_column(String(36), ForeignKey("comparisons.id", ondelete="CASCADE"), nullable=False, index=True)
    video_id: Mapped[str] = mapped_column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)

    comparison: Mapped["Comparison"] = relationship("Comparison", back_populates="items")


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
