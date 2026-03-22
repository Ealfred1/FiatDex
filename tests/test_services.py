import pytest
import uuid
import respx
import httpx
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.auth_service import auth_service
from app.services.injective_service import injective_service
from app.services.price_service import price_service
from app.services.paystack_service import PaystackService
from app.services.notification_service import notification_service
from app.schemas.token import MarketSummary, TokenMeta
from app.models.user import User

@pytest.fixture(autouse=True)
def mock_external(mocker):
    mocker.patch("app.services.auth_service.brevo_service", new_callable=AsyncMock)
    mocker.patch("app.core.redis_client.redis_client.get_cache", return_value=None)
    mocker.patch("app.core.redis_client.redis_client.set_cache", return_value=True)
    yield

@pytest.mark.asyncio
async def test_auth_service_logic(db_session):
    # Password
    h = auth_service.hash_password("test")
    assert auth_service.verify_password("test", h)
    
    # OTP
    otp, exp = auth_service.generate_otp()
    assert len(otp) == 6
    assert exp > datetime.utcnow()
    
    # Signup duplicate
    # (Already tested in extended, but direct service call here)
    uid = uuid.uuid4()
    user = User(id=uid, email="service@test.com")
    db_session.add(user)
    await db_session.commit()
    
    with pytest.raises(Exception):
        await auth_service.register_email_user(db_session, "service@test.com", "pass", "Name", "NG")

@pytest.mark.asyncio
async def test_injective_service_logic(mocker):
    # Patch AsyncClient at the source
    with patch("app.services.injective_service.AsyncClient") as mock_client:
        instance = mock_client.return_value
        market = MagicMock()
        market.market_id = "m1"
        market.base_denom = "d1"
        market.quote_denom = "q1"
        market.ticker = "T/Q"
        market.status = "active"
        market.min_price_tick_size = "0.01"
        market.min_quantity_tick_size = "1"
        
        instance.get_spot_markets = AsyncMock(return_value=MagicMock(markets=[market]))
        
        markets = await injective_service.get_all_spot_markets()
        assert len(markets) == 1
        assert markets[0]["market_id"] == "m1"

@pytest.mark.asyncio
async def test_price_service_logic(mocker):
    # Test token price with mock summary
    mock_summary = MarketSummary(
        market_id="m1", base_denom="d1", price=Decimal("2.5"), volume=Decimal("1"),
        high=Decimal("2.5"), low=Decimal("2.5"), change=0.0, last_price=Decimal("2.5")
    )
    mocker.patch.object(injective_service, "get_all_market_summaries", return_value=[mock_summary])
    mocker.patch.object(injective_service, "get_all_spot_markets", return_value=[{"market_id": "m1", "base_denom": "d1"}])
    
    price = await price_service.get_token_price_usd("d1")
    assert price == Decimal("2.5")

@pytest.mark.asyncio
async def test_notification_service_flow():
    # Test method exists and runs
    await notification_service.send_swap_confirmed("token", "INJ", Decimal("10"), "0x...")
    
@pytest.mark.asyncio
async def test_paystack_service_flow():
    ps = PaystackService()
    with respx.mock:
        respx.post("https://api.paystack.co/transaction/initialize").mock(return_value=httpx.Response(200, json={
            "status": True, "data": {"reference": "ref", "authorization_url": "url", "access_code": "acc"}
        }))
        res = await ps.initialize_transaction("u@u.com", Decimal("10"), "NGN")
        assert res["reference"] == "ref"
