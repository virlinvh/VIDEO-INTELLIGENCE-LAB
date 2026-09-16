import pytest
import pytest_asyncio
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from backend.app.db.base import Base
from backend.app.db.models.entities import (
    Video, Creator, VideoMetadata, Transcript, TranscriptSegment, ScriptMetrics, VisualMetrics, Frame, Comparison
)
from backend.app.services.comparison_service import ComparisonService, extract_tokens, extract_ngrams
from backend.app.schemas.comparison import ComparisonCreate, ComparisonUpdate

@pytest_asyncio.fixture
async def test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    
    await engine.dispose()

def test_extract_tokens_and_ngrams_english():
    text = "Machine learning and artificial intelligence are transforming modern research tools."
    tokens = extract_tokens(text)
    assert len(tokens) == 10
    assert tokens[0] == "machine"

    bigrams = extract_ngrams(tokens, 2)
    assert len(bigrams) > 0
    trigrams = extract_ngrams(tokens, 3)
    assert len(trigrams) > 0

def test_extract_tokens_and_ngrams_tamil_and_malayalam():
    # Tamil Unicode tokens (5 words)
    tamil_text = "வணக்கம் உலகம்! செயற்கை நுண்ணறிவு தொழில்நுட்பம்."
    tamil_tokens = extract_tokens(tamil_text)
    assert len(tamil_tokens) == 5
    assert "வணக்கம்" in tamil_tokens
    assert "உலகம்" in tamil_tokens

    # Malayalam Unicode tokens (5 words)
    malayalam_text = "നമസ്കാരം ലോകം! കൃത്രിമ ബുദ്ധി സാങ്കേതികവിദ്യ."
    malayalam_tokens = extract_tokens(malayalam_text)
    assert len(malayalam_tokens) == 5
    assert "നമസ്കാരം" in malayalam_tokens

@pytest.mark.asyncio
async def test_compare_videos_validation_bounds(test_db: AsyncSession):
    with pytest.raises(HTTPException) as exc1:
        await ComparisonService.compare_videos(test_db, ["vid-1"])
    assert exc1.value.status_code == 400

    with pytest.raises(HTTPException) as exc2:
        await ComparisonService.compare_videos(test_db, [f"vid-{i}" for i in range(11)])
    assert exc2.value.status_code == 400

