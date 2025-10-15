from fastapi import APIRouter

# Import endpoint routers
from app.api.v1 import payments

api_router = APIRouter()


# Include entity routers
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
