"""
Pytest configuration and fixtures for stab-payment-api tests.

Provides reusable fixtures for database, FastAPI client, and mock data.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database_manager import Base, db_manager


# ============================================================================
# Async Event Loop
# ============================================================================
@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Database Fixtures
# ============================================================================
@pytest.fixture(scope="function")
async def db_engine():
    """Create test database engine with in-memory SQLite."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker

    async_session = sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session


# ============================================================================
# FastAPI Client Fixtures
# ============================================================================
@pytest.fixture(scope="function")
def client() -> TestClient:
    """Create FastAPI test client (sync)."""
    from main import app

    return TestClient(app)


@pytest.fixture(scope="function")
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create async FastAPI test client with database override."""
    from main import app

    # Override database dependency
    async def override_get_db():
        yield db_session

    app.dependency_overrides[db_manager.get_session] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    # Clear overrides
    app.dependency_overrides.clear()


# ============================================================================
# Mock Data Fixtures
# ============================================================================
@pytest.fixture
def mock_payment_data():
    """Mock payment data for testing."""
    return {
        "amount": 1000,
        "currency": "JPY",
        "terminal_id": "TERM001",
        "store_id": 1,
        "merchant_id": 1,
        "psp_id": 1,
    }


@pytest.fixture
def mock_paypay_response():
    """Mock PayPay API response."""
    return {
        "resultInfo": {
            "code": "SUCCESS",
            "message": "Success",
            "codeId": "08100001",
        },
        "data": {
            "codeId": "mock_code_id_123",
            "url": "https://qr.paypay.ne.jp/mock_qr_code",
            "deeplink": "paypay://payment/mock_code_id_123",
            "expiryDate": 1234567890,
            "merchantPaymentId": "test_payment_001",
            "amount": {"amount": 1000, "currency": "JPY"},
            "orderDescription": "Test Payment",
            "codeType": "ORDER_QR",
        },
    }


@pytest.fixture
def mock_environment_vars(monkeypatch):
    """Set test environment variables."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("PAYPAY_API_KEY", "test_api_key")
    monkeypatch.setenv("PAYPAY_API_SECRET", "test_api_secret")
    monkeypatch.setenv("PAYPAY_MERCHANT_ID", "test_merchant_id")
    monkeypatch.setenv("PAYPAY_PRODUCTION_MODE", "false")
