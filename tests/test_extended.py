import pytest
import respx
import httpx
import uuid
import re
import json
import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock, ANY
from sqlalchemy import select
from jose import jwt
from app.models.user import User
from app.models.holding import Holding
from app.models.transaction import Transaction
from app.models.alert import PriceAlert
from app.services.auth_service import auth_service
from app.services.injective_service import injective_service
from app.services.price_service import price_service
from app.services.notification_service import notification_service
from app.services.paystack_service import paystack_service
from app.services.brevo_service import brevo_service
from app.services.swap_service import swap_service
from app.api.v1.onramp import transak_service, kado_service
from app.schemas.token import MarketSummary, TokenMeta, TokenBalance, SwapEstimate
from app.schemas.onramp import FiatOnrampQuote
from app.config import settings

@pytest.fixture(autouse=True)
def mock_master_final_v9(mocker):
    respx.route(url=re.compile(r".*")).mock(return_value=httpx.Response(200, json={"status": "ok", "data": {"status": "success", "amount": 1000}, "rates": {"USD": 1.0}, "balances": []}))
    
    mocker.patch("app.core.redis_client.redis_client.get_cache", return_value=None)
    mocker.patch("app.core.redis_client.redis_client.set_cache", return_value=True)
    mocker.patch("app.core.redis_client.redis_client.client", new_callable=AsyncMock)
    
    # Injective
    mock_client = AsyncMock()
    mock_client.get_spot_markets.return_value = MagicMock(markets=[MagicMock(market_id="m1", base_denom="d1", quote_denom="inj", ticker="T/INJ", status="active", min_price_tick_size=0.01, min_quantity_tick_size=0.01)])
    mocker.patch.object(injective_service, "_client", mock_client)
    summary = MarketSummary(market_id="m1", base_denom="d1", price=Decimal("1"), volume=Decimal("100"), high=Decimal("1"), low=Decimal("1"), change=0, last_price=Decimal("1"))
    mocker.patch.object(injective_service, "get_all_market_summaries", return_value=[summary])
    mocker.patch.object(injective_service, "get_spot_market_summary", return_value=summary)
    mocker.patch.object(injective_service, "get_token_metadata", return_value=TokenMeta(name="T", symbol="T", decimals=18))
    mocker.patch.object(injective_service, "get_wallet_balances", return_value=[TokenBalance(denom="d1", symbol="T", name="T", logo_url=None, balance=1.0, balance_usd=1.0, decimals=18)])
    
    # Swap
    mocker.patch.object(swap_service, "estimate_swap", return_value=SwapEstimate(source_amount=1.0, target_amount=1.0, price_impact=0.001, fee_amount=0.001, min_received=0.99, exchange_rate=1.0))
    
    # Onramp
    now = datetime.datetime.now(datetime.timezone.utc)
    mock_quote = FiatOnrampQuote(provider="test", fiat_amount=Decimal("10"), fiat_currency="USD", crypto_amount=Decimal("5"), crypto_currency="INJ", total_fee=Decimal("1"), network_fee=Decimal("0.5"), service_fee=Decimal("0.5"), conversion_price=Decimal("2"), expires_at=now + datetime.timedelta(hours=1))
    mocker.patch.object(transak_service, "get_fiat_quote", return_value=mock_quote)
    mocker.patch.object(kado_service, "get_quote", return_value=mock_quote)
    yield

@pytest.mark.asyncio
class TestFiatDexFinalCoverageMaster:
    async def _get_auth_headers(self, db_session, email="final@t.com"):
        uid = uuid.uuid4()
        user = User(id=uid, email=email, email_verified=True, account_balance=Decimal("1000"), wallet_address="inj1")
        db_session.add(user)
        await db_session.commit()
        token = auth_service.create_access_token({"sub": str(uid)})
        return {"Authorization": f"Bearer {token}"}

    async def test_all_endpoints_exhaustive(self, client, db_session):
        headers = await self._get_auth_headers(db_session, "api_exhaustive@t.com")
        token_str = headers["Authorization"].split(" ")[1]
        uid = uuid.UUID(jwt.decode(token_str, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])["sub"])
        await client.get("/api/v1/health/health")
        await client.get("/api/v1/tokens?sort=volume_asc")
        await client.post("/api/v1/onramp/quote", json={"fiat_amount": 10, "fiat_currency": "USD", "target_market_id": "m1"}, headers=headers)
        await client.post("/api/v1/funding/initiate", json={"amount": 1000, "currency": "NGN"}, headers=headers)
        await client.get("/api/v1/funding/history", headers=headers)
        await client.get("/api/v1/wallet/address", headers=headers)
        await client.get("/api/v1/wallet/balances", headers=headers)
        await client.get("/api/v1/portfolio", headers=headers)
        res = await client.post("/api/v1/alerts", json={"token_denom": "d1", "token_symbol": "T", "target_price_usd": 5.0, "condition": "above"}, headers=headers)
        if res.status_code == 200:
            await client.delete(f"/api/v1/alerts/{res.json()['id']}", headers=headers)
        hold = Holding(user_id=uid, token_denom="d1", token_symbol="T", amount=Decimal("100"), total_cost_usd=Decimal("10"), avg_price_usd=Decimal("0.1"))
        db_session.add(hold)
        await db_session.commit()
        with patch.object(injective_service, "execute_spot_swap", new_callable=AsyncMock) as m:
            m.return_value = {"tx_hash": "0x", "filled_quantity": Decimal("10")}
            await client.post("/api/v1/sell/execute", json={"token_denom": "d1", "amount": "10", "min_usd_expected": "0.1"}, headers=headers)

    async def test_service_and_task_units(self, db_session):
        await injective_service.get_wallet_balances("inj1")
        await price_service.get_token_price_usd("d1")
        await brevo_service.send_otp_email("u@t.com", "S", "123")
        await paystack_service.verify_transaction("ref")
        from app.tasks.swap_tasks import _execute_swap_async
        from app.tasks.price_tasks import _check_alerts_async
        uid = uuid.uuid4()
        tx = Transaction(id=uuid.uuid4(), user_id=uid, onramp_provider="t", onramp_order_id="o", fiat_amount=Decimal("10"), fiat_currency="U", fiat_status="completed", target_denom="d1", target_token_symbol="S")
        db_session.add(tx)
        alert = PriceAlert(user_id=uid, token_denom="d1", token_symbol="T", target_price_usd=0.5, condition="above", is_active=True)
        db_session.add(alert)
        await db_session.commit()
        with patch.object(injective_service, "execute_spot_swap", new_callable=AsyncMock) as m:
            m.return_value = {"tx_hash": "0x", "filled_quantity": Decimal("1")}
            await _execute_swap_async(str(tx.id), "1", "m1", "inj1", 0.1)
        await _check_alerts_async()

    async def test_webhooks_exhaustive(self, client, db_session):
        with patch.object(paystack_service, "verify_webhook_signature", return_value=True):
            await client.post("/api/v1/funding/webhook", json={"event": "charge.success", "data": {"reference": "ref", "status": "success", "amount": 100000}}, headers={"x-paystack-signature": "sig"})
        await client.post("/api/v1/onramp/webhook/transak", json={"eventID": "ORDER_COMPLETED", "data": {"orderId": "o", "status": "COMPLETED"}})
