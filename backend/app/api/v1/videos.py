import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_
from sqlalchemy.orm import selectinload
from backend.app.config import settings
from backend.app.db.session import get_db_session
from backend.app.db.models.entities import (
    Video, VideoMetadata, Transcript, TranscriptSegment, Creator, ScriptMetrics, VisualMetrics, Frame, OCRResult, Artifact, ExtractionJob
)
from backend.app.schemas.video import VideoSummary, VideoDetailResponse, TranscriptResponse, CreatorSummary
from backend.app.schemas.script_metrics import ScriptMetricsResponse
from backend.app.schemas.visual_metrics import VisualMetricsResponse, FrameResponse, OCREvidenceItem
from backend.app.services.script_analysis_service import ScriptAnalysisService
from backend.app.services.visual_analysis_service import VisualAnalysisService
from backend.app.transcription.registry import registry
from backend.app.transcription.models import ModelStatus
from backend.app.services.job_worker import global_worker_pool

router = APIRouter(prefix="/videos", tags=["Videos"])

@router.get("", response_model=List[VideoSummary])
async def list_videos(
    search: Optional[str] = None,
    platform: Optional[str] = None,
    processing_status: Optional[str] = None,
    has_transcript: Optional[bool] = None,
    creator_id: Optional[str] = None,
    sort_by: str = Query("created_at", enum=["created_at", "duration_seconds", "title", "published_at"]),
    sort_order: str = Query("desc", enum=["asc", "desc"]),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(Video).options(
        selectinload(Video.creator),
        selectinload(Video.metadata_rel),
        selectinload(Video.transcript)
    )

    if search:
        stmt = stmt.where(or_(
            Video.title.ilike(f"%{search}%"),
            Video.platform_video_id.ilike(f"%{search}%")
        ))
    if platform:
        stmt = stmt.where(Video.platform == platform)
    if processing_status:
        stmt = stmt.where(Video.processing_status == processing_status)
    if creator_id:
        stmt = stmt.where(Video.creator_id == creator_id)

    order_col = getattr(Video, sort_by, Video.created_at)
    stmt = stmt.order_by(desc(order_col) if sort_order == "desc" else order_col).limit(limit)

    res = await db.execute(stmt)
    videos = res.scalars().all()

    summaries: List[VideoSummary] = []
    for v in videos:
        c_summary = CreatorSummary.model_validate(v.creator) if v.creator else None
        thumb = v.metadata_rel.thumbnail_url if v.metadata_rel else None
        views = v.metadata_rel.view_count if v.metadata_rel else None
        likes = v.metadata_rel.like_count if v.metadata_rel else None
        has_t = v.transcript is not None

        if has_transcript is not None and has_t != has_transcript:
            continue

        summaries.append(VideoSummary(
            id=v.id,
            platform=v.platform,
            platform_video_id=v.platform_video_id,
            original_url=v.original_url,
            title=v.title,
            duration_seconds=v.duration_seconds,
            creator=c_summary,
            processing_status=v.processing_status,
            media_state=v.media_state,
            published_at=v.published_at,
            created_at=v.created_at,
            thumbnail_url=thumb,
            view_count=views,
            like_count=likes,
            has_transcript=has_t
        ))

    return summaries

@router.get("/{video_id}", response_model=VideoDetailResponse)
async def get_video(video_id: str, db: AsyncSession = Depends(get_db_session)):
    stmt = select(Video).options(
        selectinload(Video.creator),
        selectinload(Video.metadata_rel),
        selectinload(Video.transcript)
    ).where(Video.id == video_id)
    res = await db.execute(stmt)
    v = res.scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=404, detail="Video record not found")

    c_summary = CreatorSummary.model_validate(v.creator) if v.creator else None
    vm = v.metadata_rel
    raw_exists = (settings.metadata_path / f"{v.id}.json").exists()

    return VideoDetailResponse(
        id=v.id,
        platform=v.platform,
        platform_video_id=v.platform_video_id,
        original_url=v.original_url,
        title=v.title,
        duration_seconds=v.duration_seconds,
        creator=c_summary,
        processing_status=v.processing_status,
        media_state=v.media_state,
        published_at=v.published_at,
        created_at=v.created_at,
        description=vm.description if vm else None,
        thumbnail_url=vm.thumbnail_url if vm else None,
        chapters=vm.chapters if vm else [],
        hashtags=vm.hashtags if vm else [],
        tags=vm.tags if vm else [],
        categories=vm.categories if vm else [],
        view_count=vm.view_count if vm else None,
        like_count=vm.like_count if vm else None,
        comment_count=vm.comment_count if vm else None,
        technical_details=vm.technical_details if vm else {},
        has_transcript=v.transcript is not None,
        has_raw_data=raw_exists
    )

