"""Payment API endpoints.

Provides RESTful API for payment operations including:
- Creating payments.
- Querying payments with filtering and pagination.
- Basic CRUD operations.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.schemas.common import PaginatedResponse
from app.schemas.payment import (
    InitPaymentRequest,
    PaymentFilter,
    PaymentResponse,
    PaymentStatusResponse,
)
from app.services.payment_service import PaymentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["payments"])


def get_payment_service(
    db: AsyncSession = Depends(get_db), current_user: str | None = Depends(get_current_user)
) -> PaymentService:
    """Get payment service instance."""
    return PaymentService(db, user_id=current_user)


@router.get("", response_model=PaginatedResponse[PaymentResponse])
async def list_payments(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    search: str | None = Query(None, description="Search in request_id, txn_id"),
    sort_by: str | None = Query("created_at", description="Field to sort by"),
    sort_order: str | None = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    # Filter parameters
    status: str | None = Query(None, description="Filter by payment status"),
    store_id: int | None = Query(None, description="Filter by store ID"),
    terminal_id: int | None = Query(None, description="Filter by terminal ID"),
    service: PaymentService = Depends(get_payment_service),
):
    """List payments with filtering, search, and pagination.

    Supports searching by request_id, txn_id.
    Allows filtering by status, store, terminal.
    """
    filters = PaymentFilter(
        page=page,
        limit=limit,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        status=status,
        store_id=store_id,
        terminal_id=terminal_id,
    )

    return await service.list(filters=filters)


@router.get("/id/{payment_id}", response_model=PaymentResponse)
async def get_payment(payment_id: int, service: PaymentService = Depends(get_payment_service)):
    """Get payment by ID."""
    try:
        return await service.get(payment_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{request_id}", response_model=PaymentStatusResponse)
async def get_payment_by_request_id(
    request_id: str, service: PaymentService = Depends(get_payment_service)
):
    """Get payment by request_id."""
    try:
        payment = await service.get_payment_status(request_id)
        return payment
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/init", response_model=PaymentStatusResponse, status_code=status.HTTP_201_CREATED)
async def init_payment(
    data: InitPaymentRequest, service: PaymentService = Depends(get_payment_service)
):
    """Initialize a new payment with PayPay QR code generation.

    Creates payment record and generates QR code through PayPay API.
    Returns QR code data and payment status.

    Raises:
        409: Payment with same request_id already exists
        400: Invalid request data

    """
    try:
        return await service.init_payment(data)
    except HTTPException:
        # Re-raise HTTPException as-is (400, 404, 409, etc from service layer)
        raise
    except Exception as e:
        # Catch all unexpected errors as 500
        logger.error(f"Unexpected error in init_payment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred"
        )


@router.get("/{request_id}", response_model=PaymentStatusResponse)
async def get_payment_status(
    request_id: str, service: PaymentService = Depends(get_payment_service)
):
    """Get payment status by request_id.

    Returns current payment status and details.
    """
    try:
        return await service.get_payment_status(request_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
