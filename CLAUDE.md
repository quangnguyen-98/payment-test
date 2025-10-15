# CLAUDE.md - Payment API

## Service Overview
**Name**: stab-payment-api
**Type**: FastAPI Payment Processing Service
**Purpose**: Handle payment transactions with PayPay and other providers
**Port**: 8007

## Architecture Position
```
[Payment WebView] → [Payment API] → [PayPay Gateway]
                           ↓
                    [Shared Database]
```

## Key Responsibilities
1. **Payment Creation**: Initialize payments and generate QR codes
2. **Status Polling**: Track payment status with providers
3. **Transaction Management**: Store and retrieve payment records
4. **Provider Integration**: Interface with PayPay, future providers

## Technical Stack
- **Framework**: FastAPI
- **ASGI Server**: Uvicorn
- **Database**: PostgreSQL with SQLAlchemy
- **Async**: asyncio, httpx
- **Validation**: Pydantic
- **Migrations**: Alembic

## Project Structure
```
app/
├── main.py                    # FastAPI app entry
├── api/
│   └── v1/
│       ├── endpoints/
│       │   └── payments.py  # Payment endpoints
│       └── deps.py          # Dependencies
├── core/
│   ├── config.py           # Settings
│   ├── database.py         # Database connection
│   └── exceptions.py       # Custom exceptions
├── models/
│   └── payment.py          # SQLAlchemy models
├── schemas/
│   ├── payment.py          # Pydantic schemas
│   └── paypay.py          # PayPay specific schemas
├── services/
│   ├── payment_service.py  # Payment business logic
│   ├── paypay_service.py  # PayPay integration
│   └── payment_poller.py  # Background status polling
└── db/
    └── base.py            # Database base config
```

## Python Coding Standards

### Import Organization
```python
# ✅ CORRECT - Imports at top, properly organized
# Standard library
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import uuid4

# Third party
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

# Local application
from app.core.database import get_db
from app.models.payment import Payment
from app.schemas.payment import PaymentCreate, PaymentResponse
from app.services.paypay_service import PayPayService

# ❌ WRONG - Don't import inside functions
async def create_payment(data: PaymentCreate):
    from app.services.paypay_service import PayPayService  # NO!
```

### Async Database Operations
```python
# ✅ CORRECT - Async all the way
async def get_payment(
    payment_id: str,
    db: AsyncSession = Depends(get_db)
) -> Optional[Payment]:
    result = await db.execute(
        select(Payment).where(Payment.id == payment_id)
    )
    return result.scalar_one_or_none()

# ❌ WRONG - Don't use sync operations
def get_payment(payment_id: str):  # Should be async
    return db.query(Payment).filter(Payment.id == payment_id).first()
```

### Service Layer Pattern
```python
# ✅ CORRECT - Business logic in service layer
class PaymentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.paypay = PayPayService()

    async def create_payment(
        self,
        amount: int,
        currency: str,
        terminal_id: str
    ) -> Payment:
        # Generate unique request ID
        request_id = str(uuid4())

        # Create QR with provider
        qr_data = await self.paypay.create_qr_code(
            amount=amount,
            merchant_payment_id=request_id
        )

        # Save to database
        payment = Payment(
            request_id=request_id,
            amount=amount,
            currency=currency,
            terminal_id=terminal_id,
            qr_code=qr_data.qr_code,
            status="PENDING"
        )
        self.db.add(payment)
        await self.db.commit()

        return payment
```

### Error Handling
```python
# ✅ CORRECT - Proper error handling
async def get_payment_status(payment_id: str) -> PaymentResponse:
    try:
        payment = await payment_service.get_payment(payment_id)
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Payment {payment_id} not found"
            )
        return PaymentResponse.from_orm(payment)

    except Exception as e:
        logger.error(f"Error fetching payment {payment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
```

## API Endpoints
```python
# POST /api/v1/payments/init
async def init_payment(
    data: PaymentCreate,
    db: AsyncSession = Depends(get_db)
) -> PaymentResponse:
    """Initialize new payment with QR code."""
    service = PaymentService(db)
    payment = await service.create_payment(
        amount=data.amount,
        currency=data.currency,
        terminal_id=data.terminal_id
    )
    return PaymentResponse.from_orm(payment)

# GET /api/v1/payments/{payment_id}/status
async def get_payment_status(
    payment_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Get current payment status."""
    service = PaymentService(db)
    payment = await service.get_payment(payment_id)
    return {"status": payment.status, "txn_id": payment.txn_id}
```

## Background Tasks
```python
# Payment status polling
async def poll_payment_status():
    """Background task to poll pending payments."""
    while True:
        try:
            async with get_db_context() as db:
                service = PaymentService(db)
                pending_payments = await service.get_pending_payments()

                for payment in pending_payments:
                    status = await service.check_payment_status(payment.id)
                    if status != "PENDING":
                        await service.update_payment_status(
                            payment.id, status
                        )

        except Exception as e:
            logger.error(f"Polling error: {e}")

        await asyncio.sleep(3)  # Poll every 3 seconds
```

## Environment Variables
```env
# .env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/stabdb
PAYPAY_API_KEY=xxx
PAYPAY_API_SECRET=xxx
PAYPAY_MERCHANT_ID=xxx
PAYPAY_BASE_URL=https://api.paypay.ne.jp
POLLING_INTERVAL=3
PAYMENT_TIMEOUT=300
```

## Database Migrations
```bash
# Create migration
alembic revision --autogenerate -m "Add payment table"

# Run migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Running the Service
```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Development
uvicorn app.main:app --reload --port 8007

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8007 --workers 4

# Docker
docker build -t stab-payment-api .
docker run -p 8007:8007 stab-payment-api
```

## Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run async tests
pytest -m asyncio
```

## Common Issues & Solutions

### Database Connection Issues
- Check DATABASE_URL format
- Verify PostgreSQL is running
- Check network connectivity

### PayPay Integration Fails
- Verify API credentials
- Check merchant ID configuration
- Review PayPay API documentation

### Polling Performance
- Adjust POLLING_INTERVAL
- Implement connection pooling
- Consider using Redis for caching

## Related Services
- **Payment WebView**: Frontend that initiates payments
- **Portal API**: Shares database for payment records
- **PayPay Gateway**: External payment provider