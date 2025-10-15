"""Payment Service - Business logic layer for payment operations.

This service handles:
- Payment processing and lifecycle management
- Business logic and validation
- Transaction management
"""

import logging
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import conflict, not_found
from app.models.merchant import Merchant
from app.models.payment import Payment as PaymentModel
from app.models.payment import PaymentStatus, PaymentTender
from app.models.store import Store
from app.models.terminal import Terminal
from app.repositories.payment_repository import PaymentRepository
from app.repositories.terminal_repository import TerminalRepository
from app.schemas.common import PaginatedResponse, PaginationMeta
from app.schemas.payment import (
    InitPaymentRequest,
    PaymentFilter,
    PaymentStatusResponse,
)
from app.schemas.payment import (
    PaymentResponse as PaymentSchema,
)

# PayPayPaymentStatus removed - using PaymentStatus directly
from app.services.paypay_service import PayPayService

logger = logging.getLogger(__name__)


class PaymentService:
    """Service class for Payment entity.

    Provides business logic operations for payments.
    """

    def __init__(self, session: AsyncSession, *, user_id: str | None = None):
        """Initialize service with session and user context.

        Args:
            session: Database session
            user_id: Current user ID for audit

        """
        self.session = session
        self.repo = PaymentRepository(session, user_id=user_id)
        self.terminal_repo = TerminalRepository(session, user_id=user_id)
        self.user_id = user_id

    async def list(
        self, *, filters: PaymentFilter | None = None
    ) -> PaginatedResponse[PaymentSchema]:
        """List payments with filters, pagination, search and sorting."""
        # Set default filter if none provided
        if filters is None:
            filters = PaymentFilter()

        # Get data, total count and total pages
        items, total, total_pages = await self.repo.list(filters=filters)

        # Convert to schemas
        payment_schemas = [PaymentSchema.model_validate(item) for item in items]

        return PaginatedResponse(
            data=payment_schemas,
            pagination=PaginationMeta(
                page=filters.page, limit=filters.limit, total=total, total_pages=total_pages
            ),
        )

    async def get(self, payment_id: int) -> PaymentSchema:
        """Get payment by ID."""
        db_payment = await self.repo.get(payment_id)
        if not db_payment:
            raise ValueError(f"Payment with ID {payment_id} not found")

        return PaymentSchema.model_validate(db_payment)

    async def get_by_request_id(self, request_id: str) -> PaymentSchema:
        """Get payment by request_id."""
        db_payment = await self.repo.get_by_request_id(request_id)
        if not db_payment:
            raise ValueError(f"Payment with request_id {request_id} not found")

        return PaymentSchema.model_validate(db_payment)

    async def get_payment_status(self, request_id: str) -> PaymentStatusResponse:
        """Get payment status by request_id."""
        db_payment = await self.repo.get_by_request_id(request_id)
        if not db_payment:
            raise ValueError(f"Payment with request_id {request_id} not found")

        # Return payment status response
        return PaymentStatusResponse(
            request_id=db_payment.request_id,
            qr_string=db_payment.deeplink if db_payment.status == PaymentStatus.PENDING else None,
            status=db_payment.status.value,
            amount=float(db_payment.amount),
            currency=db_payment.currency,
            expires_at=db_payment.expires_at,
            txn_id=db_payment.txn_id if db_payment.status == PaymentStatus.COMPLETED else None,
        )

    async def _auto_populate_hierarchy_ids_and_config(
        self,
        terminal_id: int,
        store_id: int | None = None,
        merchant_id: int | None = None,
        psp_id: int | None = None,
    ) -> tuple[object | None, int | None, int | None, int | None, dict | None]:
        """Auto-populate missing hierarchy IDs from terminal relationships and fetch payment config.

        Returns:
            tuple: (terminal, store_id, merchant_id, psp_id, payment_config)

        """
        # Eager load full hierarchy and payment config in one query
        stmt = (
            select(Terminal)
            .where(Terminal.id == terminal_id)
            .options(
                selectinload(Terminal.store)
                .selectinload(Store.merchant)
                .selectinload(Merchant.psp),
                selectinload(Terminal.store).selectinload(Store.payment_config),
            )
        )
        result = await self.session.execute(stmt)
        terminal = result.scalar_one_or_none()

        if not terminal:
            return None, store_id, merchant_id, psp_id, None

        # Get payment config from store if available
        payment_config = None
        if terminal.store and terminal.store.payment_config:
            payment_config = terminal.store.payment_config.config

        # Use terminal's relationships to populate missing IDs
        if terminal.store:
            # If store_id not provided, use terminal's store_id
            if not store_id:
                store_id = terminal.store.id

            # If merchant_id not provided and store has merchant
            if not merchant_id and terminal.store.merchant:
                merchant_id = terminal.store.merchant.id

            # If psp_id not provided and merchant has psp
            if not psp_id and terminal.store.merchant and terminal.store.merchant.psp:
                psp_id = terminal.store.merchant.psp.id

        return terminal, store_id, merchant_id, psp_id, payment_config

    async def init_payment(self, data: InitPaymentRequest) -> PaymentStatusResponse:
        """Initialize a new payment with PayPay QR code generation."""
        # Auto-populate hierarchy IDs and fetch payment config from store
        (
            terminal,
            store_id,
            merchant_id,
            psp_id,
            store_payment_config,
        ) = await self._auto_populate_hierarchy_ids_and_config(
            terminal_id=data.terminal_id,
            store_id=data.store_id,
            merchant_id=data.merchant_id,
            psp_id=data.psp_id,
        )

        if not terminal:
            raise not_found(f"Terminal with ID {data.terminal_id} not found")

        # Check if payment already exists
        existing = await self.repo.get_by_request_id(data.request_id)
        if existing:
            raise conflict(f"Payment with request_id {data.request_id} already exists")

        # Extract PayPay merchant_id from store's payment config
        paypay_merchant_id = None
        if store_payment_config and isinstance(store_payment_config, dict):
            # Get PayPay config from store's payment config
            paypay_config = store_payment_config.get("PAYPAY", {})
            if paypay_config:
                paypay_merchant_id = paypay_config.get("paypay_merchant_id")
                logger.info(
                    f"[Payment] Using PayPay merchant ID from store config: {paypay_merchant_id}"
                )

        # Initialize PayPay service with merchant_id if provided
        paypay_service = PayPayService(merchant_id=paypay_merchant_id)

        # Generate QR code through PayPay with actual payment data
        qr_response = await paypay_service.generate_qr_code(
            request_id=data.request_id,
            amount=Decimal(str(data.amount)),
            currency=data.currency,
            terminal_id=data.terminal_id,
        )

        logger.info(
            f"[Payment] QR code generated for {data.request_id}, merchant_id: {paypay_merchant_id}"
        )

        # Calculate expiration time from PayPay response
        # PayPay returns expiryDate as Unix timestamp (epoch)
        expires_at_ts = qr_response.data.expiryDate
        # Convert to timezone-aware UTC datetime for PostgreSQL TIMESTAMP WITH TIME ZONE
        expires_at = datetime.fromtimestamp(expires_at_ts, tz=UTC)

        # Create payment record with all IDs (including auto-populated ones)
        payment_model = PaymentModel(
            request_id=data.request_id,
            status=PaymentStatus.PENDING,
            amount=Decimal(str(data.amount)),
            currency=data.currency,
            tender=PaymentTender.PAYPAY,
            deeplink=qr_response.data.deeplink,
            expires_at=expires_at,
            terminal_id=data.terminal_id,
            store_id=store_id,
            merchant_id=merchant_id,
            psp_id=psp_id,
        )

        await self.repo.create(payment_model)

        # No need to queue - the poller will automatically pick it up
        logger.info(f"Payment {data.request_id} created, poller will check status automatically")

        # Return response
        return PaymentStatusResponse(
            request_id=data.request_id,
            qr_string=qr_response.data.deeplink,
            status=PaymentStatus.PENDING.value,  # Use PaymentStatus enum value
            amount=data.amount,
            currency=data.currency,
            expires_at=expires_at,
        )

    async def get_payment_status(self, request_id: str) -> PaymentStatusResponse:
        """Get payment status by request_id."""
        payment = await self.repo.get_by_request_id(request_id)
        if not payment:
            raise ValueError(f"Payment with request_id {request_id} not found")

        return PaymentStatusResponse(
            request_id=payment.request_id,
            qr_string=payment.deeplink if payment.deeplink else None,
            status=payment.status.value,  # Use PaymentStatus enum value directly
            amount=int(payment.amount),
            currency=payment.currency,
            expires_at=payment.expires_at or datetime.now(UTC),
            txn_id=payment.txn_id,
        )

    async def update_payment_status_by_request_id(
        self, request_id: str, status: PaymentStatus, txn_id: str | None = None
    ):
        """Update payment status by request_id with optional transaction ID."""
        # Use PaymentStatus directly
        payment_status = status
        await self.repo.update_status_by_request_id(request_id, payment_status, txn_id=txn_id)
        logger.info(
            f"Updated payment {request_id} status to {payment_status}"
            + (f" with TXN ID: {txn_id}" if txn_id else "")
        )
