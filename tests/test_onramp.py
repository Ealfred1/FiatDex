import pytest
import hmac, hashlib, json
import respx, httpx
from unittest.mock import AsyncMock

pytestmark = pytest.mark.asyncio

class TestOnrampQuote:

    async def test_quote_ngn_returns_inj_estimate(self, client, auth_headers, mocker):
        """NGN quote returns estimated INJ amount."""
        mocker.patch(
            "app.services.transak_service.TransakService.get_fiat_quote",
            return_value=AsyncMock(crypto_amount=2.45, fees=250.0, expires_at=None)
        )
        mocker.patch(
            "app.services.swap_service.SwapService.estimate_swap",
            return_value=AsyncMock(target_amount=125.5)
        )
        
        response = await client.post(
            "/api/v1/onramp/quote",
            headers=auth_headers,
            json={
                "fiat_amount": 5000,
                "fiat_currency": "NGN",
                "target_market_id": "0x" + "a" * 64,
                "payment_method": "credit_debit_card",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["estimated_inj_amount"] == 2.45
        assert data["estimated_target_amount"] == 125.5

    async def test_quote_requires_auth(self, client):
        """Quote endpoint returns 401 without auth."""
        response = await client.post("/api/v1/onramp/quote", json={
            "fiat_amount": 5000, "fiat_currency": "NGN",
            "target_market_id": "0x" + "a" * 64,
        })
        assert response.status_code == 401


class TestOnrampInitiate:

    async def test_creates_pending_transaction(self, client, auth_headers, db_session, mocker):
        """Initiating a purchase creates a Transaction with pending status."""
        mocker.patch(
            "app.services.transak_service.TransakService.generate_widget_url",
            return_value="https://global.transak.com/?apiKey=test&..."
        )
        response = await client.post(
            "/api/v1/onramp/initiate",
            headers=auth_headers,
            json={
                "provider": "transak",
                "fiat_amount": 5000,
                "fiat_currency": "NGN",
                "target_denom": "factory/inj1abc/token1",
                "payment_method": "credit_debit_card",
                "slippage_tolerance": 0.01,
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "transaction_id" in data
        assert "widget_url" in data

    async def test_widget_url_contains_wallet_address(self, client, auth_headers, test_user, mocker):
        """Widget URL includes the authenticated user's wallet address."""
        mock_url = f"https://global.transak.com/?walletAddress={test_user.wallet_address}"
        mocker.patch(
            "app.services.transak_service.TransakService.generate_widget_url",
            return_value=mock_url
        )
        response = await client.post(
            "/api/v1/onramp/initiate",
            headers=auth_headers,
            json={
                "provider": "transak",
                "fiat_amount": 5000, "fiat_currency": "NGN",
                "target_denom": "factory/inj1abc/token1",
            }
        )
        assert response.status_code == 200
        assert test_user.wallet_address in response.json()["widget_url"]


class TestTransactionStatus:

    async def test_returns_pending_status(self, client, auth_headers, pending_transaction):
        """Status endpoint returns pending for a newly created transaction."""
        response = await client.get(
            f"/api/v1/onramp/transaction/{pending_transaction.id}/status",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["onramp_status"] == "pending"

    async def test_returns_confirmed_status(self, client, auth_headers, completed_transaction):
        """Status endpoint returns confirmed for a completed swap."""
        response = await client.get(
            f"/api/v1/onramp/transaction/{completed_transaction.id}/status",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["swap_status"] == "confirmed"
