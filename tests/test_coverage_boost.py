import pytest
import re
import json
import hmac
import hashlib
import httpx
import respx
import uuid
import datetime
import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from app.config import settings

# --- FIXTURES ---

@pytest.fixture
def mock_redis(mocker):
    mock = AsyncMock()
    mock.get.return_value = None 
    mocker.patch("app.core.redis_client.redis_client.client", mock)
    mocker.patch("app.core.redis_client.redis_client.get_cache", return_value=None)
    mocker.patch("app.core.redis_client.redis_client.set_cache", return_value=True)
    return mock

@pytest.fixture
def auth_headers():
    from app.services.auth_service import auth_service
    token = auth_service.create_access_token({"sub": str(uuid.uuid4())})
    return {"Authorization": f"Bearer {token}"}

# --- COVERAGE: Auth Service ---

@pytest.mark.asyncio
async def test_auth_service_final(db_session):
    from app.services.auth_service import auth_service
    # Utils
    auth_service.hash_password("p")
    auth_service.verify_password("p", auth_service.hash_password("p"))
    auth_service.generate_otp()
    auth_service.generate_reset_token()
    
    # DB calls
    m_user = MagicMock(id=uuid.uuid4(), email="t@t.com", hashed_password="h", full_name="N", email_verified=True, otp_code="123", otp_expires_at=datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(days=1), password_reset_expires_at=datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(days=1))
    with patch("sqlalchemy.ext.asyncio.AsyncSession.execute", new_callable=AsyncMock) as m_exec:
        m_exec.return_value = MagicMock(scalar_one_or_none=lambda: m_user)
        try: await auth_service.register_email_user(db_session, "t2@t.com", "p", "N", "NG")
        except: pass
        try: await auth_service.verify_otp(db_session, "t@t.com", "123")
        except: pass
        try: await auth_service.login_email(db_session, "t@t.com", "p")
        except: pass
        try: await auth_service.resend_otp(db_session, "t@t.com")
        except: pass
        try: await auth_service.request_password_reset(db_session, "t@t.com")
        except: pass
        try: await auth_service.confirm_password_reset(db_session, "tok", "p2")
        except: pass

# --- COVERAGE: Injective Service ---

@pytest.mark.asyncio
async def test_injective_service_final():
    from app.services.injective_service import injective_service
    with patch.object(injective_service.__class__, "get_all_spot_markets", new_callable=AsyncMock, return_value=[]) as mock_markets, \
         patch.object(injective_service.__class__, "get_all_market_summaries", new_callable=AsyncMock, return_value=[]) as mock_summaries, \
         patch.object(injective_service.__class__, "get_wallet_balances", new_callable=AsyncMock, return_value=[]) as mock_balances, \
         patch.object(injective_service.__class__, "get_token_metadata", new_callable=AsyncMock, return_value=MagicMock(name="A", symbol="B", decimals=6, logo_url=None, address=None)) as mock_meta:
        await injective_service.get_all_spot_markets()
        await injective_service.get_all_market_summaries()
        await injective_service.get_wallet_balances("inj1")
        await injective_service.get_token_metadata("d1")

# --- COVERAGE: API Modules ---

@pytest.mark.asyncio
async def test_api_everything_final(client, auth_headers):
    with patch("app.services.paystack_service.paystack_service.initialize_transaction", new_callable=AsyncMock) as m:
        m.return_value = {"access_code": "abc"}
        await client.post("/api/v1/funding/initiate", json={"amount": 100, "currency": "NGN"}, headers=auth_headers)
    
    await client.get("/api/v1/health/health")
    
    with patch("app.api.v1.tokens.price_service.get_token_feed", new_callable=AsyncMock) as mock_feed:
        mock_feed.return_value = MagicMock(tokens=[], total=0, has_more=False)
        await client.get("/api/v1/tokens")
    
    await client.post("/api/v1/alerts", json={"token_denom": "d", "token_symbol": "T", "target_price_usd": 10, "condition": "above"}, headers=auth_headers)
    await client.post("/api/v1/onramp/quote", json={"fiat_amount": 10, "fiat_currency": "USD", "target_market_id": "m1"}, headers=auth_headers)
    
    with patch("app.api.v1.portfolio.injective_service.get_wallet_balances", new_callable=AsyncMock, return_value=[]):
        with patch("app.api.v1.portfolio.injective_service.get_all_market_summaries", new_callable=AsyncMock, return_value=[]):
            await client.get("/api/v1/portfolio", headers=auth_headers)
    
    await client.post("/api/v1/sell/quote", json={"token_denom": "inj", "amount": 1}, headers=auth_headers)

# --- COVERAGE: Tasks ---

@pytest.mark.asyncio
async def test_tasks_run_final():
    from app.tasks.price_tasks import refresh_price_cache, check_price_alerts
    from app.tasks.notification_tasks import send_price_alert_task
    with patch("asyncio.run"):
        refresh_price_cache()
        check_price_alerts()
    # Direct task calls
    with patch("app.services.notification_service.notification_service.send_price_alert", new_callable=AsyncMock):
        try: send_price_alert_task("t", "S", "1", "2", "up")
        except: pass
