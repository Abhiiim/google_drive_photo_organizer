"""Custom exception classes for the application."""

from datetime import datetime
from typing import Any, Dict, Optional


class AppException(Exception):
    """Base exception class for application errors."""

    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        path: Optional[str] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.path = path
        self.timestamp = datetime.utcnow()

        super().__init__(self.message)


class ValidationError(AppException):
    """Exception raised for input validation errors."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        path: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=422,
            details=details,
            path=path,
        )


class ResourceNotFoundError(AppException):
    """Exception raised when a requested resource is not found."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        path: Optional[str] = None,
    ):
        message = f"{resource_type} with id '{resource_id}' not found"
        super().__init__(
            message=message,
            error_code="RESOURCE_NOT_FOUND",
            status_code=404,
            details={"resource_type": resource_type, "resource_id": resource_id},
            path=path,
        )


class JobNotFoundError(ResourceNotFoundError):
    """Exception raised when a job is not found."""

    def __init__(self, job_id: str, path: Optional[str] = None):
        super().__init__(
            resource_type="Job",
            resource_id=job_id,
            path=path,
        )


class ProcessingError(AppException):
    """Exception raised during photo processing operations."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        path: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            error_code="PROCESSING_ERROR",
            status_code=500,
            details=details,
            path=path,
        )


class GoogleDriveError(AppException):
    """Exception raised for Google Drive API errors."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        path: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            error_code="GOOGLE_DRIVE_ERROR",
            status_code=502,
            details=details,
            path=path,
        )


class AuthenticationError(AppException):
    """Exception raised for authentication failures."""

    def __init__(
        self,
        message: str = "Authentication required",
        details: Optional[Dict[str, Any]] = None,
        path: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=401,
            details=details,
            path=path,
        )


class AuthorizationError(AppException):
    """Exception raised for authorization failures."""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        details: Optional[Dict[str, Any]] = None,
        path: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=403,
            details=details,
            path=path,
        )


class RateLimitError(AppException):
    """Exception raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        path: Optional[str] = None,
    ):
        details = {}
        if retry_after:
            details["retry_after"] = retry_after

        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details=details,
            path=path,
        )


class ConfigurationError(AppException):
    """Exception raised for configuration-related errors."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        path: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            status_code=500,
            details=details,
            path=path,
        )
