import hmac
import hashlib
from decimal import Decimal
from typing import Dict, Any, Optional
import httpx
from urllib.parse import urlencode
from datetime import datetime

from app.config import settings
from app.schemas.onramp import FiatQuote, TransakOrderResult

class TransakService:
    def __init__(self):
        self.api_key = settings.TRANSAK_API_KEY
        self.secret_key = settings.TRANSAK_SECRET_KEY
        self.base_url = (
            "https://api.transak.com" 
            if settings.TRANSAK_ENVIRONMENT == "PRODUCTION" 
            else "https://staging-api.transak.com"
        )
        self.widget_url_base = (
            "https://global.transak.com"
            if settings.TRANSAK_ENVIRONMENT == "PRODUCTION"
            else "https://staging-global.transak.com"
        )

    async def get_fiat_quote(
        self,
        fiat_amount: Decimal,
        fiat_currency: str,
        crypto_currency: str = "INJ",
        payment_method: str = "credit_debit_card",
    ) -> FiatQuote:
        """
        Get a real-time quote for a fiat → INJ purchase.
        """
        params = {
            "partnerApiKey": self.api_key,
            "fiatCurrency": fiat_currency,
            "cryptoCurrency": crypto_currency,
            "fiatAmount": float(fiat_amount),
            "paymentMethod": payment_method,
            "network": "injective"
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/api/v2/currencies/price", params=params)
            resp.raise_for_status()
            data = resp.json()["response"]
            
            return FiatQuote(
                provider="transak",
                fiat_amount=fiat_amount,
                fiat_currency=fiat_currency,
                crypto_amount=Decimal(data["cryptoAmount"]),
                crypto_currency=crypto_currency,
                total_fee=Decimal(data["totalFee"]),
                network_fee=Decimal(data["networkFee"]),
                service_fee=Decimal(data["transakFee"]),
                conversion_price=Decimal(data["conversionPrice"]),
                expires_at=datetime.utcnow() # Transak doesn't always provide expiry in this call
            )

    async def generate_widget_url(
        self,
        fiat_amount: Decimal,
        fiat_currency: str,
        wallet_address: str,
        order_id: str,
    ) -> str:
        """
        Generate a Transak widget URL.
        """
        params = {
            "apiKey": self.api_key,
            "fiatCurrency": fiat_currency,
            "defaultFiatAmount": float(fiat_amount),
            "cryptoCurrencyCode": "INJ",
            "walletAddress": wallet_address,
            "partnerOrderId": order_id,
            "network": "injective",
            "themeColor": "000000", # Example theme
            "environment": settings.TRANSAK_ENVIRONMENT
        }
        
        query_string = urlencode(params)
        return f"{self.widget_url_base}?{query_string}"

    async def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify that an incoming webhook is genuinely from Transak.
        """
        if not signature:
            return False
            
        expected_sig = hmac.new(
            self.secret_key.encode("utf-8"),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_sig, signature)

    async def process_order_completed_webhook(self, data: dict) -> TransakOrderResult:
        """
        Process a completed order webhook from Transak.
        """
        webhook_data = data.get("webhookData", {})
        return TransakOrderResult(
            order_id=webhook_data.get("id"),
            status=webhook_data.get("status"),
            fiat_amount=Decimal(webhook_data.get("fiatAmount", 0)),
            crypto_amount=Decimal(webhook_data.get("cryptoAmount", 0)),
            wallet_address=webhook_data.get("walletAddress"),
            tx_hash=webhook_data.get("transactionHash")
        )

transak_service = TransakService()
