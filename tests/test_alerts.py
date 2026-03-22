import pytest
from unittest.mock import MagicMock
from app.models.alert import PriceAlert
from app.models.watchlist import WatchlistItem
from sqlalchemy import select

pytestmark = pytest.mark.asyncio

class TestCreateAlert:

    async def test_creates_alert(self, client, auth_headers):
        """Creating an alert returns the new alert object."""
        response = await client.post(
            "/api/v1/alerts",
            headers=auth_headers,
            json={
                "token_denom": "factory/inj1abc/token1",
                "token_symbol": "TOKEN1",
                "target_price_usd": 2.50,
                "condition": "above",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["token_symbol"] == "TOKEN1"
        assert data["condition"] == "above"
        assert data["is_active"] is True
        assert "id" in data

    async def test_alert_limit_enforced(self, client, auth_headers, db_session, test_user):
        """Cannot create more than 10 active alerts."""
        for i in range(10):
            db_session.add(PriceAlert(
                user_id=test_user.id,
                token_denom=f"factory/inj/t{i}",
                token_symbol=f"T{i}",
                target_price_usd=1.0,
                condition="above",
                is_active=True,
            ))
        await db_session.flush()

        response = await client.post(
            "/api/v1/alerts",
            headers=auth_headers,
            json={
                "token_denom": "factory/inj/t11",
                "token_symbol": "T11",
                "target_price_usd": 1.0,
                "condition": "above",
            }
        )
        assert response.status_code == 400
        assert "Maximum 10 active alerts" in response.json()["detail"]


class TestWatchlist:

    async def test_add_to_watchlist(self, client, auth_headers):
        response = await client.post(
            "/api/v1/alerts/watchlist",
            headers=auth_headers,
            json={"token_denom": "factory/inj/watch", "token_symbol": "WATCH"}
        )
        assert response.status_code == 200

    async def test_duplicate_watchlist_returns_409(self, client, auth_headers, db_session, test_user):
        """Adding same token twice returns 409 Conflict."""
        item = WatchlistItem(
            user_id=test_user.id,
            token_denom="factory/inj/dup",
            token_symbol="DUP"
        )
        db_session.add(item)
        await db_session.flush()

        response = await client.post(
            "/api/v1/alerts/watchlist",
            headers=auth_headers,
            json={"token_denom": "factory/inj/dup", "token_symbol": "DUP"}
        )
        assert response.status_code == 409

    async def test_remove_from_watchlist(self, client, auth_headers, db_session, test_user):
        # Using a URL-safe denom representation if necessary, or just ensure the route handles it
        denom = "factory-inj-rm"
        item = WatchlistItem(
            user_id=test_user.id,
            token_denom=denom,
            token_symbol="RM"
        )
        db_session.add(item)
        await db_session.flush()

        # The route for DELETE is /watchlist/{token_denom}
        # If token_denom contains slashes, it might need encoding or the route should use :path
        response = await client.delete(
            f"/api/v1/alerts/watchlist/{denom}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Verify it's gone
        stmt = select(WatchlistItem).where(WatchlistItem.token_denom == denom)
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is None
