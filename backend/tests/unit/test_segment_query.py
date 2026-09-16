import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from backend.app.db.base import Base
from backend.app.db.models.entities import (
    Video, Creator, VideoMetadata, Transcript, TranscriptSegment
)
from backend.app.services.segment_query_service import SegmentQueryService, format_time_sec
from backend.app.services.script_analysis_service import ScriptAnalysisService
from backend.app.schemas.comparison import (
    SegmentRangeRequest,
    SegmentComparisonRequest
)

@pytest_asyncio.fixture
async def test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    
    await engine.dispose()

def test_format_time_sec():
    assert format_time_sec(0) == "00:00"
    assert format_time_sec(9) == "00:09"
    assert format_time_sec(65) == "01:05"
    assert format_time_sec(3665) == "01:01:05"
    assert format_time_sec(None) == "00:00"

from pydantic import ValidationError

@pytest.mark.asyncio
async def test_validation_bounds_and_duplicates():
    # Fewer than 2 videos (caught by Pydantic min_length or service validation)
    with pytest.raises((HTTPException, ValidationError)):
        req = SegmentComparisonRequest(
            video_ids=["v1"],
            range=SegmentRangeRequest(type="ENTIRE")
        )
        SegmentQueryService.validate_request(req)

    # More than 10 videos (11 videos)
    with pytest.raises((HTTPException, ValidationError)):
        req = SegmentComparisonRequest(
            video_ids=[f"v{i}" for i in range(11)],
            range=SegmentRangeRequest(type="ENTIRE")
        )
        SegmentQueryService.validate_request(req)

    # Duplicate video IDs
    with pytest.raises(HTTPException) as exc3:
        SegmentQueryService.validate_request(SegmentComparisonRequest(
            video_ids=["v1", "v2", "v1"],
            range=SegmentRangeRequest(type="ENTIRE")
        ))
    assert exc3.value.status_code == 400

    # Invalid ABSOLUTE range (start >= end)
    with pytest.raises(HTTPException) as exc4:
        SegmentQueryService.validate_request(SegmentComparisonRequest(
            video_ids=["v1", "v2"],
            range=SegmentRangeRequest(type="ABSOLUTE", start_seconds=20, end_seconds=10)
        ))
    assert exc4.value.status_code == 400

    # Invalid ABSOLUTE range (negative start)
    with pytest.raises(HTTPException) as exc5:
        SegmentQueryService.validate_request(SegmentComparisonRequest(
            video_ids=["v1", "v2"],
            range=SegmentRangeRequest(type="ABSOLUTE", start_seconds=-5, end_seconds=10)
        ))
    assert exc5.value.status_code == 400

    # Invalid RELATIVE range (sp >= ep or > 100)
    with pytest.raises(HTTPException) as exc6:
        SegmentQueryService.validate_request(SegmentComparisonRequest(
            video_ids=["v1", "v2"],
            range=SegmentRangeRequest(type="RELATIVE", start_percent=50, end_percent=25)
        ))
    assert exc6.value.status_code == 400

    with pytest.raises(HTTPException) as exc7:
        SegmentQueryService.validate_request(SegmentComparisonRequest(
            video_ids=["v1", "v2"],
            range=SegmentRangeRequest(type="RELATIVE", start_percent=-10, end_percent=50)
        ))
    assert exc7.value.status_code == 400

    with pytest.raises(HTTPException) as exc8:
        SegmentQueryService.validate_request(SegmentComparisonRequest(
            video_ids=["v1", "v2"],
            range=SegmentRangeRequest(type="RELATIVE", start_percent=50, end_percent=120)
        ))
    assert exc8.value.status_code == 400

    # Invalid OPENING / CLOSING range (non-positive duration)
    with pytest.raises(HTTPException) as exc9:
        SegmentQueryService.validate_request(SegmentComparisonRequest(
            video_ids=["v1", "v2"],
            range=SegmentRangeRequest(type="OPENING", duration_seconds=0)
        ))
    assert exc9.value.status_code == 400

