import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from backend.app.db.base import Base
from backend.app.db.models.entities import Creator, Video, VideoMetadata, ExtractionJob

@pytest_asyncio.fixture
async def test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    
    await engine.dispose()

@pytest.mark.asyncio
async def test_create_creator_and_video(test_db: AsyncSession):
    creator = Creator(platform="youtube", platform_creator_id="UC123", name="Tech Explainer", handle="@techexplain")
    test_db.add(creator)
    await test_db.flush()

    video = Video(
        platform="youtube",
        platform_video_id="abc12345",
        original_url="https://www.youtube.com/watch?v=abc12345",
        title="Understanding Deterministic Systems",
        duration_seconds=360,
        creator_id=creator.id,
        processing_status="COMPLETED",
        media_state="NOT_DOWNLOADED"
    )
    test_db.add(video)
    await test_db.commit()

    result = await test_db.execute(select(Video).where(Video.platform_video_id == "abc12345"))
    saved_video = result.scalar_one()
    assert saved_video.title == "Understanding Deterministic Systems"
    assert saved_video.creator_id == creator.id
