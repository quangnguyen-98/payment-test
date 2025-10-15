"""Payment Repository - Data access layer for payment operations.

Provides database operations for payment entities using repository pattern
with mixins for common functionality.
"""

from collections.abc import Sequence

from app.models.payment import Payment, PaymentStatus
from app.models.terminal import Terminal
from app.repositories.base_mixins import (
    BulkOperationsMixin,
    CRUDMixin,
    EagerLoadMixin,
    PaginationMixin,
)
from app.repositories.filter_constants import FilterOperators, FilterTypes


class PaymentRepository(CRUDMixin[Payment], BulkOperationsMixin, EagerLoadMixin, PaginationMixin):
    """Repository class for Payment entity.

    Handles all database operations for payments with support for:
    - CRUD operations
    - Bulk operations
    - Search and filtering
    - Pagination
    - Payment-specific operations
    """

    # Fields that support text search
    SEARCHABLE_FIELDS = ["request_id", "txn_id"]

    # Declarative filter configuration
    FILTER_CONFIG = {
        "status": {"type": FilterTypes.DIRECT, "field": "status", "operator": FilterOperators.AUTO},
        "terminal_id": {
            "type": FilterTypes.DIRECT,
            "field": "terminal_id",
            "operator": FilterOperators.AUTO,
        },
        # Manual join filter for store_id through terminal
        "store_id": {"type": FilterTypes.CUSTOM, "handler": "_filter_by_store_id"},
        "payment_id": {
            "type": FilterTypes.DIRECT,
            "field": "id",  # Maps payment_id to Payment.id
            "operator": FilterOperators.AUTO,
        },
        "amount_gte": {
            "type": FilterTypes.DIRECT,
            "field": "amount",
            "operator": FilterOperators.GTE,
        },
        "amount_lte": {
            "type": FilterTypes.DIRECT,
            "field": "amount",
            "operator": FilterOperators.LTE,
        },
        "tender": {"type": FilterTypes.DIRECT, "field": "tender", "operator": FilterOperators.AUTO},
        "currency": {
            "type": FilterTypes.DIRECT,
            "field": "currency",
            "operator": FilterOperators.AUTO,
        },
    }

    def __init__(self, session, **kwargs):
        super().__init__(session, **kwargs)
        self.model = Payment
        self.id_attr = Payment.id
        self.tenant_attr = None  # No tenant for payment

    async def get_by_request_id(self, request_id: str) -> Payment | None:
        """Get payment by request_id."""
        stmt = self._base_query().where(Payment.request_id == request_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_txn_id(self, txn_id: str) -> Payment | None:
        """Get payment by transaction ID."""
        stmt = self._base_query().where(Payment.txn_id == txn_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def _filter_by_store_id(self, stmt, value):
        """Custom filter for store_id through terminal join."""
        stmt = stmt.join(Terminal, Payment.terminal_id == Terminal.id)
        if isinstance(value, list):
            stmt = stmt.where(Terminal.store_id.in_(value))
        else:
            stmt = stmt.where(Terminal.store_id == value)
        return stmt

    async def get_by_terminal(self, terminal_id: int) -> Sequence[Payment]:
        """Get all payments for a terminal."""
        stmt = self._base_query().where(Payment.terminal_id == terminal_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_pending_payments(self) -> Sequence[Payment]:
        """Get all pending payments."""
        stmt = self._base_query().where(Payment.status == PaymentStatus.PENDING)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_completed_payments(self) -> Sequence[Payment]:
        """Get all completed payments."""
        stmt = self._base_query().where(Payment.status == PaymentStatus.COMPLETED)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_failed_payments(self) -> Sequence[Payment]:
        """Get all failed payments."""
        stmt = self._base_query().where(Payment.status == PaymentStatus.FAILED)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_status_by_request_id(
        self, request_id: str, status: PaymentStatus, txn_id: str | None = None
    ) -> Payment | None:
        """Update payment status by request_id with optional transaction ID."""
        payment = await self.get_by_request_id(request_id)
        if not payment:
            return None

        payment.status = status
        if txn_id:
            payment.txn_id = txn_id

        await self.session.commit()
        await self.session.refresh(payment)
        return payment