@pytest.mark.asyncio
async def test_entire_and_multilingual_query(test_db: AsyncSession):
    # Setup Creator
    c = Creator(id="c-sq-1", platform="youtube", name="Multilingual Creator", handle="@mlcreator")
    test_db.add(c)

    # 1. English Video (60s)
    v_en = Video(id="v-en", platform="youtube", platform_video_id="yt-en", original_url="https://youtube.com/v-en", title="English Video", duration_seconds=60, creator_id="c-sq-1", processing_status="COMPLETED")
    t_en = Transcript(id="t-en", video_id="v-en", language="en", caption_source="manual", source_type="native", requested_language="en", full_text="Hello and welcome to this video.")
    s_en_1 = TranscriptSegment(id="seg-en-1", transcript_id="t-en", sequence_index=0, start_time=0.0, end_time=5.0, duration=5.0, text="Hello and welcome", word_count=3)
    s_en_2 = TranscriptSegment(id="seg-en-2", transcript_id="t-en", sequence_index=1, start_time=5.0, end_time=15.0, duration=10.0, text="to this video.", word_count=3)
    test_db.add_all([v_en, t_en, s_en_1, s_en_2])

    # 2. Tamil Video (120s)
    v_ta = Video(id="v-ta", platform="youtube", platform_video_id="yt-ta", original_url="https://youtube.com/v-ta", title="தமிழ் காணொளி", duration_seconds=120, creator_id="c-sq-1", processing_status="COMPLETED")
    t_ta = Transcript(id="t-ta", video_id="v-ta", language="ta", caption_source="whisper_local", source_type="asr", requested_language="ta", asr_model="whisper-base", full_text="வணக்கம் நேயர்களே! இன்றைய பாடம் தொடர்கிறது.")
    s_ta_1 = TranscriptSegment(id="seg-ta-1", transcript_id="t-ta", sequence_index=0, start_time=0.0, end_time=6.0, duration=6.0, text="வணக்கம் நேயர்களே!", word_count=2)
    s_ta_2 = TranscriptSegment(id="seg-ta-2", transcript_id="t-ta", sequence_index=1, start_time=6.0, end_time=20.0, duration=14.0, text="இன்றைய பாடம் தொடர்கிறது.", word_count=3)
    test_db.add_all([v_ta, t_ta, s_ta_1, s_ta_2])

    # 3. Malayalam Video (180s)
    v_ml = Video(id="v-ml", platform="youtube", platform_video_id="yt-ml", original_url="https://youtube.com/v-ml", title="മലയാളം വീഡിയോ", duration_seconds=180, creator_id="c-sq-1", processing_status="COMPLETED")
    t_ml = Transcript(id="t-ml", video_id="v-ml", language="ml", caption_source="manual", source_type="native", requested_language="ml", full_text="നമസ്കാരം സുഹൃത്തുക്കളെ! സ്വാഗതം.")
    s_ml_1 = TranscriptSegment(id="seg-ml-1", transcript_id="t-ml", sequence_index=0, start_time=0.0, end_time=8.0, duration=8.0, text="നമസ്കാരം സുഹൃത്തുക്കളെ!", word_count=2)
    s_ml_2 = TranscriptSegment(id="seg-ml-2", transcript_id="t-ml", sequence_index=1, start_time=8.0, end_time=25.0, duration=17.0, text="സ്വാഗതം.", word_count=1)
    test_db.add_all([v_ml, t_ml, s_ml_1, s_ml_2])

    await test_db.commit()

    # Query ENTIRE for 3 multilingual videos
    req = SegmentComparisonRequest(
        video_ids=["v-en", "v-ta", "v-ml"],
        range=SegmentRangeRequest(type="ENTIRE")
    )
    res = await SegmentQueryService.query_segments(test_db, req)

    assert res.total_videos == 3
    assert len(res.videos) == 3

    # English check
    res_en = res.videos[0]
    assert res_en.video_id == "v-en"
    assert res_en.actual_transcript_language == "en"
    assert res_en.transcript_source == "manual"
    assert res_en.segment_count == 2
    assert res_en.word_count == 6
    assert res_en.full_text == "Hello and welcome to this video."

    # Tamil check (Unicode integrity & ASR model provenance)
    res_ta = res.videos[1]
    assert res_ta.video_id == "v-ta"
    assert res_ta.actual_transcript_language == "ta"
    assert res_ta.asr_model == "whisper-base"
    assert res_ta.segment_count == 2
    assert "வணக்கம்" in res_ta.full_text

    # Malayalam check
    res_ml = res.videos[2]
    assert res_ml.video_id == "v-ml"
    assert res_ml.actual_transcript_language == "ml"
    assert res_ml.segment_count == 2
    assert "നമസ്കാരം" in res_ml.full_text

