"""Custom exceptions and error handling."""

from typing import Any


class AppError(Exception):
    """Base application error."""
    
    def __init__(
        self,
        message: str,
        code: str,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(AppError):
    """Validation error (400)."""
    
    def __init__(self, message: str, field: str | None = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=400,
            details={"field": field} if field else {},
        )


class NotFoundError(AppError):
    """Resource not found (404)."""
    
    def __init__(self, resource: str, identifier: str | int):
        super().__init__(
            message=f"{resource} not found: {identifier}",
            code="NOT_FOUND",
            status_code=404,
            details={"resource": resource, "identifier": str(identifier)},
        )


class ConflictError(AppError):
    """Resource conflict (409)."""
    
    def __init__(self, message: str, resource: str | None = None):
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=409,
            details={"resource": resource} if resource else {},
        )


class InvalidStateError(AppError):
    """Invalid state transition (422)."""
    
    def __init__(self, message: str, current_state: str | None = None):
        super().__init__(
            message=message,
            code="INVALID_STATE",
            status_code=422,
            details={"current_state": current_state} if current_state else {},
        )


class ExternalServiceError(AppError):
    """External service error (502/503)."""
    
    def __init__(
        self,
        message: str,
        service: str,
        status_code: int = 502,
        retryable: bool = False,
    ):
        super().__init__(
            message=message,
            code="EXTERNAL_SERVICE_ERROR",
            status_code=status_code,
            details={"service": service, "retryable": retryable},
        )


class LLMError(ExternalServiceError):
    """LLM service error."""
    
    def __init__(self, message: str, provider: str, retryable: bool = True):
        super().__init__(
            message=message,
            service=f"llm_{provider}",
            status_code=503,
            retryable=retryable,
        )


class LinkedInError(ExternalServiceError):
    """LinkedIn service error."""
    
    def __init__(self, message: str, operation: str, retryable: bool = True):
        super().__init__(
            message=message,
            service=f"linkedin_{operation}",
            status_code=502,
            retryable=retryable,
        )
