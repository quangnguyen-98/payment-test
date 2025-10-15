# app/core/error_handlers.py
"""Global error handlers for FastAPI application.
Handles all types of exceptions and returns consistent JSON responses.
"""

import logging
import traceback

from fastapi import Request, status
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import DataError, IntegrityError, SQLAlchemyError

from app.core.config import settings

logger = logging.getLogger(__name__)


def clean_traceback(traceback_str: str) -> str:
    """Clean up traceback by removing anyio/starlette internal exceptions.
    These are not relevant to the actual error and make the traceback hard to read.
    """
    lines = traceback_str.split("\n")
    cleaned_lines = []
    skip_section = False
    in_actual_error = False

    for _i, line in enumerate(lines):
        # Detect when we're in the actual error section (our code)
        if "/app/" in line or "/main.py" in line:
            in_actual_error = True

        # Skip entire sections related to internal exceptions
        if any(
            pattern in line
            for pattern in [
                "anyio.WouldBlock",
                "anyio.EndOfStream",
                "raise WouldBlock",
                "raise EndOfStream",
                "During handling of the above exception",
            ]
        ):
            skip_section = True
            continue

        # Stop skipping when we hit the real traceback
        if skip_section and "Traceback (most recent call last):" in line and in_actual_error:
            skip_section = False
            cleaned_lines.append(line)
            continue

        # Skip internal middleware noise
        if any(
            skip_pattern in line
            for skip_pattern in [
                "anyio/streams/memory.py",
                "receive_nowait()",
                "recv_stream.receive()",
                "receive_or_disconnect",
                "send_no_error",
                "raise app_exc",
                "sender)",
                "raise e",
                "raise exc",
                "^^^^^^^^^^^^^^^^^^^^^",
                "^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
                "^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
                "^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            ]
        ):
            continue

        # Skip if in skip section
        if skip_section:
            continue

        # Keep important lines
        cleaned_lines.append(line)

    # Remove multiple consecutive empty lines
    result = []
    prev_empty = False
    for line in cleaned_lines:
        if line.strip() == "":
            if not prev_empty:
                result.append(line)
                prev_empty = True
        else:
            result.append(line)
            prev_empty = False

    # Join and clean up
    final_result = "\n".join(result).strip()

    # If traceback is too minimal, return a simple version
    if len(final_result.split("\n")) < 5:
        # Extract just the essential error info
        for line in reversed(lines):
            if 'File "' in line and ("/app/" in line or "main.py" in line):
                error_lines = []
                idx = lines.index(line)
                # Get the file location and the actual error
                for j in range(idx, min(idx + 4, len(lines))):
                    if lines[j].strip():
                        error_lines.append(lines[j])
                if error_lines:
                    return "Traceback (most recent call last):\n" + "\n".join(error_lines)
        return traceback_str  # Return original if we can't clean it

    return final_result


def create_error_response(
    request: Request,
    status_code: int,
    error_code: str,
    message: str,
    details: dict | list | None = None,
    traceback_str: str = None,
) -> JSONResponse:
    """Create a consistent error response format.

    Args:
        request: The request object
        status_code: HTTP status code
        error_code: Application-specific error code
        message: Human-readable error message
        details: Additional error details
        traceback_str: Traceback string (only included in development)

    Returns:
        JSONResponse with error details

    """
    error_response = {
        "error": {
            "code": error_code,
            "message": message,
            "path": str(request.url.path),
            "method": request.method,
        }
    }

    # Add request ID if available
    if hasattr(request.state, "request_id"):
        error_response["error"]["request_id"] = request.state.request_id

    # Add details if provided
    if details is not None:
        error_response["error"]["details"] = details

    # Add traceback in local environment only
    if settings.ENVIRONMENT == "local" and traceback_str:
        # Clean up traceback - remove anyio/starlette internal exceptions
        cleaned_traceback = clean_traceback(traceback_str)
        error_response["error"]["traceback"] = cleaned_traceback.split("\n")

    return JSONResponse(status_code=status_code, content=error_response)


# async def handle_base_api_exception(request: Request, exc: BaseAPIException) -> JSONResponse:
#     """Handle custom API exceptions."""
#     request_id = getattr(request.state, "request_id", "unknown")
#     logger.warning(
#         f"API Exception: {exc.error_code} - {exc.detail} "
#         f"[Path: {request.url.path}] [Method: {request.method}] [ID: {request_id}]"
#     )
#
#     return create_error_response(
#         request=request,
#         status_code=exc.status_code,
#         error_code=exc.error_code,
#         message=exc.detail,
#         details=exc.extra if hasattr(exc, "extra") else None,
#     )


async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle standard HTTPException."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning(
        f"HTTP Exception: {exc.status_code} - {exc.detail} "
        f"[Path: {request.url.path}] [Method: {request.method}] [ID: {request_id}]"
    )

    return create_error_response(
        request=request,
        status_code=exc.status_code,
        error_code=f"HTTP_{exc.status_code}",
        message=exc.detail,
    )