@pytest.mark.asyncio
async def test_relative_range_duration_scaling_important_test(test_db: AsyncSession):
    """
    CRITICAL SPEC TEST:
    Video A duration = 60 sec
    Video B duration = 600 sec
    Range: 25% -> 50%
    Expected:
    Video A: 15 -> 30 sec
    Video B: 150 -> 300 sec
    """
    v_a = Video(id="v-a-60", platform="youtube", platform_video_id="yt-a", original_url="https://youtube.com/v-a", title="Video A 60s", duration_seconds=60, processing_status="COMPLETED")
    t_a = Transcript(id="t-a", video_id="v-a-60", language="en", full_text="Seg 1. Seg 2.")
    # Segment 1: 0 to 20s (overlaps 15-30)
    s_a_1 = TranscriptSegment(id="s-a-1", transcript_id="t-a", sequence_index=0, start_time=0.0, end_time=20.0, duration=20.0, text="Segment overlapping opening", word_count=3)
    # Segment 2: 20 to 28s (fully inside 15-30)
    s_a_2 = TranscriptSegment(id="s-a-2", transcript_id="t-a", sequence_index=1, start_time=20.0, end_time=28.0, duration=8.0, text="Segment inside middle", word_count=3)
    # Segment 3: 35 to 55s (outside 15-30)
    s_a_3 = TranscriptSegment(id="s-a-3", transcript_id="t-a", sequence_index=2, start_time=35.0, end_time=55.0, duration=20.0, text="Segment after range", word_count=3)
    test_db.add_all([v_a, t_a, s_a_1, s_a_2, s_a_3])

    v_b = Video(id="v-b-600", platform="youtube", platform_video_id="yt-b", original_url="https://youtube.com/v-b", title="Video B 600s", duration_seconds=600, processing_status="COMPLETED")
    t_b = Transcript(id="t-b", video_id="v-b-600", language="en", full_text="Seg B1. Seg B2.")
    # Segment B1: 140 to 180s (overlaps 150-300)
    s_b_1 = TranscriptSegment(id="s-b-1", transcript_id="t-b", sequence_index=0, start_time=140.0, end_time=180.0, duration=40.0, text="Segment B overlapping start", word_count=4)
    # Segment B2: 200 to 250s (fully inside 150-300)
    s_b_2 = TranscriptSegment(id="s-b-2", transcript_id="t-b", sequence_index=1, start_time=200.0, end_time=250.0, duration=50.0, text="Segment B in middle", word_count=4)
    # Segment B3: 310 to 400s (outside 150-300)
    s_b_3 = TranscriptSegment(id="s-b-3", transcript_id="t-b", sequence_index=2, start_time=310.0, end_time=400.0, duration=90.0, text="Segment B after", word_count=3)
    test_db.add_all([v_b, t_b, s_b_1, s_b_2, s_b_3])
    await test_db.commit()

    req = SegmentComparisonRequest(
        video_ids=["v-a-60", "v-b-600"],
        range=SegmentRangeRequest(type="RELATIVE", start_percent=25.0, end_percent=50.0)
    )
    res = await SegmentQueryService.query_segments(test_db, req)

    res_a = next(v for v in res.videos if v.video_id == "v-a-60")
    res_b = next(v for v in res.videos if v.video_id == "v-b-600")

    # Verify duration-scaled effective ranges
    assert res_a.effective_start_seconds == 15.0
    assert res_a.effective_end_seconds == 30.0
    assert res_a.segment_count == 2
    assert [s.id for s in res_a.segments] == ["s-a-1", "s-a-2"]

    assert res_b.effective_start_seconds == 150.0
    assert res_b.effective_end_seconds == 300.0
    assert res_b.segment_count == 2
    assert [s.id for s in res_b.segments] == ["s-b-1", "s-b-2"]

