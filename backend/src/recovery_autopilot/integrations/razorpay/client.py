"""Typed Razorpay Gateway client with explicit mode isolation (Synthetic vs. Test Mode)."""

import asyncio
import logging
import uuid
from typing import Any, Dict, Optional, Protocol, runtime_checkable

import httpx

logger = logging.getLogger("recovery_autopilot.integrations.razorpay.client")


class RazorpayGatewayError(Exception):
    """Exception raised for Razorpay gateway errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, is_retryable: bool = False, details: Any = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.is_retryable = is_retryable
        self.details = details


@runtime_checkable
class RazorpayGatewayClient(Protocol):
    """Asynchronous protocol for Razorpay operations."""

    async def create_payment_link(
        self,
        amount_paise: int,
        currency: str,
        description: str,
        customer_name: str,
        customer_email: str,
        customer_phone: str = "",
        notes: Optional[Dict[str, Any]] = None,
        idempotency_key: str = "",
    ) -> Dict[str, Any]:
        """Create a Razorpay payment link."""
        ...


class SyntheticRazorpayClient:
    """Local simulation client with zero network calls and deterministic IDs."""

    def __init__(self):
        self.mode = "synthetic"

    async def create_payment_link(
        self,
        amount_paise: int,
        currency: str,
        description: str,
        customer_name: str,
        customer_email: str,
        customer_phone: str = "",
        notes: Optional[Dict[str, Any]] = None,
        idempotency_key: str = "",
    ) -> Dict[str, Any]:
        sim_id = f"plink_syn_{uuid.uuid4().hex[:12]}"
        sim_url = f"https://rzp.io/i/syn_{sim_id[10:]}"
        return {
            "id": sim_id,
            "short_url": sim_url,
            "amount": amount_paise,
            "currency": currency,
            "status": "created",
            "notes": notes or {},
            "mode": "synthetic",
        }


class GenuineRazorpayTestClient:
    """Live test-mode client communicating strictly with Razorpay test APIs."""

    def __init__(self, key_id: str, key_secret: str, timeout_seconds: float = 10.0):
        if not key_id.startswith("rzp_test_"):
            raise ValueError("GenuineRazorpayTestClient only accepts rzp_test_ keys. Live keys are rejected.")
        self.key_id = key_id
        self.key_secret = key_secret
        self.timeout = timeout_seconds
        self.base_url = "https://api.razorpay.com/v1"

    async def create_payment_link(
        self,
        amount_paise: int,
        currency: str,
        description: str,
        customer_name: str,
        customer_email: str,
        customer_phone: str = "",
        notes: Optional[Dict[str, Any]] = None,
        idempotency_key: str = "",
    ) -> Dict[str, Any]:
        """Create payment link on Razorpay with retry backoff for 5xx network errors."""
        endpoint = f"{self.base_url}/payment_links"
        payload = {
            "amount": amount_paise,
            "currency": currency,
            "accept_partial": False,
            "description": description,
            "customer": {
                "name": customer_name,
                "email": customer_email,
                "contact": customer_phone,
            },
            "notes": notes,
        }
        headers = {
            "Content-Type": "application/json",
            "X-Razorpay-Idempotency-Key": idempotency_key,
        }

        # Up to 3 attempts with exponential backoff on 5xx/network errors
        max_attempts = 3
        last_err = None

        for attempt in range(1, max_attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout, auth=(self.key_id, self.key_secret)) as client:
                    resp = await client.post(endpoint, json=payload, headers=headers)

                    if resp.status_code in (200, 201):
                        data = resp.json()
                        return {
                            "id": data.get("id"),
                            "short_url": data.get("short_url"),
                            "amount": data.get("amount", amount_paise),
                            "currency": data.get("currency", currency),
                            "status": data.get("status", "created"),
                            "notes": notes,
                            "mode": "razorpay_test",
                        }

                    # Non-retryable 4xx client errors
                    if 400 <= resp.status_code < 500:
                        err_data = resp.json().get("error", {})
                        desc = err_data.get("description") or resp.text
                        raise RazorpayGatewayError(
                            f"Razorpay Client Error ({resp.status_code}): {desc}",
                            status_code=resp.status_code,
                            is_retryable=False,
                            details=err_data,
                        )

                    # 5xx server errors are retryable
                    last_err = RazorpayGatewayError(f"Razorpay Server Error ({resp.status_code})", status_code=resp.status_code, is_retryable=True)

            except (httpx.RequestError, httpx.TimeoutException) as exc:
                last_err = RazorpayGatewayError(f"Network error communicating with Razorpay: {str(exc)}", is_retryable=True)

            if attempt < max_attempts:
                await asyncio.sleep(0.5 * (2 ** (attempt - 1)))

        raise last_err or RazorpayGatewayError("Payment link generation failed after retries.")
