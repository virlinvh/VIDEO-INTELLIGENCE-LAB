from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db_session
from backend.app.schemas.comparison import (
    ComparisonCreate,
    ComparisonRead,
    ComparisonAnalyzeRequest,
    MultiVideoComparisonResult,
    CreatorAggregateMetrics,
)
from backend.app.services.comparison_service import ComparisonService

router = APIRouter()

@router.post("/analyze", response_model=MultiVideoComparisonResult)
async def analyze_videos(
    data: ComparisonAnalyzeRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Deterministically compare 2 to 10 videos by calculating multi-video overview matrices,
    normalized 0-100% timeline deciles, vocabulary overlap, signature words, n-grams,
    and opening/closing hook pacing.
    """
    return await ComparisonService.compare_videos(db, data.video_ids)

@router.post("", response_model=ComparisonRead, status_code=status.HTTP_201_CREATED)
async def create_saved_comparison(
    data: ComparisonCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Save a comparison group for later quick access.
    """
    return await ComparisonService.create_comparison(db, data)

@router.get("", response_model=List[ComparisonRead])
async def list_saved_comparisons(
    db: AsyncSession = Depends(get_db_session)
):
    """
    List all saved video comparison groups.
    """
    return await ComparisonService.list_comparisons(db)

@router.get("/{comparison_id}", response_model=ComparisonRead)
async def get_saved_comparison(
    comparison_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get a saved video comparison group by ID.
    """
    return await ComparisonService.get_comparison_by_id(db, comparison_id)

@router.delete("/{comparison_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_comparison(
    comparison_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Delete a saved video comparison group.
    """
    await ComparisonService.delete_comparison(db, comparison_id)
    return None

@router.get("/creator/{creator_id}", response_model=CreatorAggregateMetrics)
async def get_creator_aggregate_metrics(
    creator_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get creator-level aggregate metrics across all videos by this creator in the local Library.
    """
    return await ComparisonService.get_creator_metrics(db, creator_id)