async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors from request data."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning(
        f"Validation Error: {request.url.path} - {request.method} - {exc.errors()} [ID: {request_id}]"
    )

    # Format validation errors
    errors = []
    for error in exc.errors():
        error_detail = {
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        errors.append(error_detail)

    return create_error_response(
        request=request,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code="VALIDATION_ERROR",
        message="Request validation failed",
        details=errors,
    )


async def handle_pydantic_validation_error(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle Pydantic validation errors from internal validation."""
    logger.warning(f"Pydantic Validation Error: {request.url.path} - {exc.errors()}")

    errors = []
    for error in exc.errors():
        error_detail = {
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        errors.append(error_detail)

    return create_error_response(
        request=request,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code="VALIDATION_ERROR",
        message="Data validation failed",
        details=errors,
    )


async def handle_database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle SQLAlchemy database errors - only generic patterns."""
    error_message = "Database operation failed"
    error_code = "DATABASE_ERROR"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    details = None

    # Handle specific database errors
    if isinstance(exc, IntegrityError):
        status_code = status.HTTP_409_CONFLICT
        error_code = "INTEGRITY_ERROR"

        # Generic parsing - không if/else cụ thể cho từng field
        error_str = str(exc.orig).lower() if exc.orig else str(exc).lower()

        if "duplicate" in error_str or "unique" in error_str:
            error_message = "Duplicate value for unique constraint"
        elif "foreign key" in error_str:
            error_message = "Foreign key constraint violation"
        elif "not null" in error_str or "cannot be null" in error_str:
            error_message = "Required field cannot be null"
        elif "check constraint" in error_str:
            error_message = "Check constraint violation"
        else:
            error_message = "Database integrity constraint violated"

    elif isinstance(exc, DataError):
        error_message = "Invalid data format"
        error_code = "DATA_ERROR"
        status_code = status.HTTP_400_BAD_REQUEST

    # Log the error
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning(
        f"Database Error: {error_code} - {error_message} "
        f"[Path: {request.url.path}] [Method: {request.method}] [ID: {request_id}]"
    )

    # Include details only in local environment
    if settings.ENVIRONMENT == "local":
        details = {"db_error": str(exc), "type": type(exc).__name__}

    return create_error_response(
        request=request,
        status_code=status_code,
        error_code=error_code,
        message=error_message,
        details=details,
        traceback_str=traceback.format_exc() if settings.ENVIRONMENT == "local" else None,
    )


async def handle_generic_exception(request: Request, exc: Exception) -> JSONResponse:
    """Handle any unhandled exceptions."""
    # Log the full error with traceback
    # Check if we have request_id to avoid duplicate logging
    getattr(request.state, "request_id", "unknown")
    # logger.error(
    #     f"Unhandled Exception: {type(exc).__name__} - {str(exc)} "
    #     f"[Path: {request.url.path}] [Method: {request.method}] [ID: {request_id}]",
    #     exc_info=True
    # )

    # Determine response based on environment
    if settings.ENVIRONMENT == "local":
        # In development, provide detailed error information
        return create_error_response(
            request=request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="INTERNAL_SERVER_ERROR",
            message=f"An unexpected error occurred: {str(exc)}",
            details={
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
            },
            traceback_str=traceback.format_exc(),
        )
    else:
        # In production, hide internal details
        return create_error_response(
            request=request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred. Please try again later.",
        )


def register_error_handlers(app):
    """Register essential error handlers with the FastAPI app.
    Keep it simple - only handle what FastAPI doesn't handle well by default.

    Args:
        app: FastAPI application instance

    """
    # 1. Validation errors (FastAPI's default is good but we want custom format)
    app.add_exception_handler(RequestValidationError, handle_validation_error)

    # 2. Database errors (need special handling for integrity constraints)
    app.add_exception_handler(SQLAlchemyError, handle_database_error)

    # 3. HTTPException is already handled well by FastAPI
    # We only add this if we want custom response format
    # app.add_exception_handler(HTTPException, handle_http_exception)

    # 4. Catch-all for unexpected errors (with clean traceback in dev)
    app.add_exception_handler(Exception, handle_generic_exception)

    logger.info("Error handlers registered successfully")
