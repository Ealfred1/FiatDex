import pytest
from unittest.mock import AsyncMock, MagicMock
from app.api.v1.health import HealthResponse

class TestHealthEndpoint:

    async def test_health_returns_200_when_all_ok(self, client, mock_redis, mocker):
        """Health endpoint returns 200 with all checks passing."""
        # Mock InjectiveService instance methods
        mocker.patch("app.api.v1.health.injective_service.get_all_market_summaries", return_value=[])
        
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    async def test_health_returns_503_when_db_down(self, client, mock_redis, mocker):
        """Health endpoint returns 503 when database is unreachable."""
        # Patch the check_database function or the session execution
        mocker.patch("app.api.v1.health.AsyncSession.execute", side_effect=Exception("DB down"))
        
        response = await client.get("/api/v1/health")
        # Ensure the endpoint actually returns 503 on exception
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"

    async def test_health_returns_503_when_redis_down(self, client, mock_redis, mocker):
        """Health endpoint returns 503 when Redis is unreachable."""
        mocker.patch.object(mock_redis.client, "ping", side_effect=Exception("Redis down"))
        
        response = await client.get("/api/v1/health")
        assert response.status_code == 503

    async def test_health_does_not_require_auth(self, client):
        """Health endpoint is publicly accessible — no auth header needed."""
        response = await client.get("/api/v1/health")
        assert response.status_code != 401