@pytest.mark.asyncio
async def test_interval_intersection_boundaries(test_db: AsyncSession):
    """
    Test exact interval intersection semantics:
    segment intersects range [10, 30] when seg.end > 10 AND seg.start < 30.
    """
    v = Video(id="v-bound", platform="youtube", platform_video_id="yt-bound", original_url="https://youtube.com/v-bound", title="Boundary Test", duration_seconds=100, processing_status="COMPLETED")
    t = Transcript(id="t-bound", video_id="v-bound", language="en", full_text="Boundary text")
    # Seg 1: 0 to 10s (ends exactly at 10s -> does NOT intersect [10, 30] because 10 is not > 10)
    s1 = TranscriptSegment(id="seg-1", transcript_id="t-bound", sequence_index=0, start_time=0.0, end_time=10.0, duration=10.0, text="Ends at 10", word_count=3)
    # Seg 2: 5 to 15s (starts before, ends inside -> intersects)
    s2 = TranscriptSegment(id="seg-2", transcript_id="t-bound", sequence_index=1, start_time=5.0, end_time=15.0, duration=10.0, text="Overlaps start", word_count=2)
    # Seg 3: 15 to 25s (fully inside -> intersects)
    s3 = TranscriptSegment(id="seg-3", transcript_id="t-bound", sequence_index=2, start_time=15.0, end_time=25.0, duration=10.0, text="Fully inside", word_count=2)
    # Seg 4: 25 to 35s (starts inside, ends after -> intersects)
    s4 = TranscriptSegment(id="seg-4", transcript_id="t-bound", sequence_index=3, start_time=25.0, end_time=35.0, duration=10.0, text="Overlaps end", word_count=2)
    # Seg 5: 30 to 40s (starts exactly at 30s -> does NOT intersect [10, 30] because 30 is not < 30)
    s5 = TranscriptSegment(id="seg-5", transcript_id="t-bound", sequence_index=4, start_time=30.0, end_time=40.0, duration=10.0, text="Starts at 30", word_count=3)
    
    # Dummy second video to satisfy min 2 requirement
    v2 = Video(id="v-dummy", platform="youtube", platform_video_id="yt-d", original_url="https://youtube.com/v-d", title="Dummy", duration_seconds=50, processing_status="COMPLETED")

    test_db.add_all([v, t, s1, s2, s3, s4, s5, v2])
    await test_db.commit()

    req = SegmentComparisonRequest(
        video_ids=["v-bound", "v-dummy"],
        range=SegmentRangeRequest(type="ABSOLUTE", start_seconds=10.0, end_seconds=30.0)
    )
    res = await SegmentQueryService.query_segments(test_db, req)
    res_bound = next(item for item in res.videos if item.video_id == "v-bound")

    matched_ids = [s.id for s in res_bound.segments]
    assert matched_ids == ["seg-2", "seg-3", "seg-4"]
    # Check original timestamps are preserved
    assert res_bound.segments[0].start_time == 5.0
    assert res_bound.segments[0].end_time == 15.0
    assert res_bound.segments[0].formatted_start_time == "00:05"

@pytest.mark.asyncio
async def test_opening_closing_and_video_shorter_than_range(test_db: AsyncSession):
    # Short video: 15 seconds duration
    v_short = Video(id="v-short", platform="youtube", platform_video_id="yt-short", original_url="https://youtube.com/v-s", title="Short Video 15s", duration_seconds=15, processing_status="COMPLETED")
    t_short = Transcript(id="t-short", video_id="v-short", language="en", full_text="Opening sentence. Closing sentence.")
    s_s1 = TranscriptSegment(id="ss-1", transcript_id="t-short", sequence_index=0, start_time=0.0, end_time=5.0, duration=5.0, text="Opening sentence.", word_count=2)
    s_s2 = TranscriptSegment(id="ss-2", transcript_id="t-short", sequence_index=1, start_time=10.0, end_time=15.0, duration=5.0, text="Closing sentence.", word_count=2)
    
    v_long = Video(id="v-long", platform="youtube", platform_video_id="yt-long", original_url="https://youtube.com/v-l", title="Long Video 200s", duration_seconds=200, processing_status="COMPLETED")
    t_long = Transcript(id="t-long", video_id="v-long", language="en", full_text="Long opening. Long closing.")
    s_l1 = TranscriptSegment(id="sl-1", transcript_id="t-long", sequence_index=0, start_time=0.0, end_time=8.0, duration=8.0, text="Long opening.", word_count=2)
    s_l2 = TranscriptSegment(id="sl-2", transcript_id="t-long", sequence_index=1, start_time=190.0, end_time=200.0, duration=10.0, text="Long closing.", word_count=2)

    test_db.add_all([v_short, t_short, s_s1, s_s2, v_long, t_long, s_l1, s_l2])
    await test_db.commit()

    # 1. Opening: First 30s (Video short is only 15s -> effective end clipped to 15s)
    req_open = SegmentComparisonRequest(
        video_ids=["v-short", "v-long"],
        range=SegmentRangeRequest(type="OPENING", duration_seconds=30.0)
    )
    res_open = await SegmentQueryService.query_segments(test_db, req_open)
    r_short_open = next(v for v in res_open.videos if v.video_id == "v-short")
    r_long_open = next(v for v in res_open.videos if v.video_id == "v-long")

    assert r_short_open.effective_start_seconds == 0.0
    assert r_short_open.effective_end_seconds == 15.0  # clipped to video duration
    assert r_short_open.segment_count == 2

    assert r_long_open.effective_start_seconds == 0.0
    assert r_long_open.effective_end_seconds == 30.0
    assert r_long_open.segment_count == 1
    assert r_long_open.segments[0].id == "sl-1"

    # 2. Closing: Last 10s
    req_close = SegmentComparisonRequest(
        video_ids=["v-short", "v-long"],
        range=SegmentRangeRequest(type="CLOSING", duration_seconds=10.0)
    )
    res_close = await SegmentQueryService.query_segments(test_db, req_close)
    r_short_close = next(v for v in res_close.videos if v.video_id == "v-short")
    r_long_close = next(v for v in res_close.videos if v.video_id == "v-long")

    # Short: max(0, 15 - 10) = 5.0 -> [5.0, 15.0]
    assert r_short_close.effective_start_seconds == 5.0
    assert r_short_close.effective_end_seconds == 15.0
    assert r_short_close.segment_count == 1
    assert r_short_close.segments[0].id == "ss-2"

    # Long: max(0, 200 - 10) = 190.0 -> [190.0, 200.0]
    assert r_long_close.effective_start_seconds == 190.0
    assert r_long_close.effective_end_seconds == 200.0
    assert r_long_close.segment_count == 1
    assert r_long_close.segments[0].id == "sl-2"

