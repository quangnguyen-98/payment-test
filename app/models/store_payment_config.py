"""Store Payment Configuration model for managing payment settings per store.

This model stores ALL payment configurations for a store in a single record.
"""

from sqlalchemy import JSON, Column, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class StorePaymentConfig(BaseModel):
    """Store Payment Configuration model.

    Stores ALL payment brand configurations for a store in one record.
    Each store has exactly one config record.
    """

    __tablename__ = "store_payment_configs"

    # Foreign key - one config per store
    store_id = Column(
        Integer,
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One config per store
        index=True,
    )

    # All payment configurations stored as JSON
    # Structure:
    # {
    #   "PAYPAY": {
    #     "paypay_merchant_id": "MERCH001",
    #     "paypay_merchant_name": "Store ABC"
    #   },
    #   "AUPAY": {
    #     "aupay_company_code": "COMP123",
    #     "aupay_qr_payment_merchant_id": "QR456"
    #   }
    # }
    config = Column(JSON, nullable=False, default=dict)

    # Relationship - one-to-one with Store
    store = relationship("Store", back_populates="payment_config", uselist=False)

    def __repr__(self):
        return f"<StorePaymentConfig(store_id={self.store_id})>"
