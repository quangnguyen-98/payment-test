"""STAB Payment API

Main FastAPI application for the payment service.
Handles payment processing, refunds, and status updates.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import payments
from app.core.config import settings
from app.core.database_manager import check_async_database_health, db_manager
from app.services.payment_poller import start_payment_poller

# Configure logging
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler.

    Handles startup and shutdown events for the FastAPI application.
    """
    # Startup
    logger.info(f"Starting {settings.API_TITLE} v{settings.API_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    # Initialize database
    try:
        await db_manager.initialize()
        health = await db_manager.check_health()
        if health["healthy"]:
            logger.info("Database connection established successfully")
        else:
            logger.error(f"Database health check failed: {health['message']}")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

    # Start payment status poller (only 1 worker to avoid duplicates)
    start_payment_poller()

    yield

    # Shutdown
    logger.info("Shutting down application...")
    await db_manager.close()
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="STAB Payment API for processing payments, refunds, and status updates",
    debug=settings.DEBUG,
    docs_url="/docs" if settings.ENABLE_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_DOCS else None,
    lifespan=lifespan,
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.ALLOWED_METHODS,
    allow_headers=settings.ALLOWED_HEADERS,
)

# Disable TrustedHostMiddleware for development (Android emulator compatibility)
# app.add_middleware(
#     TrustedHostMiddleware,
#     allowed_hosts=settings.ALLOWED_HOSTS
# )

# Include API routers
app.include_router(payments.router, prefix="/api/v1")


# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.API_TITLE,
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health/database")
async def database_health_check():
    """Database health check endpoint."""
    try:
        health = await check_async_database_health()
        return {"status": "healthy" if health["healthy"] else "unhealthy", "database": health}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


@app.get("/")
async def root():
    """Root endpoint with basic API information."""
    return {
        "service": settings.API_TITLE,
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT,
        "docs_url": "/docs" if settings.ENABLE_DOCS else None,
        "health_url": "/health",
    }


@app.get("/favicon.ico")
async def favicon():
    """Return empty favicon to avoid 404 errors."""
    from fastapi.responses import Response

    return Response(content="", media_type="image/x-icon")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
