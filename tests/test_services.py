import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from app.services.price_service import price_service
from app.services.transak_service import transak_service

@pytest.mark.asyncio
async def test_price_service_forex_fallback():
    # Test fallback if API fails
    rate = await price_service.get_forex_rate("USD", "NGN")
    assert rate == 1500.0

@pytest.mark.asyncio
async def test_transak_generate_url():
    url = await transak_service.generate_widget_url(
        fiat_amount=Decimal("100"),
        fiat_currency="USD",
        wallet_address="inj1...",
        order_id="test-id"
    )
    assert "global.transak.com" in url or "staging-global.transak.com" in url
    assert "test-id" in url
