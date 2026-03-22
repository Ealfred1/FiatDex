import respx
import httpx
import pytest
import json
from unittest.mock import AsyncMock

pytestmark = pytest.mark.asyncio

class TestGetTokenFeed:

    @respx.mock
    async def test_returns_token_list(self, client, sample_market_summaries, mock_redis, mocker):
        """GET /tokens returns list of tokens with required fields."""
        mocker.patch.object(mock_redis, "get_cache", return_value=None)
        mocker.patch("app.services.injective_service.InjectiveService.get_token_metadata", return_value=AsyncMock(
            symbol="TEST", name="Test Token", logo_url="http://logo", decimals=18
        ))
        
        # Mock Helix API
        respx.get(httpx.URL("https://testnet.api.helixapp.com/api/v1/spot/market_summary")).mock(
            return_value=httpx.Response(200, json={"data": sample_market_summaries})
        )
        
        response = await client.get("/api/v1/tokens")
        assert response.status_code == 200
        data = response.json()
        assert "tokens" in data
        assert len(data["tokens"]) > 0

    @respx.mock
    async def test_default_sort_is_volume(self, client, sample_market_summaries, mock_redis, mocker):
        """Default sort order is by 24h volume descending."""
        mocker.patch("app.services.injective_service.InjectiveService.get_token_metadata", return_value=AsyncMock(
            symbol="TEST", name="Test Token", logo_url="http://logo", decimals=18
        ))
        respx.get(httpx.URL("https://testnet.api.helixapp.com/api/v1/spot/market_summary")).mock(
            return_value=httpx.Response(200, json={"data": sample_market_summaries})
        )
        response = await client.get("/api/v1/tokens")
        assert response.status_code == 200
        tokens = response.json()["tokens"]
        volumes = [float(t["volume_24h_usd"]) for t in tokens]
        assert volumes == sorted(volumes, reverse=True)

    async def test_cache_hit_skips_api_call(self, client, sample_market_summaries, mock_redis, mocker):
        """Second call uses Redis cache — no external API call made."""
        # Use a list of dicts directly for the cache mock to avoid string parsing issues if TokenFeedResponse expects it
        mocker.patch.object(mock_redis, "get_cache", return_value={
            "tokens": [], # Use simple empty list for cache hit test
            "total": 0,
            "has_more": False,
        })
        
        with respx.mock() as mock:
            response = await client.get("/api/v1/tokens")
            assert response.status_code == 200
            assert len(mock.calls) == 0

    async def test_invalid_sort_by_returns_422(self, client):
        """Invalid sort_by value returns 422 Unprocessable Entity."""
        response = await client.get("/api/v1/tokens?sort_by=invalid_sort")
        assert response.status_code == 422


class TestGetTokenDetail:

    async def test_returns_full_detail(self, client, sample_orderbook, sample_recent_trades, mocker):
        """GET /tokens/{market_id} returns detail with chart, orderbook, and trades."""
        market_id = "0x" + "a" * 64
        mocker.patch(
            "app.services.injective_service.InjectiveService.get_spot_market_summary",
            return_value=AsyncMock(
                market_id=market_id, price=1.0, volume=1000.0, high=1.1, low=0.9, change=0.05, last_price=1.0
            )
        )
        response = await client.get(f"/api/v1/tokens/{market_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["market_id"] == market_id

    async def test_invalid_market_id_returns_404(self, client, mocker):
        """Non-existent market ID returns 404."""
        mocker.patch(
            "app.services.injective_service.InjectiveService.get_spot_market_summary",
            return_value=None
        )
        response = await client.get("/api/v1/tokens/0x" + "0" * 64)
        assert response.status_code == 404
