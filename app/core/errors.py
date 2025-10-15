"""Simplified error handling utilities.

This module provides simple error responses without complex exception hierarchies.
Just call the function when you need to return an error.
"""

from typing import Any

from fastapi import HTTPException, status


class ErrorResponse:
    """Simple error response builder."""

    @staticmethod
    def bad_request(detail: str, headers: dict[str, Any] | None = None) -> HTTPException:
        """Return a 400 Bad Request error."""
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=detail, headers=headers
        )

    @staticmethod
    def unauthorized(
        detail: str = "Unauthorized", headers: dict[str, Any] | None = None
    ) -> HTTPException:
        """Return a 401 Unauthorized error."""
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers=headers or {"WWW-Authenticate": "Bearer"},
        )

    @staticmethod
    def forbidden(detail: str = "Forbidden") -> HTTPException:
        """Return a 403 Forbidden error."""
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

    @staticmethod
    def not_found(detail: str = "Resource not found") -> HTTPException:
        """Return a 404 Not Found error."""
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

    @staticmethod
    def conflict(detail: str = "Resource already exists") -> HTTPException:
        """Return a 409 Conflict error."""
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

    @staticmethod
    def validation_error(detail: str = "Validation failed") -> HTTPException:
        """Return a 422 Unprocessable Entity error."""
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

    @staticmethod
    def internal_error(detail: str = "Internal server error") -> HTTPException:
        """Return a 500 Internal Server Error."""
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)

    @staticmethod
    def upstream_error(detail: str = "Upstream service error") -> HTTPException:
        """Return a 502 Bad Gateway error."""
        return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)


# Shortcuts for common errors
def bad_request(detail: str) -> HTTPException:
    """Shortcut for bad request error."""
    return ErrorResponse.bad_request(detail)


def not_found(detail: str) -> HTTPException:
    """Shortcut for not found error."""
    return ErrorResponse.not_found(detail)


def conflict(detail: str) -> HTTPException:
    """Shortcut for conflict error."""
    return ErrorResponse.conflict(detail)


def upstream_error(detail: str) -> HTTPException:
    """Shortcut for upstream service error."""
    return ErrorResponse.upstream_error(detail)