@pytest.mark.asyncio
async def test_compare_videos_full_workflow(test_db: AsyncSession):
    # Setup Creator
    creator = Creator(
        id="c-test-comp",
        platform="youtube",
        name="Tech Educator",
        handle="@techeducator"
    )
    test_db.add(creator)
    await test_db.commit()

    # Video 1: Short video (60s)
    v1 = Video(
        id="v-comp-1",
        platform="youtube",
        platform_video_id="yt-c1",
        original_url="https://youtube.com/watch?v=c1",
        title="Intro to Python Functions",
        duration_seconds=60,
        creator_id="c-test-comp",
        processing_status="COMPLETED"
    )
    meta1 = VideoMetadata(
        video_id="v-comp-1",
        view_count=10000,
        like_count=500,
        comment_count=50
    )
    t1 = Transcript(
        id="t-comp-1",
        video_id="v-comp-1",
        language="en",
        full_text="Hello world! Today we explore Python functions. How do functions work? They return values!"
    )
    s1_1 = TranscriptSegment(id="seg-1-1", transcript_id="t-comp-1", sequence_index=0, start_time=0.0, end_time=15.0, duration=15.0, text="Hello world! Today we explore Python functions.", word_count=7)
    s1_2 = TranscriptSegment(id="seg-1-2", transcript_id="t-comp-1", sequence_index=1, start_time=15.0, end_time=45.0, duration=30.0, text="How do functions work? They return values!", word_count=7)
    sm1 = ScriptMetrics(
        id="sm-comp-1",
        video_id="v-comp-1",
        word_count=14,
        estimated_wpm=14.0,
        lexical_diversity_ttr=0.85,
        question_count=1,
        exclamation_count=2
    )
    vm1 = VisualMetrics(
        id="vm-comp-1",
        video_id="v-comp-1",
        scene_count=3,
        scene_change_frequency=3.0,
        avg_scene_duration=20.0,
        scene_timestamps=[0.0, 20.0, 40.0],
        technical_properties={"resolution": "1920x1080", "fps": 30.0}
    )

    test_db.add_all([v1, meta1, t1, s1_1, s1_2, sm1, vm1])

    # Video 2: Medium video (120s) without visual metrics (tests missing data handling)
    v2 = Video(
        id="v-comp-2",
        platform="youtube",
        platform_video_id="yt-c2",
        original_url="https://youtube.com/watch?v=c2",
        title="Advanced Python Generators",
        duration_seconds=120,
        creator_id="c-test-comp",
        processing_status="COMPLETED"
    )
    meta2 = VideoMetadata(
        video_id="v-comp-2",
        view_count=20000,
        like_count=1200,
        comment_count=100
    )
    t2 = Transcript(
        id="t-comp-2",
        video_id="v-comp-2",
        language="en",
        full_text="Welcome back! Today we analyze Python generators and functions. Why use generators? Because they yield values efficiently."
    )
    s2_1 = TranscriptSegment(id="seg-2-1", transcript_id="t-comp-2", sequence_index=0, start_time=0.0, end_time=30.0, duration=30.0, text="Welcome back! Today we analyze Python generators and functions.", word_count=9)
    s2_2 = TranscriptSegment(id="seg-2-2", transcript_id="t-comp-2", sequence_index=1, start_time=30.0, end_time=120.0, duration=90.0, text="Why use generators? Because they yield values efficiently.", word_count=8)
    sm2 = ScriptMetrics(
        id="sm-comp-2",
        video_id="v-comp-2",
        word_count=17,
        estimated_wpm=8.5,
        lexical_diversity_ttr=0.88,
        question_count=1,
        exclamation_count=1
    )

    test_db.add_all([v2, meta2, t2, s2_1, s2_2, sm2])
    await test_db.commit()

    # Compare v1 and v2
    result = await ComparisonService.compare_videos(test_db, ["v-comp-1", "v-comp-2"])

    assert len(result.videos) == 2
    assert result.videos[0].id == "v-comp-1"
    assert result.videos[1].id == "v-comp-2"
    assert result.has_mixed_languages is False
    assert result.detected_languages == ["en"]

    # Verify Matrix Rows
    matrix_keys = [r.key for r in result.matrix]
    assert "duration" in matrix_keys
    assert "word_count" in matrix_keys
    assert "wpm" in matrix_keys
    assert "scene_changes" in matrix_keys

    # Check that missing visual metrics in v2 is gracefully handled
    sc_row = next(r for r in result.matrix if r.key == "scene_changes")
    assert sc_row.values["v-comp-1"].status == "AVAILABLE"
    assert sc_row.values["v-comp-2"].status == "NOT_ANALYZED"
    assert sc_row.values["v-comp-2"].display_value == "Not analyzed"

    # Verify Timeline Deciles
    assert len(result.timeline_deciles) == 10
    assert result.timeline_deciles[0].decile_label == "0-10%"
    assert result.timeline_deciles[0].series["v-comp-1"]["has_transcript"] is True
    assert result.timeline_deciles[0].series["v-comp-1"]["has_visuals"] is True
    assert result.timeline_deciles[0].series["v-comp-2"]["has_visuals"] is False

    # Verify Shared Vocabulary ("python", "functions")
    shared_words = [item.word for item in result.shared_vocabulary]
    assert "python" in shared_words or "functions" in shared_words

    # Verify Openings and Closings
    assert len(result.openings_closings) == 2
    assert result.openings_closings[0].opening_text is not None

    # Verify Creator Aggregates
    assert len(result.creator_aggregates) == 1
    assert result.creator_aggregates[0].creator_name == "Tech Educator"
    assert result.creator_aggregates[0].sample_size_n == 2
    assert result.creator_aggregates[0].mean_duration_seconds == 90.0

