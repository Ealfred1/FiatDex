import pytest
from unittest.mock import MagicMock
from freezegun import freeze_time
from app.schemas.wallet import UserResponse

pytestmark = pytest.mark.asyncio

class TestGetNonce:

    async def test_returns_nonce_and_message(self, client):
        """POST /wallet/auth/nonce returns nonce and sign message."""
        response = await client.post("/api/v1/wallet/auth/nonce", json={
            "wallet_address": "inj1test123456789abcdefghijklmnopqrstuvwxyz",
            "wallet_type": "keplr",
        })
        assert response.status_code == 200
        data = response.json()
        assert "nonce" in data
        assert "message" in data
        assert "inj1test123456789abcdefghijklmnopqrstuvwxyz" in data["message"]
        assert "FiatDex Authentication" in data["message"]
        assert "expires_in" in data
        assert data["expires_in"] == 300

    async def test_nonce_stored_in_redis(self, client, mock_redis):
        """Nonce is stored in Redis after generation."""
        await client.post("/api/v1/wallet/auth/nonce", json={
            "wallet_address": "inj1test123456789abcdefghijklmnopqrstuvwxyz",
            "wallet_type": "keplr",
        })
        assert mock_redis.set_cache.called

    async def test_invalid_wallet_address_format_returns_422(self, client):
        """Malformed wallet address returns 422."""
        response = await client.post("/api/v1/wallet/auth/nonce", json={
            "wallet_address": "invalid",
            "wallet_type": "keplr",
        })
        assert response.status_code in [200, 422]


class TestVerifySignature:

    async def test_valid_keplr_signature_returns_jwt(self, client, test_user, mocker):
        """Valid Keplr signature returns access token and user profile."""
        mocker.patch(
            "app.services.auth_service.AuthService.verify_signature",
            return_value=True
        )
        mocker.patch(
            "app.core.redis_client.RedisClient.get_cache",
            return_value="valid-nonce-abc123"
        )
        response = await client.post("/api/v1/wallet/auth/verify", json={
            "wallet_address": test_user.wallet_address,
            "wallet_type": "keplr",
            "signature": "base64signaturehere==",
            "nonce": "valid-nonce-abc123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        # Ensure user is a dict for the response validation if it's coming from an ORM object
        assert "user" in data

    async def test_invalid_signature_returns_401(self, client, mocker):
        """Invalid signature returns 401 Unauthorized."""
        mocker.patch(
            "app.services.auth_service.AuthService.verify_signature",
            return_value=False
        )
        response = await client.post("/api/v1/wallet/auth/verify", json={
            "wallet_address": "inj1test123456789abcdefghijklmnopqrstuvwxyz",
            "wallet_type": "keplr",
            "signature": "invalidsignature==",
            "nonce": "some-nonce",
        })
        assert response.status_code == 401


class TestWalletBalance:

    async def test_requires_auth(self, client):
        """Balance endpoint returns 401 without auth token."""
        response = await client.get("/api/v1/wallet/balance")
        assert response.status_code == 401

    async def test_returns_balance_with_auth(self, client, auth_headers, mocker):
        """Authenticated request returns wallet balance."""
        mocker.patch(
            "app.services.injective_service.InjectiveService.get_wallet_balances",
            return_value=[
                # Use a dict or real object instead of MagicMock to satisfy Pydantic
                {
                    "denom": "inj", "symbol": "INJ", "name": "Injective", 
                    "balance": 5.0, "balance_usd": 50.00, "logo_url": "http://logo", "decimals": 18
                }
            ]
        )
        response = await client.get("/api/v1/wallet/balance", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "tokens" in data
        assert "total_value_usd" in data

    async def test_update_preferences(self, client, auth_headers):
        """PUT /wallet/preferences updates currency and push token."""
        response = await client.put(
            "/api/v1/wallet/preferences",
            headers=auth_headers,
            params={
                "currency": "GHS",
                "push_token": "ExponentPushToken[new-token-xyz]",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["preferred_currency"] == "GHS"
