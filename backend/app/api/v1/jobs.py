from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from backend.app.db.session import get_db_session
from backend.app.db.models.entities import ExtractionJob, Video
from backend.app.schemas.job import (
    JobBatchValidateRequest, JobBatchValidateResponse,
    JobSubmitRequest, JobStatusResponse
)
from backend.app.services.url_service import URLService
from backend.app.services.job_worker import global_worker_pool

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.post("/validate", response_model=JobBatchValidateResponse)
async def validate_urls(payload: JobBatchValidateRequest, db: AsyncSession = Depends(get_db_session)):
    batch = URLService.parse_batch(payload.raw_text)
    
    # Check if already in library
    for item in batch["items"]:
        if item["is_valid"]:
            stmt = select(Video.id).where(Video.platform == item["platform"], Video.platform_video_id == item["video_id"])
            res = await db.execute(stmt)
            if res.scalar_one_or_none():
                item["already_in_library"] = True

    return batch

@router.post("", response_model=List[JobStatusResponse])
async def submit_jobs(payload: JobSubmitRequest, db: AsyncSession = Depends(get_db_session)):
    submitted_jobs: List[ExtractionJob] = []

    for raw_url in payload.urls:
        url_str = raw_url.strip()
        if not url_str:
            continue

        parsed = URLService.parse_url(url_str)
        target_url = parsed.canonical_url if parsed.is_valid else url_str
        mode = payload.overrides.get(url_str, payload.default_mode)
        language = payload.language_overrides.get(url_str, payload.default_language)

        # Active duplicate protection: if there is already an active job for the same URL + mode + language
        active_stmt = select(ExtractionJob).where(
            ExtractionJob.url == target_url,
            ExtractionJob.processing_mode == mode,
            ExtractionJob.requested_transcript_language == language,
            ExtractionJob.state.in_(["QUEUED", "VALIDATING", "EXTRACTING_METADATA", "GETTING_CAPTIONS", "PROCESSING_MEDIA", "PROCESSING_TRANSCRIPT", "TRANSCRIBING_LOCAL_ASR", "ACQUIRING_AUDIO", "PREPARING_AUDIO"])
        )
        existing_res = await db.execute(active_stmt)
        existing_job = existing_res.scalar_one_or_none()
        if existing_job:
            # Reuse existing active job rather than creating redundant upstream calls
            submitted_jobs.append(existing_job)
            continue

        job = ExtractionJob(
            url=target_url,
            processing_mode=mode,
            requested_transcript_language=language,
            state="QUEUED",
            progress_percent=0,
            current_step="Enqueued for extraction"
        )
        db.add(job)
        await db.flush()
        submitted_jobs.append(job)
        global_worker_pool.enqueue_job(job.id)

    await db.commit()
    return submitted_jobs

@router.get("", response_model=List[JobStatusResponse])
async def list_jobs(
    state: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(ExtractionJob).order_by(desc(ExtractionJob.created_at)).limit(limit)
    if state:
        stmt = stmt.where(ExtractionJob.state == state)
    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db_session)):
    res = await db.execute(select(ExtractionJob).where(ExtractionJob.id == job_id))
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str, db: AsyncSession = Depends(get_db_session)):
    await global_worker_pool.cancel_job(job_id)
    res = await db.execute(select(ExtractionJob).where(ExtractionJob.id == job_id))
    job = res.scalar_one_or_none()
    if job:
        job.state = "CANCELLED"
        job.current_step = "Cancelled by user"
        await db.commit()
    return {"status": "cancelled", "job_id": job_id}

@router.post("/{job_id}/retry", response_model=JobStatusResponse)
async def retry_job(job_id: str, db: AsyncSession = Depends(get_db_session)):
    res = await db.execute(select(ExtractionJob).where(ExtractionJob.id == job_id))
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.state = "QUEUED"
    job.progress_percent = 0
    job.current_step = "Retrying job"
    job.error_details = None
    job.warnings = []
    await db.commit()

    global_worker_pool.enqueue_job(job.id)
    return job