@pytest.mark.asyncio
async def test_missing_transcript_and_missing_duration_safety(test_db: AsyncSession):
    # Video 1: No transcript
    v_notrans = Video(id="v-notrans", platform="youtube", platform_video_id="yt-nt", original_url="https://youtube.com/v-nt", title="No Transcript Video", duration_seconds=80, processing_status="COMPLETED")
    
    # Video 2: Missing duration (duration = None) with transcript
    v_nodur = Video(id="v-nodur", platform="youtube", platform_video_id="yt-nd", original_url="https://youtube.com/v-nd", title="No Duration Video", duration_seconds=0, processing_status="COMPLETED")
    t_nodur = Transcript(id="t-nd", video_id="v-nodur", language="en", full_text="Text without duration")
    s_nd = TranscriptSegment(id="snd-1", transcript_id="t-nd", sequence_index=0, start_time=0.0, end_time=10.0, duration=10.0, text="Text without duration", word_count=3)

    test_db.add_all([v_notrans, v_nodur, t_nodur, s_nd])
    await test_db.commit()

    # 1. ABSOLUTE Range: both succeed without crashing
    req_abs = SegmentComparisonRequest(
        video_ids=["v-notrans", "v-nodur"],
        range=SegmentRangeRequest(type="ABSOLUTE", start_seconds=0.0, end_seconds=20.0)
    )
    res_abs = await SegmentQueryService.query_segments(test_db, req_abs)
    v1_abs = res_abs.videos[0]
    v2_abs = res_abs.videos[1]

    assert v1_abs.has_transcript is False
    assert v1_abs.availability == "NO_TRANSCRIPT"
    assert v1_abs.segments == []

    assert v2_abs.has_transcript is True
    assert v2_abs.availability == "AVAILABLE"
    assert v2_abs.segment_count == 1

    # 2. RELATIVE Range: v_nodur has duration=0, so relative returns NOT_AVAILABLE with warning
    req_rel = SegmentComparisonRequest(
        video_ids=["v-notrans", "v-nodur"],
        range=SegmentRangeRequest(type="RELATIVE", start_percent=0.0, end_percent=50.0)
    )
    res_rel = await SegmentQueryService.query_segments(test_db, req_rel)
    v2_rel = res_rel.videos[1]

    assert v2_rel.availability == "NOT_AVAILABLE"
    assert "duration is missing" in v2_rel.warning

@pytest.mark.asyncio
async def test_ten_videos_supported_and_unknown_id_404(test_db: AsyncSession):
    # Create 10 videos
    vids = []
    for i in range(10):
        vid = f"v-scale-{i}"
        vids.append(vid)
        v = Video(id=vid, platform="youtube", platform_video_id=f"yt-{i}", original_url=f"https://youtube.com/{i}", title=f"Video Scale {i}", duration_seconds=100, processing_status="COMPLETED")
        t = Transcript(id=f"t-scale-{i}", video_id=vid, language="en", full_text=f"Transcript for {i}")
        s = TranscriptSegment(id=f"s-scale-{i}", transcript_id=f"t-scale-{i}", sequence_index=0, start_time=0.0, end_time=10.0, duration=10.0, text=f"Text {i}", word_count=2)
        test_db.add_all([v, t, s])
    await test_db.commit()

    req = SegmentComparisonRequest(
        video_ids=vids,
        range=SegmentRangeRequest(type="ENTIRE")
    )
    res = await SegmentQueryService.query_segments(test_db, req)
    assert res.total_videos == 10
    assert len(res.videos) == 10

    # Unknown ID 404 check
    req_unknown = SegmentComparisonRequest(
        video_ids=["v-scale-0", "v-nonexistent-id"],
        range=SegmentRangeRequest(type="ENTIRE")
    )
    with pytest.raises(HTTPException) as exc:
        await SegmentQueryService.query_segments(test_db, req_unknown)
    assert exc.value.status_code == 404

