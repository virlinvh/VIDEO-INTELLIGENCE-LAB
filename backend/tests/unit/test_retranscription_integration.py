import pytest
import uuid
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.session import async_session_factory
from backend.app.db.models.entities import Video, Transcript, TranscriptSegment, ExtractionJob
from sqlalchemy import select

client = TestClient(app)

@pytest.mark.asyncio
async def test_retranscription_real_db_and_job_lifecycle():
    video_id = str(uuid.uuid4())
    
    # 1. Insert real video and initial English transcript into SQLite
    async with async_session_factory() as session:
        v = Video(
            id=video_id,
            platform="youtube",
            platform_video_id="test_vid_123",
            original_url="https://www.youtube.com/watch?v=test_vid_123",
            title="Test Video for Retranscription",
            duration_seconds=60,
            processing_status="COMPLETED"
        )
        t = Transcript(
            video_id=video_id,
            language="en",
            requested_language="en",
            source_type="automatic",
            caption_source="YouTube Automatic Captions",
            is_generated=True,
            full_text="Hello world this is initial english transcript."
        )
        session.add(v)
        session.add(t)
        await session.flush()

        seg = TranscriptSegment(
            transcript_id=t.id,
            sequence_index=0,
            start_time=0.0,
            end_time=5.0,
            duration=5.0,
            text="Hello world this is initial english transcript.",
            word_count=7
        )
        session.add(seg)
        await session.commit()

    # 2. Call POST /api/v1/videos/{video_id}/retranscribe with language "ta"
    response = client.post(
        f"/api/v1/videos/{video_id}/retranscribe",
        json={"language": "ta"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["language"] == "ta"
    assert data["status"] == "QUEUED"

    job_id = data["job_id"]

    # 3. Verify ExtractionJob record created in database with requested_transcript_language
    async with async_session_factory() as session:
        j_res = await session.execute(select(ExtractionJob).where(ExtractionJob.id == job_id))
        job = j_res.scalar_one_or_none()
        assert job is not None
        assert job.processing_mode == "RETRANSCRIBE"
        assert job.requested_transcript_language == "ta"
        assert job.video_id == video_id

    # 4. Clean up test record
    async with async_session_factory() as session:
        v_to_del = (await session.execute(select(Video).where(Video.id == video_id))).scalar_one_or_none()
        if v_to_del:
            await session.delete(v_to_del)
        j_to_del = (await session.execute(select(ExtractionJob).where(ExtractionJob.id == job_id))).scalar_one_or_none()
        if j_to_del:
            await session.delete(j_to_del)
        await session.commit()
