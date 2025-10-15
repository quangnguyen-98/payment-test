"""Simple payment status poller that queries database for pending payments.

This service periodically checks pending payments and updates their status
by calling PayPay API with rate limiting to avoid hitting API limits.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.payment import Payment, PaymentStatus
from app.services.paypay_service import PayPayService

logger = logging.getLogger(__name__)


class PaymentPoller:
    """Service that polls pending payments from database."""

    def __init__(self):
        """Initialize the poller with configuration."""
        self.paypay_service = PayPayService()
        self.rate_limit_delay = 1.0  # Delay between API calls in seconds
        self.batch_size = 5  # Number of payments to check per batch
        self.check_interval = 5  # Seconds between database checks (reduced from 10)
        self.max_pending_time = 600  # Max time (seconds) to keep checking a payment

    async def get_pending_payments(self, session: AsyncSession, limit: int = 10) -> list[Payment]:
        """Get pending payments that need status check (excluding expired ones)."""
        try:
            # Calculate cutoff time - don't check payments older than max_pending_time
            cutoff_time = datetime.now(UTC) - timedelta(seconds=self.max_pending_time)
            now = datetime.now(UTC)

            result = await session.execute(
                select(Payment)
                .where(
                    and_(
                        Payment.status == PaymentStatus.PENDING,
                        Payment.created_at > cutoff_time,  # Only recent payments
                        Payment.expires_at > now,  # Skip expired (handled separately)
                    )
                )
                .order_by(Payment.created_at.desc())  # Check newest first
                .limit(limit)
            )

            payments = result.scalars().all()

            if payments:
                logger.info(f"📋 Found {len(payments)} pending payments to check")
                for p in payments:
                    logger.debug(f"  - {p.request_id} (created: {p.created_at})")

            return payments

        except Exception as e:
            logger.error(f"Error fetching pending payments: {e}")
            return []

    async def check_payment_status(self, session: AsyncSession, payment: Payment) -> bool:
        """Check and update payment status from PayPay."""
        try:
            logger.info(f"🔍 Checking status for payment {payment.request_id}")

            # Call PayPay API
            result = await self.paypay_service.get_payment_details(payment.request_id)

            # Check API response
            result_info = result.get("resultInfo", {})
            if result_info.get("code") != "SUCCESS":
                logger.warning(
                    f"PayPay API error for {payment.request_id}: {result_info.get('message')}"
                )
                return False  # Will retry later

            data = result.get("data", {})
            paypay_status = data.get("status")

            logger.info(f"📊 PayPay status for {payment.request_id}: {paypay_status}")

            # Update based on PayPay status
            status_updated = False

            if paypay_status == "COMPLETED":
                payment.status = PaymentStatus.COMPLETED
                payment.txn_id = data.get("paymentId")
                logger.info(f"✅ Payment {payment.request_id} COMPLETED (txn: {payment.txn_id})")
                status_updated = True

            elif paypay_status == "FAILED":
                payment.status = PaymentStatus.FAILED
                logger.info(f"❌ Payment {payment.request_id} FAILED")
                status_updated = True

            elif paypay_status == "EXPIRED":
                payment.status = PaymentStatus.TIMEOUT
                logger.info(f"⏱️ Payment {payment.request_id} EXPIRED")
                status_updated = True

            elif paypay_status == "CANCELED":
                payment.status = PaymentStatus.CANCELLED
                logger.info(f"🚫 Payment {payment.request_id} CANCELLED")
                status_updated = True

            elif paypay_status in ["CREATED", "AUTHORIZED"]:
                # Still pending - no update needed
                logger.debug(f"⏳ Payment {payment.request_id} still pending")
                status_updated = False
            else:
                logger.warning(f"Unknown PayPay status '{paypay_status}' for {payment.request_id}")
                status_updated = False

            if status_updated:
                payment.updated_at = datetime.now(UTC)
                await session.commit()
                logger.info(f"💾 Updated payment {payment.request_id} to {payment.status.value}")

            return status_updated

        except Exception as e:
            logger.error(f"Error checking payment {payment.request_id}: {e}", exc_info=True)
            await session.rollback()
            return False

    async def process_batch(self, session: AsyncSession):
        """Process a batch of pending payments."""
        try:
            # First, handle expired payments separately (no API call needed)
            await self.handle_expired_payments(session)

            # Get pending payments
            payments = await self.get_pending_payments(session, limit=self.batch_size)

            if not payments:
                logger.debug("No pending payments to check")
                return

            logger.info(f"🔄 Processing batch of {len(payments)} payments")

            # Check each payment with rate limiting
            for i, payment in enumerate(payments):
                try:
                    # Add delay between API calls to avoid rate limiting
                    if i > 0:
                        await asyncio.sleep(self.rate_limit_delay)

                    await self.check_payment_status(session, payment)

                except Exception as e:
                    logger.error(f"Failed to check payment {payment.request_id}: {e}")
                    continue

            logger.info("✅ Batch processing complete")

        except Exception as e:
            logger.error(f"Error processing batch: {e}", exc_info=True)

    async def handle_expired_payments(self, session: AsyncSession):
        """Update all expired pending payments to TIMEOUT status."""
        try:
            now = datetime.now(UTC)

            # Find all expired pending payments
            result = await session.execute(
                select(Payment)
                .where(and_(Payment.status == PaymentStatus.PENDING, Payment.expires_at <= now))
                .limit(10)  # Process up to 10 expired payments at once
            )

            expired_payments = result.scalars().all()

            if expired_payments:
                logger.info(f"⏰ Found {len(expired_payments)} expired payments")

                for payment in expired_payments:
                    logger.info(
                        f"⏰ Marking payment {payment.request_id} as TIMEOUT (expired: {payment.expires_at})"
                    )
                    payment.status = PaymentStatus.TIMEOUT
                    payment.updated_at = now

                await session.commit()
                logger.info(f"✅ Updated {len(expired_payments)} expired payments to TIMEOUT")

        except Exception as e:
            logger.error(f"Error handling expired payments: {e}", exc_info=True)
            await session.rollback()

    async def get_stats(self, session: AsyncSession) -> dict:
        """Get polling statistics."""
        try:
            # Count payments by status
            result = await session.execute(
                select(Payment.status, func.count(Payment.id).label("count"))
                .where(Payment.created_at > datetime.now(UTC) - timedelta(hours=1))
                .group_by(Payment.status)
            )

            stats = {row[0].value: row[1] for row in result}

            # Add total pending older than 5 minutes
            old_pending_result = await session.execute(
                select(func.count(Payment.id)).where(
                    and_(
                        Payment.status == PaymentStatus.PENDING,
                        Payment.created_at < datetime.now(UTC) - timedelta(minutes=5),
                    )
                )
            )
            stats["old_pending"] = old_pending_result.scalar() or 0

            return stats

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}


async def run_poller():
    """Main poller loop that runs continuously."""
    logger.info("=" * 60)
    logger.info("🚀 Starting Payment Status Poller")
    logger.info("Rate limit delay: 1 second between API calls")
    logger.info("Batch size: 5 payments per cycle")
    logger.info("Check interval: 5 seconds")
    logger.info("Timeout: 300 seconds (5 minutes)")
    logger.info("=" * 60)

    # Create async engine
    if settings.DATABASE_URL.startswith("sqlite"):
        engine = create_async_engine(
            settings.DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///"),
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,
        )
    else:
        engine = create_async_engine(
            settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
            pool_pre_ping=True,
        )

    async_session = async_sessionmaker(engine, expire_on_commit=False)
    poller = PaymentPoller()

    iteration = 0
    last_stats_time = datetime.now(UTC)

    while True:
        try:
            iteration += 1

            async with async_session() as session:
                # Process a batch
                await poller.process_batch(session)

                # Log stats every 5 minutes
                if datetime.now(UTC) - last_stats_time > timedelta(minutes=5):
                    stats = await poller.get_stats(session)
                    logger.info(f"📊 Poller Stats: {stats}")
                    last_stats_time = datetime.now(UTC)

                # Health check every 100 iterations
                if iteration % 100 == 0:
                    logger.info(f"💚 Poller healthy - iteration {iteration}")

            # Wait before next check
            await asyncio.sleep(poller.check_interval)

        except Exception as e:
            logger.error(f"Poller error: {e}", exc_info=True)
            await asyncio.sleep(30)  # Wait longer on error


def start_payment_poller():
    """Start the payment poller in a background task."""
    import threading

    def run_in_thread():
        """Run the async poller in a new event loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(run_poller())
        except Exception as e:
            logger.error(f"Poller thread crashed: {e}")

    thread = threading.Thread(target=run_in_thread, daemon=True, name="PaymentPoller")
    thread.start()

    logger.info(f"✨ Payment poller started in thread {thread.name}")
    return thread
