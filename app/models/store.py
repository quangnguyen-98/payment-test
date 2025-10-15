from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.merchant import Merchant
    from app.models.store_payment_config import StorePaymentConfig
    from app.models.terminal import Terminal


class Store(BaseModel):
    """Store model - Minimal definition for payment gateway
    References stores table from stab_portal_api
    """

    __tablename__ = "stores"

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Foreign key to merchant
    merchant_id: Mapped[int | None] = mapped_column(
        ForeignKey("merchants.id"), nullable=True, index=True
    )

    # Relationships
    merchant: Mapped[Optional["Merchant"]] = relationship(
        "Merchant", back_populates="stores", lazy="select"
    )

    terminals: Mapped[list["Terminal"]] = relationship(
        "Terminal", back_populates="store", lazy="select"
    )

    payment_config: Mapped[Optional["StorePaymentConfig"]] = relationship(
        "StorePaymentConfig", back_populates="store", lazy="select", uselist=False
    )

    def __repr__(self):
        return f"<Store(id={self.id}, name={self.name})>"
