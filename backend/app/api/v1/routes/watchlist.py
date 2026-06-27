"""Watchlist management endpoints."""

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.watchlist import (
    AddWatchlistRequest,
)
from app.schemas.responses import (
    AddWatchlistResponse,
    RemoveWatchlistResponse,
    ListWatchlistResponse,
)
from app.services.watchlist_service import WatchlistService
from app.core.dependencies import get_db_session, get_current_user_id, get_trace_id
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/monitor", tags=["watchlist"])


@router.post("/add", response_model=AddWatchlistResponse)
async def add_to_watchlist(
    request: AddWatchlistRequest,
    db: AsyncSession = Depends(get_db_session),
    user_id: int = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
) -> AddWatchlistResponse:
    """Add a LinkedIn profile to the user's watchlist.
    
    Accepts either:
    - profile_url: Full LinkedIn profile URL
    - member_id: LinkedIn member ID
    
    Returns error if profile already in watchlist.
    """
    logger.info(
        "add_watchlist_request",
        user_id=user_id,
        has_url=request.profile_url is not None,
        has_member_id=request.member_id is not None,
        trace_id=trace_id,
    )
    
    watchlist_service = WatchlistService(db=db)
    
    response_data = await watchlist_service.add_profile(
        user_id=user_id,
        profile_url=request.profile_url,
        member_id=request.member_id,
        note=request.note,
        trace_id=trace_id,
    )
    
    return AddWatchlistResponse(**response_data)


@router.delete("/remove/{profile_id}", response_model=RemoveWatchlistResponse)
async def remove_from_watchlist(
    profile_id: str = Path(..., min_length=1, max_length=100),
    db: AsyncSession = Depends(get_db_session),
    user_id: int = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
) -> RemoveWatchlistResponse:
    """Remove a profile from the user's watchlist.
    
    Returns 404 if profile not found in watchlist.
    """
    logger.info(
        "remove_watchlist_request",
        user_id=user_id,
        profile_id=profile_id,
        trace_id=trace_id,
    )
    
    watchlist_service = WatchlistService(db=db)
    
    response_data = await watchlist_service.remove_profile(
        user_id=user_id,
        profile_id=profile_id,
        trace_id=trace_id,
    )
    
    return RemoveWatchlistResponse(**response_data)


@router.get("/list", response_model=ListWatchlistResponse)
async def list_watchlist(
    db: AsyncSession = Depends(get_db_session),
    user_id: int = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
) -> ListWatchlistResponse:
    """List all profiles in the user's watchlist."""
    logger.info("list_watchlist_request", user_id=user_id, trace_id=trace_id)
    
    watchlist_service = WatchlistService(db=db)
    
    response_data = await watchlist_service.list_profiles(
        user_id=user_id,
        trace_id=trace_id,
    )
    
    return ListWatchlistResponse(**response_data)