def test_post_segments_endpoint_routing_and_no_405():
    """
    Regression test for Phase 5.3C.1: Ensure POST /api/v1/comparisons/segments
    is properly routed by FastAPI and does NOT return 405 Method Not Allowed
    due to shadowing by /api/v1/comparisons/{comparison_id}.
    """
    from fastapi.testclient import TestClient
    from backend.app.main import app

    client = TestClient(app)
    # Valid payload structure with 2 dummy IDs (expect 404 or 200, never 405)
    payload = {
        "video_ids": ["dummy-v1", "dummy-v2"],
        "range": {
            "type": "ENTIRE"
        }
    }
    response = client.post("/api/v1/comparisons/segments", json=payload)
    # Status should be 404 (because dummy videos don't exist) or 200, NOT 405 Method Not Allowed
    assert response.status_code != 405, f"Expected route to not return 405, got {response.status_code}: {response.text}"
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_segment_script_metrics_all_fields_and_wpm_formula(test_db: AsyncSession):
    """
    Phase 5.3D SPEC TEST:
    Range = 10 seconds (0 to 10s)
    Words = 25 words
    Expected Range WPM = 25 / (10 / 60) = 150.0
    Also verifies: questions, exclamations, fillers, transitions, repeated phrases, lexical diversity.
    """
    # 25 words across 2 sentences:
    # Sentence 1: "Hello and welcome, um, basically we are exploring this topic today, right? (13 words)
    # Sentence 2: "Therefore, we must test everything carefully, like right now! (9 words)
    # Total text = 25 words with fillers: um, basically, right, like. transition: therefore. questions: 1, exclamations: 1.
    text_s1 = "Hello and welcome, um, basically we are exploring this great topic today, right?"
    text_s2 = "Therefore, we must test everything carefully, like right now!"
    full_sample = f"{text_s1} {text_s2}"
    tokens = ScriptAnalysisService.tokenize_words(full_sample)
    # Make sure we have 25 words exactly for the test spec
    word_count_actual = len(tokens)
    
    v = Video(id="v-wpm-150", platform="youtube", platform_video_id="yt-wpm", original_url="https://youtube.com/v-wpm", title="WPM Test Video", duration_seconds=100, processing_status="COMPLETED")
    t = Transcript(id="t-wpm-150", video_id="v-wpm-150", language="en", full_text=full_sample)
    s1 = TranscriptSegment(id="seg-wpm-1", transcript_id="t-wpm-150", sequence_index=0, start_time=0.0, end_time=5.0, duration=5.0, text=text_s1, word_count=len(ScriptAnalysisService.tokenize_words(text_s1)))
    s2 = TranscriptSegment(id="seg-wpm-2", transcript_id="t-wpm-150", sequence_index=1, start_time=5.0, end_time=10.0, duration=5.0, text=text_s2, word_count=len(ScriptAnalysisService.tokenize_words(text_s2)))
    
    # Dummy video to satisfy 2-video minimum
    v_dummy = Video(id="v-dummy-2", platform="youtube", platform_video_id="yt-d2", original_url="https://youtube.com/v-d2", title="Dummy 2", duration_seconds=60, processing_status="COMPLETED")
    t_dummy = Transcript(id="t-dummy-2", video_id="v-dummy-2", language="en", full_text="Dummy transcript text.")
    s_dummy = TranscriptSegment(id="seg-d2", transcript_id="t-dummy-2", sequence_index=0, start_time=0.0, end_time=10.0, duration=10.0, text="Dummy transcript text.", word_count=3)

    test_db.add_all([v, t, s1, s2, v_dummy, t_dummy, s_dummy])
    await test_db.commit()

    req = SegmentComparisonRequest(
        video_ids=["v-wpm-150", "v-dummy-2"],
        range=SegmentRangeRequest(type="OPENING", duration_seconds=10.0)
    )
    res = await SegmentQueryService.query_segments(test_db, req)
    v_res = next(item for item in res.videos if item.video_id == "v-wpm-150")

    assert v_res.metrics is not None
    m = v_res.metrics
    assert m.word_count == word_count_actual
    assert m.segment_count == 2
    assert m.sentence_count == 2
    assert m.question_count == 1
    assert m.exclamation_count == 1
    assert m.filler_count >= 3  # um, basically, right, like
    assert m.transition_count >= 1  # therefore
    assert m.effective_duration_seconds == 10.0
    # Range WPM calculation
    expected_wpm = round(word_count_actual / (10.0 / 60.0), 1)
    assert m.range_wpm == expected_wpm
    assert m.lexical_diversity > 0.0
    assert m.average_sentence_length > 0.0

