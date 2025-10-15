import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class PaymentStatus(str, enum.Enum):
    """Payment status enumeration."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"  # Add timeout status


class PaymentTender(str, enum.Enum):
    """Payment tender enumeration."""

    PAYPAY = "PAYPAY"
    RAKUTEN = "RAKUTEN"


class Payment(BaseModel):
    """Payment model - SQLAlchemy v2 style with type annotations
    Enhanced for payment gateway integration.
    """

    __tablename__ = "payments"

    # External UUID for API communications
    request_id: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True, default=lambda: str(uuid.uuid4())
    )

    # Required fields
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2), nullable=False, index=True
    )

    # Currency field (JPY, USD, etc.)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="JPY")

    # Payment method
    tender: Mapped[PaymentTender] = mapped_column(
        Enum(PaymentTender), nullable=False, default=PaymentTender.PAYPAY
    )

    # Status field
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False, index=True
    )

    # PayPay/provider specific fields
    deeplink: Mapped[str | None] = mapped_column(Text, nullable=True)

    txn_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),  # Use timezone-aware datetime like created_at/updated_at
        nullable=True,
    )

    # Hierarchy IDs - no foreign key constraints to allow flexible joins
    terminal_id: Mapped[int | None] = mapped_column(
        nullable=True,
        index=True,  # Keep index for performance
    )

    store_id: Mapped[int | None] = mapped_column(
        nullable=True,
        index=True,  # Keep index for performance
    )

    merchant_id: Mapped[int | None] = mapped_column(
        nullable=True,
        index=True,  # Keep index for performance
    )

    psp_id: Mapped[int | None] = mapped_column(
        nullable=True,
        index=True,  # Keep index for performance
    )

    def __repr__(self):
        return f"<Payment(id={self.id}, request_id={self.request_id}, amount={self.amount}, status={self.status})>"
