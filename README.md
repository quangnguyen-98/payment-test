# STAB Payment API

FastAPI-based payment gateway service for PayPay and other payment providers with direct database access.

## Features

- Payment initialization with QR code generation
- Payment status monitoring with background polling
- Direct database access to stab_portal_api payment tables
- PayPay integration (mock implementation for development)
- Background queue processing for payment status updates

## Quick Start

### 1. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
# Key settings:
# - DATABASE_URL: Connection string to stab_portal_api database
# - PAYPAY_API_KEY, PAYPAY_API_SECRET, PAYPAY_MERCHANT_ID: PayPay credentials
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the Service

```bash
# Development mode with auto-reload
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8000
```

The service will be available at:
- API: http://localhost:8000
- Documentation: http://localhost:8000/docs

## API Endpoints

### POST /payments/init
Initialize a new payment with PayPay QR code generation.

**Request:**
```json
{
  "request_id": "unique-payment-id",
  "amount": "100.00",
  "currency": "JPY",
  "tender": "PAYPAY",
  "terminal_id": 1
}
```

**Response:**
```json
{
  "request_id": "unique-payment-id",
  "status": "PENDING",
  "amount": "100.00",
  "currency": "JPY",
  "qr_string": "paypay://payment?link_key=MOCK_12345",
  "expires_at": "2025-09-17T21:00:00Z"
}
```

### GET /payments/{request_id}
Get payment status by request ID.

**Response:**
```json
{
  "request_id": "unique-payment-id",
  "status": "PENDING",
  "amount": "100.00",
  "currency": "JPY",
  "tender": "PAYPAY",
  "qr_string": "paypay://payment?link_key=MOCK_12345",
  "txn_id": null,
  "created_at": "2025-09-17T20:45:00Z",
  "expires_at": "2025-09-17T21:00:00Z"
}
```

### GET /health
Health check endpoint.

## Architecture

### Services
- **PayPayService**: PayPay API integration (mock for development)
- **PaymentService**: Direct database operations on payment tables
- **Queue Consumer**: Background payment status monitoring

### Payment Flow
1. Client calls `/payments/init`
2. Service generates PayPay QR code
3. Payment record created directly in database
4. Background worker monitors payment status
5. Client polls `/payments/{request_id}` for status updates

## Development Notes

- Currently uses mock PayPay responses for development
- Background queue uses in-memory Queue (replace with Redis/SQS for production)
- Payment status polling runs in background thread
- Direct database access to payment tables (same DB as stab_portal_api)

## Dependencies

- **Database**: Requires access to stab_portal_api database
- **PayPay API**: Configure credentials for production use

## Configuration

Key environment variables:
- `DATABASE_URL`: Database connection string (PostgreSQL or SQLite)
- `PAYPAY_API_*`: PayPay API credentials
- `PORT`: Service port (default: 8000)
- `QUEUE_POLL_INTERVAL`: Background polling interval in seconds (default: 5)