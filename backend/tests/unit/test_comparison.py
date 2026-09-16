import pytest
import pytest_asyncio
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from backend.app.db.base import Base
from backend.app.db.models.entities import (
    Video, Creator, VideoMetadata, Transcript, TranscriptSegment, ScriptMetrics, VisualMetrics, Comparison
)
from backend.app.services.comparison_service import ComparisonService, extract_tokens, extract_ngrams
from backend.app.schemas.comparison import ComparisonCreate

@pytest_asyncio.fixture
async def test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    
    await engine.dispose()

def test_extract_tokens_and_ngrams():
    text = "Machine learning and artificial intelligence are transforming modern research tools."
    tokens = extract_tokens(text)
    assert len(tokens) == 10
    assert tokens[0] == "machine"

    bigrams = extract_ngrams(tokens, 2)
    assert len(bigrams) > 0
    trigrams = extract_ngrams(tokens, 3)
    assert len(trigrams) > 0

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
    assert sc_row.values["v-comp-2"].display_value == "Not Analyzed"

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
async def test_saved_comparisons_crud(test_db: AsyncSession):
    v1 = Video(id="v-save-1", platform="youtube", platform_video_id="yt-s1", original_url="https://youtube.com/watch?v=s1", title="Title 1", duration_seconds=100)
    v2 = Video(id="v-save-2", platform="youtube", platform_video_id="yt-s2", original_url="https://youtube.com/watch?v=s2", title="Title 2", duration_seconds=200)
    test_db.add_all([v1, v2])
    await test_db.commit()

    # Create saved comparison
    created = await ComparisonService.create_comparison(
        test_db,
        ComparisonCreate(title="Benchmark Python Videos", video_ids=["v-save-1", "v-save-2"])
    )
    assert created.title == "Benchmark Python Videos"
    assert len(created.videos) == 2

    # List
    listed = await ComparisonService.list_comparisons(test_db)
    assert any(c.id == created.id for c in listed)

    # Get by ID
    fetched = await ComparisonService.get_comparison_by_id(test_db, created.id)
    assert fetched.id == created.id

    # Delete
    await ComparisonService.delete_comparison(test_db, created.id)
    with pytest.raises(HTTPException) as exc:
        await ComparisonService.get_comparison_by_id(test_db, created.id)
    assert exc.value.status_code == 404
