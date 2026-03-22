import httpx
from decimal import Decimal
from typing import List, Dict, Any
from app.config import settings

class NotificationService:
    def __init__(self):
        self.expo_url = settings.EXPO_PUSH_TOKEN_BASE

    async def send_swap_confirmed(
        self,
        expo_push_token: str,
        token_symbol: str,
        amount: Decimal,
        tx_hash: str,
    ) -> None:
        """Send 'Your {amount} {symbol} has arrived!' push notification."""
        message = {
            "to": expo_push_token,
            "title": "Swap Confirmed! 🚀",
            "body": f"Your {amount:.4f} {token_symbol} has arrived in your wallet.",
            "data": {"tx_hash": tx_hash, "type": "swap_confirmed"},
            "sound": "default"
        }
        await self._send_to_expo([message])

    async def send_swap_failed(
        self, expo_push_token: str, token_symbol: str, reason: str
    ) -> None:
        """Send swap failure notification."""
        message = {
            "to": expo_push_token,
            "title": "Swap Failed ⚠️",
            "body": f"We couldn't complete your swap to {token_symbol}. Tap for details.",
            "data": {"reason": reason, "type": "swap_failed"},
            "sound": "default"
        }
        await self._send_to_expo([message])

    async def send_price_alert(
        self,
        expo_push_token: str,
        token_symbol: str,
        target_price: Decimal,
        current_price: Decimal,
        condition: str,
    ) -> None:
        """Send price alert notification."""
        condition_str = "risen above" if condition == "above" else "dropped below"
        message = {
            "to": expo_push_token,
            "title": f"{token_symbol} Alert! 📈",
            "body": f"{token_symbol} has {condition_str} your target of ${target_price}.",
            "data": {"symbol": token_symbol, "price": str(current_price), "type": "price_alert"},
            "sound": "default"
        }
        await self._send_to_expo([message])

    async def _send_to_expo(self, messages: List[Dict[str, Any]]) -> None:
        """
        POST to Expo Push API. Handles chunking.
        """
        if not messages:
            return

        # Expo accepts max 100 messages per request
        for i in range(0, len(messages), 100):
            chunk = messages[i : i + 100]
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        self.expo_url,
                        json=chunk,
                        headers={"Content-Type": "application/json"}
                    )
                    resp.raise_for_status()
                    # In production, we'd log delivery receipts here
            except Exception as e:
                # Log error
                print(f"Failed to send notifications: {str(e)}")

notification_service = NotificationService()
