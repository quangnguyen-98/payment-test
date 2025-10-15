"""PayPay-specific data models using Pydantic v2."""

from datetime import datetime

from pydantic import BaseModel, Field


class PayPayAmount(BaseModel):
    """PayPay amount model."""

    amount: int = Field(..., description="Amount in smallest currency unit (e.g., yen)")
    currency: str = Field(..., description="Currency code (e.g., 'JPY')")


class PayPayQRData(BaseModel):
    """PayPay QR code data model."""

    codeId: str = Field(..., description="Unique code ID")
    url: str = Field(..., description="QR code URL")
    expiryDate: int = Field(..., description="Expiration timestamp (epoch)")
    merchantPaymentId: str = Field(..., description="Merchant-defined payment ID")
    amount: PayPayAmount = Field(..., description="Amount and currency")
    codeType: str = Field(..., description="Type of the QR code")
    requestedAt: int = Field(..., description="Timestamp of the request (epoch)")
    isAuthorization: bool = Field(..., description="Whether the payment is an authorization")
    deeplink: str = Field(..., description="Deeplink to open PayPay app")


class PayPayResultInfo(BaseModel):
    """PayPay result information model."""

    code: str = Field(..., description="Result code")
    message: str = Field(..., description="Result message")
    codeId: str | None = Field(None, description="Optional code ID")


class PayPayQRResponse(BaseModel):
    """PayPay QR code generation response."""

    result_info: PayPayResultInfo = Field(..., description="Result information")
    data: PayPayQRData = Field(..., description="QR code data")


class PayPayQRRequest(BaseModel):
    """PayPay QR code generation request."""

    merchant_payment_id: str = Field(..., description="Merchant payment ID")
    amount: int = Field(..., description="Payment amount")
    currency: str = Field(default="JPY", description="Currency code")
    code_type: str = Field(default="ORDER_QR", description="QR code type")
    terminal_id: int | None = Field(None, description="Terminal ID")


class PayPayWebhookPayload(BaseModel):
    """PayPay webhook payload model."""

    notification_type: str = Field(..., description="Type of the notification")
    store_id: str | None = Field(None, description="Store ID")
    paid_at: datetime | None = Field(None, description="Payment time")
    expires_at: datetime | None = Field(None, description="Expiration time")
    merchant_order_id: str = Field(..., description="Merchant's order ID")
    pos_id: str | None = Field(None, description="POS ID")
    order_amount: int = Field(
        ..., description="Order amount in smallest currency unit (e.g. cents)"
    )
    merchant_id: str = Field(..., description="Merchant ID")
    state: str = Field(..., description="Payment state")
    order_id: str = Field(..., description="PayPay order ID")
    authorized_at: datetime | None = Field(None, description="Authorization time")
