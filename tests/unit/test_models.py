"""
Unit tests for database models.

Tests model creation, validation, and relationships.
"""

from decimal import Decimal

import pytest

from app.models.payment import Payment, PaymentStatus, PaymentTender


class TestPaymentStatus:
    """Test PaymentStatus enum."""

    def test_payment_status_values(self):
        """Test all payment status values exist."""
        assert PaymentStatus.PENDING == "PENDING"
        assert PaymentStatus.COMPLETED == "COMPLETED"
        assert PaymentStatus.FAILED == "FAILED"
        assert PaymentStatus.CANCELLED == "CANCELLED"
        assert PaymentStatus.TIMEOUT == "TIMEOUT"

    def test_payment_status_is_enum(self):
        """Test PaymentStatus is an enum."""
        assert issubclass(PaymentStatus, str)
        statuses = [status.value for status in PaymentStatus]
        assert "PENDING" in statuses
        assert "COMPLETED" in statuses


class TestPaymentTender:
    """Test PaymentTender enum."""

    def test_payment_tender_values(self):
        """Test payment tender values."""
        assert PaymentTender.PAYPAY == "PAYPAY"
        assert PaymentTender.RAKUTEN == "RAKUTEN"

    def test_payment_tender_is_enum(self):
        """Test PaymentTender is an enum."""
        assert issubclass(PaymentTender, str)


class TestPaymentModel:
    """Test Payment model."""

    @pytest.mark.asyncio
    async def test_payment_creation(self, db_session):
        """Test creating a payment record."""
        payment = Payment(
            amount=Decimal("1000.00"),
            currency="JPY",
            status=PaymentStatus.PENDING,
            tender=PaymentTender.PAYPAY,
            terminal_id="TERM001",
            store_id=1,
            merchant_id=1,
            psp_id=1,
        )

        db_session.add(payment)
        await db_session.commit()
        await db_session.refresh(payment)

        assert payment.id is not None
        assert payment.request_id is not None
        assert payment.amount == Decimal("1000.00")
        assert payment.status == PaymentStatus.PENDING

    @pytest.mark.asyncio
    async def test_payment_request_id_unique(self, db_session):
        """Test payment request_id is unique."""
        payment1 = Payment(
            amount=Decimal("1000.00"),
            currency="JPY",
            status=PaymentStatus.PENDING,
            tender=PaymentTender.PAYPAY,
            terminal_id="TERM001",
            store_id=1,
            merchant_id=1,
            psp_id=1,
        )

        payment2 = Payment(
            amount=Decimal("2000.00"),
            currency="JPY",
            status=PaymentStatus.PENDING,
            tender=PaymentTender.PAYPAY,
            terminal_id="TERM002",
            store_id=1,
            merchant_id=1,
            psp_id=1,
        )

        db_session.add(payment1)
        db_session.add(payment2)
        await db_session.commit()

        # request_id should be different
        assert payment1.request_id != payment2.request_id

    @pytest.mark.asyncio
    async def test_payment_default_values(self, db_session):
        """Test payment default values are set."""
        payment = Payment(
            amount=Decimal("1000.00"),
            currency="JPY",
            status=PaymentStatus.PENDING,
            tender=PaymentTender.PAYPAY,
            terminal_id="TERM001",
            store_id=1,
            merchant_id=1,
            psp_id=1,
        )

        db_session.add(payment)
        await db_session.commit()
        await db_session.refresh(payment)

        # Check default/auto-generated fields
        assert payment.request_id is not None
        assert payment.created_at is not None
        assert payment.updated_at is not None

    @pytest.mark.asyncio
    async def test_payment_status_update(self, db_session):
        """Test updating payment status."""
        payment = Payment(
            amount=Decimal("1000.00"),
            currency="JPY",
            status=PaymentStatus.PENDING,
            tender=PaymentTender.PAYPAY,
            terminal_id="TERM001",
            store_id=1,
            merchant_id=1,
            psp_id=1,
        )

        db_session.add(payment)
        await db_session.commit()
        await db_session.refresh(payment)

        # Update status
        payment.status = PaymentStatus.COMPLETED
        await db_session.commit()
        await db_session.refresh(payment)

        assert payment.status == PaymentStatus.COMPLETED
