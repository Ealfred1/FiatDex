import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

@pytest.mark.asyncio
async def test_get_tokens(client: AsyncClient):
    response = await client.get("/api/v1/tokens")
    assert response.status_code == 200
    data = response.json()
    assert "tokens" in data
    assert isinstance(data["tokens"], list)

@pytest.mark.asyncio
async def test_auth_flow_nonce(client: AsyncClient):
    payload = {
        "wallet_address": "inj1px7l6v4xvzkp9v3j8y9x5h9s2m7r6v4xvzkp9v",
        "wallet_type": "metamask"
    }
    response = await client.post("/api/v1/wallet/auth/nonce", json=payload)
    assert response.status_code == 200
    assert "nonce" in response.json()
    assert "message" in response.json()

@pytest.mark.asyncio
async def test_protected_route_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/wallet/me")
    assert response.status_code == 401