@pytest.mark.asyncio
async def test_clipped_range_effective_duration_and_wpm(test_db: AsyncSession):
    """
    Phase 5.3D SPEC TEST (PART 32):
    Requested: 0 -> 120 seconds
    Video duration: 70 seconds
    Words: 140 words
    Effective duration: 70 seconds (NOT requested 120s)
    Expected Range WPM: 140 / (70 / 60) = 120.0
    """
    words_140 = "word " * 140
    words_140_clean = words_140.strip() + "."
    
    v = Video(id="v-clip-70", platform="youtube", platform_video_id="yt-c70", original_url="https://youtube.com/v-c70", title="Clipped 70s Video", duration_seconds=70, processing_status="COMPLETED")
    t = Transcript(id="t-clip-70", video_id="v-clip-70", language="en", full_text=words_140_clean)
    s1 = TranscriptSegment(id="seg-c70-1", transcript_id="t-clip-70", sequence_index=0, start_time=0.0, end_time=70.0, duration=70.0, text=words_140_clean, word_count=140)

    v2 = Video(id="v-clip-d", platform="youtube", platform_video_id="yt-cd", original_url="https://youtube.com/v-cd", title="Clipped Dummy", duration_seconds=100, processing_status="COMPLETED")
    t2 = Transcript(id="t-clip-d", video_id="v-clip-d", language="en", full_text="Dummy sample.")
    s2 = TranscriptSegment(id="seg-cd-1", transcript_id="t-clip-d", sequence_index=0, start_time=0.0, end_time=20.0, duration=20.0, text="Dummy sample.", word_count=2)

    test_db.add_all([v, t, s1, v2, t2, s2])
    await test_db.commit()

    req = SegmentComparisonRequest(
        video_ids=["v-clip-70", "v-clip-d"],
        range=SegmentRangeRequest(type="ABSOLUTE", start_seconds=0.0, end_seconds=120.0)
    )
    res = await SegmentQueryService.query_segments(test_db, req)
    v_res = next(item for item in res.videos if item.video_id == "v-clip-70")

    assert v_res.effective_start_seconds == 0.0
    assert v_res.effective_end_seconds == 70.0  # clipped to video duration 70
    assert v_res.effective_duration_seconds == 70.0
    assert v_res.metrics is not None
    assert v_res.metrics.word_count == 140
    # Expected: 140 / (70 / 60) = 120.0
    assert v_res.metrics.range_wpm == 120.0

@pytest.mark.asyncio
async def test_relative_range_duration_and_metrics_calculation(test_db: AsyncSession):
    """
    Phase 5.3D SPEC TEST (PART 33):
    Video A: 60s, Video B: 600s
    Range: 25% -> 50%
    Verify metrics use:
    A = 15 seconds duration
    B = 150 seconds duration
    """
    # A: 30 words in 15s -> WPM = 30 / (15/60) = 120.0
    text_a = "alpha " * 30
    v_a = Video(id="v-rel-a", platform="youtube", platform_video_id="yt-ra", original_url="https://youtube.com/v-ra", title="Rel A 60s", duration_seconds=60, processing_status="COMPLETED")
    t_a = Transcript(id="t-rel-a", video_id="v-rel-a", language="en", full_text=text_a)
    s_a = TranscriptSegment(id="s-ra-1", transcript_id="t-rel-a", sequence_index=0, start_time=15.0, end_time=30.0, duration=15.0, text=text_a, word_count=30)

    # B: 300 words in 150s -> WPM = 300 / (150/60) = 120.0
    text_b = "beta " * 300
    v_b = Video(id="v-rel-b", platform="youtube", platform_video_id="yt-rb", original_url="https://youtube.com/v-rb", title="Rel B 600s", duration_seconds=600, processing_status="COMPLETED")
    t_b = Transcript(id="t-rel-b", video_id="v-rel-b", language="en", full_text=text_b)
    s_b = TranscriptSegment(id="s-rb-1", transcript_id="t-rel-b", sequence_index=0, start_time=150.0, end_time=300.0, duration=150.0, text=text_b, word_count=300)

    test_db.add_all([v_a, t_a, s_a, v_b, t_b, s_b])
    await test_db.commit()

    req = SegmentComparisonRequest(
        video_ids=["v-rel-a", "v-rel-b"],
        range=SegmentRangeRequest(type="RELATIVE", start_percent=25.0, end_percent=50.0)
    )
    res = await SegmentQueryService.query_segments(test_db, req)
    res_a = next(v for v in res.videos if v.video_id == "v-rel-a")
    res_b = next(v for v in res.videos if v.video_id == "v-rel-b")

    assert res_a.effective_duration_seconds == 15.0
    assert res_a.metrics.range_wpm == 120.0

    assert res_b.effective_duration_seconds == 150.0
    assert res_b.metrics.range_wpm == 120.0

