import logging
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from paypayopa import Client

from app.core.config import settings
from app.core.errors import bad_request, upstream_error
from app.schemas.paypay import (
    PayPayQRData,
    PayPayQRRequest,
    PayPayQRResponse,
    PayPayResultInfo,
)

logger = logging.getLogger(__name__)


class PayPayService:
    """Service for integrating with PayPay API using official SDK"""

    def __init__(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        merchant_id: str | None = None,
        production_mode: bool | None = None,
    ):
        self.api_key = api_key or settings.PAYPAY_API_KEY
        self.api_secret = api_secret or settings.PAYPAY_API_SECRET
        self.merchant_id = merchant_id or settings.PAYPAY_MERCHANT_ID
        self.production_mode = (
            production_mode if production_mode is not None else settings.PAYPAY_PRODUCTION_MODE
        )

        if not self.api_key or not self.api_secret or not self.merchant_id:
            raise ValueError("PayPay credentials (API key, secret, or merchant ID) not configured")

        # Initialize PayPay client
        self.client = Client(
            auth=(self.api_key, self.api_secret), production_mode=self.production_mode
        )
        self.client.set_assume_merchant(self.merchant_id)

    async def generate_qr_code(
        self, request_id: str, amount: Decimal, currency: str = "JPY", terminal_id: int = None
    ) -> PayPayQRResponse:
        """Generate a PayPay QR code for payment using SDK"""
        # Convert Decimal to int (JPY minor units)
        amount_minor = int(amount)

        # Create PayPay QR request
        request = PayPayQRRequest(
            merchant_payment_id=request_id,
            amount=amount_minor,
            currency=currency,
            terminal_id=terminal_id,
        )

        try:
            return self._generate_real_qr_code(request)
        except Exception as e:
            # Re-raise if it's already an HTTPException (like 400 from UNAUTHORIZED)
            if isinstance(e, HTTPException):
                raise
            # Otherwise treat as upstream error
            print("Paypay error: " + str(e))
            raise upstream_error("Init payment error")

    def _generate_real_qr_code(self, request: PayPayQRRequest) -> PayPayQRResponse:
        """Generate a PayPay QR code using real SDK"""
        payload = {
            "merchantPaymentId": request.merchant_payment_id,
            "amount": {"amount": request.amount, "currency": request.currency},
            "codeType": request.code_type,
        }

        # Add terminal_id if provided (might be used as storeId)
        if request.terminal_id:
            payload["storeId"] = str(request.terminal_id)

        try:
            response = self.client.Code.create_qr_code(payload)
            print(f"PayPay response: {response}")  # Debug log

            # Check for PayPay API errors
            result_info = response.get("resultInfo", {})
            result_code = result_info.get("code")

            if result_code == "UNAUTHORIZED":
                # Invalid merchant credentials
                error_msg = "PayPay authentication failed"
                print(f"Paypay error: {error_msg}")
                raise bad_request(error_msg)

            elif result_code and result_code != "SUCCESS":
                # Other PayPay errors
                error_msg = f"PayPay API error ({result_code}): {result_info.get('message', 'Unknown error')}"
                print(f"Paypay error: {error_msg}")
                raise bad_request(error_msg)

            # Check if response has valid data
            if not response or not response.get("data"):
                error_msg = f"Invalid PayPay response: {response}"
                print(f"Paypay error: {error_msg}")
                raise upstream_error(error_msg)

            return PayPayQRResponse(
                result_info=PayPayResultInfo(**response.get("resultInfo", {})),
                data=PayPayQRData(**response.get("data", {})),
            )
        except Exception as e:
            if isinstance(e, HTTPException):
                raise  # Re-raise HTTPException as-is
            raise upstream_error(f"PayPay SDK error: {str(e)}")

    async def get_payment_status(self, merchant_payment_id: str) -> dict[str, Any]:
        """Get payment status from PayPay"""
        try:
            response = self.client.Code.get_payment_details(merchant_payment_id)
            data = response.get("data", {})
            return {
                "merchant_payment_id": merchant_payment_id,
                "status": data.get("status", "UNKNOWN"),
                "payment_id": data.get("paymentId"),
            }
        except Exception as e:
            raise upstream_error(f"Failed to get payment status: {str(e)}")

    async def get_payment_details(self, merchant_payment_id: str) -> dict[str, Any]:
        """Get payment details from PayPay API using SDK."""
        try:
            response = self.client.Code.get_payment_details(merchant_payment_id)
            return response
        except Exception as e:
            raise upstream_error(f"Failed to get payment details: {str(e)}")

    async def cancel_payment(self, payment_id: str) -> dict[str, Any]:
        """Cancel a payment using SDK"""
        try:
            return self.client.Payment.cancel_payment(payment_id)
        except Exception as e:
            raise upstream_error(f"Failed to cancel payment: {str(e)}")

    async def refund_payment(
        self, merchant_refund_id: str, payment_id: str, amount: int
    ) -> dict[str, Any]:
        """Refund a payment using SDK"""
        payload = {
            "merchantRefundId": merchant_refund_id,
            "paymentId": payment_id,
            "amount": {"amount": amount, "currency": "JPY"},
        }
        try:
            return self.client.Pending.refund_payment(payload)
        except Exception as e:
            raise upstream_error(f"Failed to refund payment: {str(e)}")

    async def delete_qr_code(self, code_id: str) -> dict[str, Any]:
        """Delete QR code using SDK"""
        try:
            return self.client.Code.delete_qr_code(code_id)
        except Exception as e:
            raise upstream_error(f"Failed to delete QR code: {str(e)}")
