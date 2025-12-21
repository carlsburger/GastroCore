"""
Custom exceptions for consistent error handling
"""
from fastapi import HTTPException, status


class GastroCoreException(HTTPException):
    """Base exception for GastroCore"""
    def __init__(self, status_code: int, detail: str, error_code: str = None):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code


class UnauthorizedException(GastroCoreException):
    """401 - Authentication required or failed"""
    def __init__(self, detail: str = "Nicht autorisiert"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code="UNAUTHORIZED"
        )


class ForbiddenException(GastroCoreException):
    """403 - Authenticated but not allowed"""
    def __init__(self, detail: str = "Keine Berechtigung"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="FORBIDDEN"
        )


class NotFoundException(GastroCoreException):
    """404 - Resource not found"""
    def __init__(self, resource: str = "Ressource"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} nicht gefunden",
            error_code="NOT_FOUND"
        )


class ValidationException(GastroCoreException):
    """400 - Validation error"""
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code="VALIDATION_ERROR"
        )


class ConflictException(GastroCoreException):
    """409 - Resource conflict"""
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code="CONFLICT"
        )


class InvalidStatusTransitionException(ValidationException):
    """Invalid status transition"""
    def __init__(self, current: str, target: str):
        super().__init__(
            detail=f"Ungültiger Statusübergang: {current} → {target}"
        )