@pytest.mark.asyncio
async def test_multilingual_mixed_language_and_division_safety(test_db: AsyncSession):
    # Video 1: Tamil video with 0 views to test division by zero safety
    v_ta = Video(
        id="v-ta-1",
        platform="youtube",
        platform_video_id="yt-ta1",
        original_url="https://youtube.com/watch?v=ta1",
        title="தமிழ் இலக்கணம்",
        duration_seconds=180,
        processing_status="COMPLETED"
    )
    meta_ta = VideoMetadata(
        video_id="v-ta-1",
        view_count=0, # 0 views -> ratio safely None
        like_count=0,
        comment_count=0
    )
    t_ta = Transcript(
        id="t-ta-1",
        video_id="v-ta-1",
        language="ta",
        full_text="வணக்கம் நேயர்களே! இன்றைய காணொளியில் நாம் தமிழ் இலக்கணம் பற்றி விரிவாகப் பார்க்கப் போகிறோம்."
    )
    test_db.add_all([v_ta, meta_ta, t_ta])

    # Video 2: English video
    v_en = Video(
        id="v-en-1",
        platform="youtube",
        platform_video_id="yt-en1",
        original_url="https://youtube.com/watch?v=en1",
        title="English Grammar",
        duration_seconds=200,
        processing_status="COMPLETED"
    )
    meta_en = VideoMetadata(
        video_id="v-en-1",
        view_count=5000,
        like_count=250,
        comment_count=25
    )
    t_en = Transcript(
        id="t-en-1",
        video_id="v-en-1",
        language="en",
        full_text="Hello viewers! In today's video we will explore English grammar in detail."
    )
    test_db.add_all([v_en, meta_en, t_en])
    await test_db.commit()

    result = await ComparisonService.compare_videos(test_db, ["v-ta-1", "v-en-1"])

    assert result.has_mixed_languages is True
    assert "ta" in result.detected_languages
    assert "en" in result.detected_languages

    # Check division by zero safety on v_ta
    v_ta_summary = next(v for v in result.videos if v.id == "v-ta-1")
    assert v_ta_summary.like_view_ratio is None
    assert v_ta_summary.comment_view_ratio is None

    # Check valid ratio on v_en (250/5000 = 5.0%)
    v_en_summary = next(v for v in result.videos if v.id == "v-en-1")
    assert v_en_summary.like_view_ratio == 5.0

@pytest.mark.asyncio
async def test_saved_comparisons_crud(test_db: AsyncSession):
    v1 = Video(id="v-save-1", platform="youtube", platform_video_id="yt-s1", original_url="https://youtube.com/watch?v=s1", title="Title 1", duration_seconds=100)
    v2 = Video(id="v-save-2", platform="youtube", platform_video_id="yt-s2", original_url="https://youtube.com/watch?v=s2", title="Title 2", duration_seconds=200)
    test_db.add_all([v1, v2])
    await test_db.commit()

    # Create saved comparison
    created = await ComparisonService.create_comparison(
        test_db,
        ComparisonCreate(title="Benchmark Python Videos", notes="Test notes", video_ids=["v-save-1", "v-save-2"])
    )
    assert created.title == "Benchmark Python Videos"
    assert created.notes == "Test notes"
    assert len(created.videos) == 2

    # List
    listed = await ComparisonService.list_comparisons(test_db)
    assert any(c.id == created.id for c in listed)

    # Get by ID
    fetched = await ComparisonService.get_comparison_by_id(test_db, created.id)
    assert fetched.id == created.id

    # Update (PATCH)
    updated = await ComparisonService.update_comparison(
        test_db,
        created.id,
        ComparisonUpdate(title="Updated Python Benchmark", notes="Updated notes")
    )
    assert updated.title == "Updated Python Benchmark"
    assert updated.notes == "Updated notes"

    # Delete
    await ComparisonService.delete_comparison(test_db, created.id)
    with pytest.raises(HTTPException) as exc:
        await ComparisonService.get_comparison_by_id(test_db, created.id)
    assert exc.value.status_code == 404

