"""Common schemas and base models."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Error detail structure."""
    
    code: str
    message: str
    trace_id: str | None = None
    field: str | None = None


class ErrorResponse(BaseModel):
    """Standard error response."""
    
    error: ErrorDetail


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success response with data."""
    
    status: str = "success"
    data: T
    trace_id: str | None = None


class PaginationParams(BaseModel):
    """Pagination query parameters."""
    
    limit: int = Field(default=20, ge=1, le=100)
    before: str | None = None  # Cursor for pagination
