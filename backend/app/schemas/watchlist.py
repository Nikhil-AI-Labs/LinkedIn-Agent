"""Watchlist endpoint schemas."""

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator


class AddWatchlistRequest(BaseModel):
    """Request to add a profile to watchlist."""
    
    profile_url: HttpUrl | None = None
    member_id: str | None = Field(None, min_length=1, max_length=100)
    note: str | None = Field(None, max_length=500)
    
    @model_validator(mode="after")
    def validate_one_source(self):
        """Ensure either profile_url or member_id is provided."""
        if not self.profile_url and not self.member_id:
            raise ValueError("Either profile_url or member_id is required")
        if self.profile_url and self.member_id:
            raise ValueError("Provide only one: profile_url or member_id")
        return self


class WatchlistProfile(BaseModel):
    """Watchlist profile entry."""
    
    id: int
    linkedin_profile_id: str
    profile_url: str | None = None
    name: str | None = None
    headline: str | None = None
    note: str | None = None
    status: Literal["active", "error", "not_found"]
    added_at: str
    last_checked: str | None = None


class AddWatchlistResponse(BaseModel):
    """Response from adding to watchlist."""
    
    status: Literal["added", "duplicate", "error"]
    trace_id: str
    profile: WatchlistProfile | None = None
    message: str | None = None


class RemoveWatchlistResponse(BaseModel):
    """Response from removing from watchlist."""
    
    status: Literal["removed", "not_found", "error"]
    trace_id: str
    profile_id: str


class ListWatchlistResponse(BaseModel):
    """Response from listing watchlist."""
    
    status: str = "success"
    trace_id: str
    profiles: list[WatchlistProfile]
    total_count: int
