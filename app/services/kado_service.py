from decimal import Decimal
from typing import Optional
import httpx
from datetime import datetime, timezone
from app.config import settings
from app.schemas.onramp import FiatOnrampQuote, KadoOrderResult

class KadoService:
    def __init__(self):
        self.api_key = settings.KADO_API_KEY
        self.base_url = "https://api.kado.money/v1"

    async def get_quote(self, fiat_amount: Decimal, fiat_currency: str, crypto_currency: str = "INJ") -> FiatOnrampQuote:
        """
        Get a quote from Kado API.
        """
        # Note: Kado API details vary, this is a placeholder based on typical Kado integration
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/quote", 
                params={
                    "apiKey": self.api_key,
                    "fiatAmount": float(fiat_amount),
                    "fiatCurrency": fiat_currency,
                    "cryptoCurrency": crypto_currency,
                    "blockchain": "injective"
                }
            )
            data = resp.json()["data"]
            
            return FiatOnrampQuote(
                provider="kado",
                fiat_amount=fiat_amount,
                fiat_currency=fiat_currency,
                crypto_amount=Decimal(data["cryptoAmount"]),
                crypto_currency=crypto_currency,
                total_fee=Decimal(data["fee"]),
                network_fee=Decimal(data["networkFee"]),
                service_fee=Decimal(data["serviceFee"]),
                conversion_price=Decimal(data["conversionPrice"]),
                expires_at=datetime.utcnow()
            )

    async def generate_widget_url(
        self, fiat_amount: Decimal, fiat_currency: str, wallet_address: str
    ) -> str:
        """
        Generate Kado widget URL.
        """
        params = {
            "apiKey": self.api_key,
            "onToAddress": wallet_address,
            "onPayAmount": float(fiat_amount),
            "onPayCurrency": fiat_currency,
            "onRevCurrency": "INJ",
            "network": "INJECTIVE",
            "product": "BUY"
        }
        # In actual Kado, this might involve a signed request or simple URL
        import urllib.parse
        query = urllib.parse.urlencode(params)
        return f"https://app.kado.money/?{query}"

    async def process_webhook(self, data: dict) -> KadoOrderResult:
        """
        Handle Kado order completion webhook.
        """
        return KadoOrderResult(
            order_id=data.get("id"),
            status=data.get("status"),
            fiat_amount=Decimal(data.get("fiatAmount", 0)),
            crypto_amount=Decimal(data.get("cryptoAmount", 0)),
            wallet_address=data.get("walletAddress"),
            tx_hash=data.get("txHash")
        )

kado_service = KadoService()
