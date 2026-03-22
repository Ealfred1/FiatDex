import pytest
from unittest.mock import MagicMock
from app.schemas.token import TokenBalance

pytestmark = pytest.mark.asyncio

class TestGetPortfolio:

    async def test_requires_auth(self, client):
        response = await client.get("/api/v1/portfolio")
        assert response.status_code == 401

    async def test_returns_portfolio_structure(self, client, auth_headers, mocker):
        """Portfolio returns holdings with total values."""
        # Return real TokenBalance objects/dicts to satisfy Pydantic
        mocker.patch(
            "app.services.injective_service.InjectiveService.get_wallet_balances",
            return_value=[
                TokenBalance(
                    denom="inj", symbol="INJ", name="Injective", 
                    logo_url="http://logo", balance=5.0, balance_usd=50.0, decimals=18
                )
            ]
        )
        response = await client.get("/api/v1/portfolio", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_value_usd" in data
        assert "holdings" in data


class TestGetTransactions:

    async def test_returns_transaction_list(self, client, auth_headers, completed_transaction):
        """Transactions endpoint returns list of user's transactions."""
        response = await client.get("/api/v1/portfolio/transactions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert data[0]["onramp_status"] == "completed"