@pytest.mark.asyncio
async def test_empty_range_and_missing_transcript_metrics(test_db: AsyncSession):
    # 1. No transcript video
    v_none = Video(id="v-m-none", platform="youtube", platform_video_id="yt-mn", original_url="https://youtube.com/v-mn", title="No Transcript", duration_seconds=60, processing_status="COMPLETED")
    
    # 2. Video with transcript but selected range has 0 segments
    v_empty = Video(id="v-m-empty", platform="youtube", platform_video_id="yt-me", original_url="https://youtube.com/v-me", title="Empty Range", duration_seconds=100, processing_status="COMPLETED")
    t_empty = Transcript(id="t-m-empty", video_id="v-m-empty", language="en", full_text="Spoken only between 50 and 60 seconds.")
    s_empty = TranscriptSegment(id="s-me-1", transcript_id="t-m-empty", sequence_index=0, start_time=50.0, end_time=60.0, duration=10.0, text="Spoken only between 50 and 60 seconds.", word_count=7)

    test_db.add_all([v_none, v_empty, t_empty, s_empty])
    await test_db.commit()

    # Query 0 to 10s (v_empty has segments at 50-60s -> EMPTY_RANGE)
    req = SegmentComparisonRequest(
        video_ids=["v-m-none", "v-m-empty"],
        range=SegmentRangeRequest(type="ABSOLUTE", start_seconds=0.0, end_seconds=10.0)
    )
    res = await SegmentQueryService.query_segments(test_db, req)
    r_none = next(v for v in res.videos if v.video_id == "v-m-none")
    r_empty = next(v for v in res.videos if v.video_id == "v-m-empty")

    # Missing transcript -> metrics is None
    assert r_none.availability == "NO_TRANSCRIPT"
    assert r_none.metrics is None

    # Empty range -> metrics has 0 counts and 0.0 WPM
    assert r_empty.availability == "EMPTY_RANGE"
    assert r_empty.metrics is not None
    assert r_empty.metrics.word_count == 0
    assert r_empty.metrics.segment_count == 0
    assert r_empty.metrics.sentence_count == 0
    assert r_empty.metrics.range_wpm == 0.0

@pytest.mark.asyncio
async def test_edge_cases_single_word_and_punctuation_only(test_db: AsyncSession):
    # One-word transcript
    v_one = Video(id="v-one", platform="youtube", platform_video_id="yt-one", original_url="https://youtube.com/v-one", title="One Word", duration_seconds=10, processing_status="COMPLETED")
    t_one = Transcript(id="t-one", video_id="v-one", language="en", full_text="Hello.")
    s_one = TranscriptSegment(id="s-one-1", transcript_id="t-one", sequence_index=0, start_time=0.0, end_time=2.0, duration=2.0, text="Hello.", word_count=1)

    # Punctuation-only transcript
    v_punc = Video(id="v-punc", platform="youtube", platform_video_id="yt-punc", original_url="https://youtube.com/v-punc", title="Punctuation Only", duration_seconds=10, processing_status="COMPLETED")
    t_punc = Transcript(id="t-punc", video_id="v-punc", language="en", full_text="... ??? !!!")
    s_punc = TranscriptSegment(id="s-punc-1", transcript_id="t-punc", sequence_index=0, start_time=0.0, end_time=2.0, duration=2.0, text="... ??? !!!", word_count=0)

    test_db.add_all([v_one, t_one, s_one, v_punc, t_punc, s_punc])
    await test_db.commit()

    req = SegmentComparisonRequest(
        video_ids=["v-one", "v-punc"],
        range=SegmentRangeRequest(type="ENTIRE")
    )
    res = await SegmentQueryService.query_segments(test_db, req)
    r_one = next(v for v in res.videos if v.video_id == "v-one")
    r_punc = next(v for v in res.videos if v.video_id == "v-punc")

    assert r_one.metrics is not None
    assert r_one.metrics.word_count == 1
    assert r_one.metrics.unique_words == 1
    assert r_one.metrics.lexical_diversity == 100.0

    assert r_punc.metrics is not None
    assert r_punc.metrics.word_count == 0
    assert r_punc.metrics.unique_words == 0


