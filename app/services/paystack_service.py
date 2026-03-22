import httpx
import hmac
import hashlib
import json
from app.config import settings
from typing import Optional, Dict, Any, Tuple
from decimal import Decimal

PAYSTACK_BASE_URL = "https://api.paystack.co"

class PaystackService:
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    async def initialize_transaction(self, email: str, amount_fiat: Decimal, currency: str) -> Optional[Dict[str, Any]]:
        """
        Initialize a transaction with Paystack.
        Note: Paystack expects amount in kobo/cents (amount * 100).
        """
        url = f"{PAYSTACK_BASE_URL}/transaction/initialize"
        payload = {
            "email": email,
            "amount": int(amount_fiat * 100),
            "currency": currency.upper(),
            "callback_url": f"{settings.FRONTEND_BASE_URL}/funding/callback",
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=self.headers)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status"):
                        return data.get("data")
                return None
            except Exception:
                return None

    async def verify_transaction(self, reference: str) -> Optional[Dict[str, Any]]:
        """
        Verify a transaction with Paystack using its reference.
        """
        url = f"{PAYSTACK_BASE_URL}/transaction/verify/{reference}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.headers)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status"):
                        return data.get("data")
                return None
            except Exception:
                return None

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify that the webhook request came from Paystack.
        """
        secret = settings.PAYSTACK_WEBHOOK_SECRET or settings.PAYSTACK_SECRET_KEY
        if not secret or secret == "dummy":
            return False
        
        if not signature:
            return False
            
        expected_signature = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha512
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)

    async def get_fiat_to_usd_rate(self, currency: str) -> Decimal:
        """
        Get approximate exchange rate. 
        In production, use a real price feed or Paystack's own conversion if available.
        For now, using hardcoded/mocked rates for African currencies.
        """
        rates = {
            "NGN": Decimal("1600.0"),
            "GHS": Decimal("15.0"),
            "KES": Decimal("130.0"),
            "ZAR": Decimal("19.0"),
        }
        return rates.get(currency.upper(), Decimal("1.0"))

paystack_service = PaystackService()