@pytest.mark.asyncio
async def test_keyframe_gallery_and_timeline_events_resilience(test_db: AsyncSession):
    # Video with visual metrics, scene changes, and extracted keyframes
    v1 = Video(
        id="v-kf-1",
        platform="youtube",
        platform_video_id="yt-kf1",
        original_url="https://youtube.com/watch?v=kf1",
        title="Visual Test Video 1",
        duration_seconds=120,
        processing_status="COMPLETED"
    )
    vm1 = VisualMetrics(
        id="vm-kf-1",
        video_id="v-kf-1",
        scene_count=4,
        scene_timestamps=[0.0, 30.0, 60.0, 90.0]
    )
    f1 = Frame(
        id="frame-kf-1",
        visual_metrics_id="vm-kf-1",
        video_id="v-kf-1",
        frame_number=0,
        timestamp=0.0,
        file_path="storage/frames/frame_0.jpg",
        width=1280,
        height=720
    )
    f2 = Frame(
        id="frame-kf-2",
        visual_metrics_id="vm-kf-1",
        video_id="v-kf-1",
        frame_number=1,
        timestamp=60.0,
        file_path="storage/frames/frame_60.jpg",
        width=1280,
        height=720
    )
    test_db.add_all([v1, vm1, f1, f2])

    # Video without visual metrics (tests fallback/empty states)
    v2 = Video(
        id="v-kf-2",
        platform="youtube",
        platform_video_id="yt-kf2",
        original_url="https://youtube.com/watch?v=kf2",
        title="Visual Test Video 2 (No Visuals)",
        duration_seconds=90,
        processing_status="COMPLETED"
    )
    test_db.add(v2)
    await test_db.commit()

    result = await ComparisonService.compare_videos(test_db, ["v-kf-1", "v-kf-2"])

    # Verify Keyframe Gallery
    assert "v-kf-1" in result.keyframe_gallery
    assert "v-kf-2" in result.keyframe_gallery
    assert len(result.keyframe_gallery["v-kf-1"]) == 5
    assert len(result.keyframe_gallery["v-kf-2"]) == 5

    # Check that image_url has proper route format
    available_frames = [kf for kf in result.keyframe_gallery["v-kf-1"] if kf.status == "AVAILABLE"]
    assert len(available_frames) > 0
    for af in available_frames:
        assert af.image_url.startswith("/api/v1/videos/frames/")
        assert af.image_url.endswith("/image")

    # Check that unanalyzed video frames have NOT_ANALYZED status and None image_url
    for kf in result.keyframe_gallery["v-kf-2"]:
        assert kf.status == "NOT_ANALYZED"
        assert kf.image_url is None

    # Verify Timeline Events & Deciles
    assert "v-kf-1" in result.timeline_events
    assert len(result.timeline_events["v-kf-1"]) == 4
    assert result.timeline_events["v-kf-1"][0].normalized_position_pct == 0.0
    assert result.timeline_events["v-kf-1"][1].normalized_position_pct == 25.0
    assert result.timeline_events["v-kf-1"][2].normalized_position_pct == 50.0
    assert result.timeline_events["v-kf-1"][3].normalized_position_pct == 75.0

    assert len(result.timeline_deciles) == 10
    for dec in result.timeline_deciles:
        assert "v-kf-1" in dec.series
        assert "v-kf-2" in dec.series
        assert isinstance(dec.series["v-kf-1"]["cuts_per_minute"], (int, float))
        assert isinstance(dec.series["v-kf-2"]["cuts_per_minute"], (int, float))

