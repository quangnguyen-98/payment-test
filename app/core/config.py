# app/core/config.py - Configuration for Payment Gateway API
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings using Pydantic BaseSettings"""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    # Application
    API_TITLE: str = "STAB Payment API"
    API_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Environment (only local and production supported)
    ENVIRONMENT: Literal["local", "production"] = "local"

    # Documentation control (independent from DEBUG mode)
    ENABLE_DOCS: bool = True

    # Database
    DATABASE_URL: str = "sqlite:///./stab_payment_gateway.db"

    # Database Connection Pool Settings (for PostgreSQL)
    DB_POOL_SIZE: int = 50  # Increased for production load
    DB_MAX_OVERFLOW: int = 50  # Allow up to 100 total connections
    DB_POOL_TIMEOUT: int = 30  # Wait up to 30 seconds for connection
    DB_POOL_RECYCLE: int = 3600  # Recycle connections after 1 hour

    # Logging
    LOG_LEVEL: str = "INFO"

    # SQL Logging (separate from app logging)
    SQL_LOG_LEVEL: str = (
        "ERROR"  # DEBUG shows all queries, INFO shows pool events, WARNING only errors
    )
    SQL_POOL_LOG_ENABLED: bool = False  # Enable connection pool logging

    # CORS settings
    ALLOWED_ORIGINS: list[str] = ["*"]
    ALLOWED_METHODS: list[str] = ["*"]
    ALLOWED_HEADERS: list[str] = ["*"]

    # Trusted Host Middleware settings (comma-separated string in env, converted to list)
    ALLOWED_HOSTS: str = Field(
        default="localhost,127.0.0.1,10.0.2.2,*.localhost",
        description="Comma-separated list of allowed hosts for TrustedHostMiddleware",
    )

    @field_validator("ALLOWED_HOSTS", mode="after")
    @classmethod
    def parse_allowed_hosts(cls, v: str) -> list[str]:
        """Parse comma-separated ALLOWED_HOSTS string into list."""
        if isinstance(v, str):
            return [host.strip() for host in v.split(",") if host.strip()]
        return v

    # AWS Cognito Configuration
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_COGNITO_USER_POOL_ID: str | None = None
    AWS_COGNITO_CLIENT_ID: str | None = None

    # Payment Gateway Specific Settings
    PAYMENT_TIMEOUT: int = 300  # 5 minutes for payment processing

    # Queue Configuration
    QUEUE_POLL_INTERVAL: int = 5  # seconds
    PAYMENT_TIMEOUT_MINUTES: int = 15  # minutes

    # PayPay Configuration
    BFF_BASE_URL: str = "http://localhost:8005"  # Default for development
    PAYPAY_API_KEY: str = "mock_api_key"  # Default for development
    PAYPAY_API_SECRET: str = "mock_api_secret"  # Default for development
    PAYPAY_MERCHANT_ID: str = "mock_merchant_id"  # Default for development
    PAYPAY_PRODUCTION_MODE: bool = False  # False for sandbox, True for production

    # API Base URL for frontend JavaScript calls
    API_BASE_URL: str = ""  # Empty for local dev, "/payment-api" for production


settings = Settings()
