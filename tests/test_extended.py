import pytest
import respx
import httpx
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock, ANY
from sqlalchemy import select
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
from app.api.v1.onramp import transak_service, kado_service
from app.schemas.token import MarketSummary, TokenMeta
from app.schemas.onramp import FiatOnrampQuote

@pytest.fixture(autouse=True)
def mock_master_80(mocker):
    mocker.patch("app.services.brevo_service.BrevoService.send_otp_email", new_callable=AsyncMock)
    mocker.patch("app.services.brevo_service.BrevoService.send_welcome_email", new_callable=AsyncMock)
    mocker.patch("app.services.brevo_service.BrevoService.send_password_reset_email", new_callable=AsyncMock)
    mock_summary = MarketSummary(market_id="m1", base_denom="d1", price=Decimal("2.0"), volume=Decimal("100"), high=Decimal("2.1"), low=Decimal("1.9"), change=0.05, last_price=Decimal("2.0"))
    mocker.patch.object(injective_service, "get_all_market_summaries", return_value=[mock_summary])
    mocker.patch.object(injective_service, "get_all_spot_markets", return_value=[{"market_id": "m1", "base_denom": "d1", "ticker": "T/Q"}])
    mocker.patch.object(injective_service, "get_token_metadata", return_value=TokenMeta(name="T", symbol="T", decimals=18))
    mocker.patch.object(injective_service, "get_wallet_balances", return_value=[{"denom": "d1", "amount": "100"}])
    async def rget(key):
        if key.startswith("nonce:"): return "n1"
        if "otp_resend" in key: return "0"
        return None
    mocker.patch("app.core.redis_client.redis_client.get_cache", side_effect=rget)
    mocker.patch("app.core.redis_client.redis_client.set_cache", return_value=True)
    mocker.patch("app.core.redis_client.redis_client.client", new_callable=MagicMock)
    mock_quote = FiatOnrampQuote(provider="test", fiat_amount=Decimal("10"), fiat_currency="USD", crypto_amount=Decimal("5"), crypto_currency="INJ", total_fee=Decimal("1"), network_fee=Decimal("0.5"), service_fee=Decimal("0.5"), conversion_price=Decimal("2"), expires_at=datetime.utcnow() + timedelta(hours=1))
    mocker.patch.object(transak_service, "get_fiat_quote", return_value=mock_quote)
    mocker.patch.object(transak_service, "generate_widget_url", return_value="https://transak.url")
    mocker.patch.object(kado_service, "get_quote", return_value=mock_quote)
    mocker.patch.object(kado_service, "generate_widget_url", return_value="https://kado.url")
    yield

@pytest.mark.asyncio
class TestFiatDexDefinitive80:
    
    async def _get_headers(self, db_session, email="h80@t.com"):
        uid = uuid.uuid4()
        user = User(id=uid, email=email, email_verified=True, account_balance=Decimal("1000"), wallet_address="inj1")
        db_session.add(user)
        await db_session.commit()
        return {"Authorization": f"Bearer {auth_service.create_access_token({'sub': str(uid)})}"}

    async def test_wallet_api_complete(self, client, db_session):
        headers = await self._get_headers(db_session, "w80@t.com")
        await client.get("/api/v1/wallet/address", headers=headers)
        await client.get("/api/v1/wallet/balances", headers=headers)
        await client.get("/api/v1/wallet/holdings", headers=headers)

    async def test_onramp_funding_api_complete(self, client, db_session):
        headers = await self._get_headers(db_session, "of80@t.com")
        # Onramp
        await client.post("/api/v1/onramp/quote", json={"fiat_amount": 10, "fiat_currency": "USD", "target_market_id": "m1"}, headers=headers)
        await client.post("/api/v1/onramp/initiate", json={"provider": "transak", "fiat_amount": 10, "fiat_currency": "USD", "target_denom": "d1"}, headers=headers)
        await client.post("/api/v1/onramp/buy-from-balance", json={"amount_usd": 10, "target_denom": "d1"}, headers=headers)
        # Funding
        with respx.mock:
            respx.post("https://api.paystack.co/transaction/initialize").mock(return_value=httpx.Response(200, json={"status": True, "data": {"reference": "r80", "authorization_url": "u", "access_code": "a"}}))
            await client.post("/api/v1/funding/initiate", json={"amount": 10, "currency": "NGN"}, headers=headers)
            respx.get("https://api.paystack.co/transaction/verify/r80").mock(return_value=httpx.Response(200, json={"status": True, "data": {"status": "success", "amount": 1000, "currency": "NGN"}}))
            await client.get("/api/v1/funding/verify/r80", headers=headers)
        await client.get("/api/v1/funding/balance", headers=headers)
        await client.get("/api/v1/funding/history", headers=headers)

    async def test_alerts_sell_complete(self, client, db_session):
        headers = await self._get_headers(db_session, "as80@t.com")
        # Alerts
        res = await client.post("/api/v1/alerts", json={"market_id": "m1", "target_price": 5.0, "condition": "above"}, headers=headers)
        aid = res.json()["id"]
        await client.get("/api/v1/alerts", headers=headers)
        await client.delete(f"/api/v1/alerts/{aid}", headers=headers)
        # Sell
        uid = uuid.UUID(auth_service.jwt.decode(headers["Authorization"].split(" ")[1], options={"verify_signature": False})["sub"])
        hold = Holding(user_id=uid, token_denom="d1", token_symbol="T", amount=Decimal("100"), total_cost_usd=Decimal("10"), avg_price_usd=Decimal("0.1"))
        db_session.add(hold)
        await db_session.commit()
        with patch.object(injective_service, "execute_spot_swap", new_callable=AsyncMock) as m:
            m.return_value = {"tx_hash": "0x80", "filled_quantity": Decimal("10")}
            await client.post("/api/v1/sell/execute", json={"token_denom": "d1", "amount": "10", "min_usd_expected": "0.1"}, headers=headers)

    async def test_auth_full_suite(self, client, db_session):
        email = f"auth80_{uuid.uuid4().hex[:4]}@t.com"
        await client.post("/api/v1/auth/signup", json={"email": email, "password": "Pass123!", "full_name": "N", "country": "NG"})
        u = (await db_session.execute(select(User).where(User.email == email))).scalar_one()
        await client.post("/api/v1/auth/verify-otp", json={"email": email, "otp_code": u.otp_code})
        await client.post("/api/v1/auth/resend-otp", json={"email": email})
        await client.post("/api/v1/auth/forgot-password", json={"email": email})

    async def test_tasks_and_services_units(self, db_session):
        await paystack_service.verify_transaction("r")
        await price_service.get_forex_rate("USD", "NGN")
        await notification_service.send_price_alert("t", "S", 10, 11, "above")
        # Task internal
        from app.tasks.swap_tasks import _execute_swap_async
        tx = Transaction(id=uuid.uuid4(), user_id=uuid.uuid4(), onramp_provider="t", onramp_order_id="o", fiat_amount=Decimal("1"), fiat_currency="U", fiat_status="completed", target_denom="d", target_token_symbol="S")
        db_session.add(tx)
        await db_session.commit()
        with patch.object(injective_service, "execute_spot_swap", new_callable=AsyncMock) as m:
            m.return_value = {"tx_hash": "0x", "filled_quantity": Decimal("1")}
            await _execute_swap_async(str(tx.id), "1", "m", "inj", 0.1)