@router.get("/{video_id}/transcript", response_model=TranscriptResponse)
async def get_video_transcript(video_id: str, db: AsyncSession = Depends(get_db_session)):
    stmt = select(Transcript).options(
        selectinload(Transcript.segments)
    ).where(Transcript.video_id == video_id)
    res = await db.execute(stmt)
    t = res.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="No transcript available for this video")

    sorted_segs = sorted(t.segments, key=lambda s: s.sequence_index)
    return TranscriptResponse(
        id=t.id,
        video_id=t.video_id,
        language=t.language,
        requested_language=t.requested_language,
        source_type=t.source_type,
        caption_source=t.caption_source,
        caption_language_code=t.caption_language_code,
        asr_model=t.asr_model,
        is_generated=t.is_generated,
        full_text=t.full_text,
        segment_count=len(sorted_segs),
        segments=sorted_segs
    )

@router.post("/{video_id}/retranscribe")
async def retranscribe_video(
    video_id: str,
    payload: dict = Body(default={}),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Enqueues an asynchronous retranscription job with atomic replacement.
    Returns the job_id immediately so UI can track progress without long-lived HTTP requests.
    """
    stmt = select(Video).where(Video.id == video_id)
    res = await db.execute(stmt)
    v = res.scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=404, detail="Video not found")

    target_lang = payload.get("language") or "en"

    job = ExtractionJob(
        url=v.original_url,
        video_id=v.id,
        processing_mode="RETRANSCRIBE",
        requested_transcript_language=target_lang,
        state="QUEUED",
        progress_percent=0,
        current_step=f"Queued for {target_lang.upper()} retranscription"
    )
    db.add(job)
    await db.commit()

    global_worker_pool.enqueue_job(job.id)

    return {
        "job_id": job.id,
        "video_id": v.id,
        "language": target_lang,
        "status": "QUEUED"
    }

@router.get("/{video_id}/raw")
async def get_video_raw_data(video_id: str):
    raw_path = settings.metadata_path / f"{video_id}.json"
    if not raw_path.exists():
        raise HTTPException(status_code=404, detail="Raw extraction metadata not found")
    try:
        return json.loads(raw_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read raw metadata: {str(e)}")

@router.delete("/{video_id}")
async def delete_video(video_id: str, db: AsyncSession = Depends(get_db_session)):
    stmt = select(Video).where(Video.id == video_id)
    res = await db.execute(stmt)
    v = res.scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=404, detail="Video not found")

    # Clean local artifacts
    meta_file = settings.metadata_path / f"{video_id}.json"
    if meta_file.exists():
        meta_file.unlink()

    transcript_file = settings.transcripts_path / f"{video_id}.txt"
    if transcript_file.exists():
        transcript_file.unlink()

    await db.delete(v)
    await db.commit()
    return {"status": "deleted", "video_id": video_id}

@router.get("/{video_id}/script-metrics", response_model=ScriptMetricsResponse)
async def get_video_script_metrics(video_id: str, db: AsyncSession = Depends(get_db_session)):
    stmt = select(ScriptMetrics).where(ScriptMetrics.video_id == video_id)
    res = await db.execute(stmt)
    sm = res.scalar_one_or_none()

    if not sm:
        # Check if transcript exists to compute metrics on the fly
        t_stmt = select(Transcript).where(Transcript.video_id == video_id)
        t_res = await db.execute(t_stmt)
        transcript = t_res.scalar_one_or_none()
        if not transcript:
            raise HTTPException(status_code=404, detail="UNAVAILABLE_NO_CAPTIONS: No transcript available for this video")
        
        sm = await ScriptAnalysisService.analyze_and_persist(video_id, db)
        if not sm:
            raise HTTPException(status_code=404, detail="UNAVAILABLE_NO_CAPTIONS: No transcript segments could be processed")

    return sm

@router.post("/{video_id}/script-metrics/recalculate", response_model=ScriptMetricsResponse)
async def recalculate_video_script_metrics(video_id: str, db: AsyncSession = Depends(get_db_session)):
    t_stmt = select(Transcript).where(Transcript.video_id == video_id)
    t_res = await db.execute(t_stmt)
    transcript = t_res.scalar_one_or_none()
    if not transcript:
        raise HTTPException(status_code=404, detail="UNAVAILABLE_NO_CAPTIONS: Cannot recalculate metrics without an existing transcript")

    sm = await ScriptAnalysisService.analyze_and_persist(video_id, db)
    if not sm:
        raise HTTPException(status_code=500, detail="Failed to calculate script metrics from transcript")
    return sm

@router.get("/{video_id}/visual-metrics", response_model=VisualMetricsResponse)
async def get_video_visual_metrics(video_id: str, db: AsyncSession = Depends(get_db_session)):
    stmt = select(VisualMetrics).options(
        selectinload(VisualMetrics.frames),
        selectinload(VisualMetrics.ocr_results)
    ).where(VisualMetrics.video_id == video_id)
    res = await db.execute(stmt)
    vm = res.scalar_one_or_none()

    if not vm:
        raise HTTPException(status_code=404, detail="NO_VISUAL_METRICS: Visual analysis has not been executed for this video")

    # Serialize frames with public media URLs
    frames_resp = []
    for f in vm.frames:
        frames_resp.append(FrameResponse(
            id=f.id,
            visual_metrics_id=f.visual_metrics_id,
            video_id=f.video_id,
            frame_number=f.frame_number,
            timestamp=f.timestamp,
            frame_type=f.frame_type,
            file_path=f.file_path,
            file_size_bytes=f.file_size_bytes,
            width=f.width,
            height=f.height,
            created_at=f.created_at,
            image_url=f"/api/v1/videos/frames/{f.id}/image"
        ))

    ocr_resp = []
    for o in vm.ocr_results:
        ocr_resp.append(OCREvidenceItem(
            id=o.id,
            timestamp=o.timestamp,
            detected_text=o.detected_text,
            confidence=o.confidence,
            frame_id=None
        ))

    return VisualMetricsResponse(
        id=vm.id,
        video_id=vm.video_id,
        algorithm_version=vm.algorithm_version,
        scene_threshold=vm.scene_threshold,
        analyzed_at=vm.analyzed_at,
        scene_count=vm.scene_count,
        avg_scene_duration=vm.avg_scene_duration,
        median_scene_duration=vm.median_scene_duration,
        shortest_scene_duration=vm.shortest_scene_duration,
        longest_scene_duration=vm.longest_scene_duration,
        scene_change_frequency=vm.scene_change_frequency,
        scene_timestamps=vm.scene_timestamps or [],
        visual_segments=vm.visual_segments or [],
        segment_duration_distribution=vm.segment_duration_distribution or {},
        visual_activity_timeline=vm.visual_activity_timeline or [],
        technical_properties=vm.technical_properties or {},
        frames=frames_resp,
        ocr_results=ocr_resp,
        ocr_available=False
    )

@router.post("/{video_id}/visual-analysis", response_model=VisualMetricsResponse)
async def start_video_visual_analysis(
    video_id: str, 
    keep_media: bool = False,
    db: AsyncSession = Depends(get_db_session)
):
    vm, err = await VisualAnalysisService.analyze_video(video_id, db, force_keep=keep_media)
    if err or not vm:
        raise HTTPException(status_code=500, detail=err or "Visual analysis failed")

    # Reload with frames
    stmt = select(VisualMetrics).options(
        selectinload(VisualMetrics.frames),
        selectinload(VisualMetrics.ocr_results)
    ).where(VisualMetrics.id == vm.id)
    res = await db.execute(stmt)
    loaded_vm = res.scalar_one()

    frames_resp = [
        FrameResponse(
            id=f.id,
            visual_metrics_id=f.visual_metrics_id,
            video_id=f.video_id,
            frame_number=f.frame_number,
            timestamp=f.timestamp,
            frame_type=f.frame_type,
            file_path=f.file_path,
            file_size_bytes=f.file_size_bytes,
            width=f.width,
            height=f.height,
            created_at=f.created_at,
            image_url=f"/api/v1/videos/frames/{f.id}/image"
        )
        for f in loaded_vm.frames
    ]

    return VisualMetricsResponse(
        id=loaded_vm.id,
        video_id=loaded_vm.video_id,
        algorithm_version=loaded_vm.algorithm_version,
        scene_threshold=loaded_vm.scene_threshold,
        analyzed_at=loaded_vm.analyzed_at,
        scene_count=loaded_vm.scene_count,
        avg_scene_duration=loaded_vm.avg_scene_duration,
        median_scene_duration=loaded_vm.median_scene_duration,
        shortest_scene_duration=loaded_vm.shortest_scene_duration,
        longest_scene_duration=loaded_vm.longest_scene_duration,
        scene_change_frequency=loaded_vm.scene_change_frequency,
        scene_timestamps=loaded_vm.scene_timestamps or [],
        visual_segments=loaded_vm.visual_segments or [],
        segment_duration_distribution=loaded_vm.segment_duration_distribution or {},
        visual_activity_timeline=loaded_vm.visual_activity_timeline or [],
        technical_properties=loaded_vm.technical_properties or {},
        frames=frames_resp,
        ocr_results=[],
        ocr_available=False
    )

@router.get("/frames/{frame_id}/image")
async def get_frame_image(frame_id: str, db: AsyncSession = Depends(get_db_session)):
    from fastapi.responses import FileResponse
    stmt = select(Frame).where(Frame.id == frame_id)
    res = await db.execute(stmt)
    f = res.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="Frame record not found")

    full_path = settings.project_root / f.file_path
    # Path traversal protection
    try:
        full_path.resolve().relative_to(settings.frames_path.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Frame image file missing")

    return FileResponse(str(full_path), media_type="image/jpeg")
