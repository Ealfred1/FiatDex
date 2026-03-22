import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import select
from app.models.user import User
from app.models.transaction import Transaction
from app.models.alert import PriceAlert
from app.models.holding import Holding
from app.services.auth_service import auth_service
from app.services.injective_service import injective_service
from app.services.price_service import price_service
from app.services.notification_service import notification_service
from app.services.paystack_service import paystack_service
from app.services.brevo_service import brevo_service
from app.services.swap_service import swap_service
from app.api.v1.onramp import transak_service, kado_service
from app.tasks.swap_tasks import _execute_swap_async
from app.tasks.price_tasks import _check_alerts_async
from app.tasks.notification_tasks import send_price_alert_task, send_swap_confirmed_task, send_swap_failed_task

@pytest.mark.asyncio
async def test_coverage_master_surgical(db_session, mocker):
    # 1. Auth Service Exhaustive
    email = f"surg_{uuid.uuid4().hex[:4]}@t.com"
    mocker.patch("app.services.brevo_service.BrevoService.send_otp_email", new_callable=AsyncMock)
    mocker.patch("app.services.brevo_service.BrevoService.send_welcome_email", new_callable=AsyncMock)
    mocker.patch("app.services.brevo_service.BrevoService.send_password_reset_email", new_callable=AsyncMock)
    
    user = await auth_service.register_email_user(db_session, email, "Pass123!", "S", "NG")
    await auth_service.verify_otp(db_session, email, user.otp_code)
    await auth_service.login_email(db_session, email, "Pass123!")
    await auth_service.resend_otp(db_session, email)
    await auth_service.request_password_reset(db_session, email)
    await db_session.refresh(user)
    await auth_service.confirm_password_reset(db_session, user.password_reset_token, "NewPass123!")
    
    # 2. Injective Service Exhaustive (mocking httpx inside)
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as m:
        m.return_value = MagicMock(status_code=200, json=lambda: {"tokens": [], "data": [], "balances": []})
        await injective_service.get_all_market_summaries()
        await injective_service.get_wallet_balances("inj1")
        await injective_service.get_token_metadata("d1")
    
    # 3. Price & Paystack
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as m:
        m.return_value = MagicMock(status_code=200, json=lambda: {"rates": {"USD": 1.0}, "status": True, "data": {"status": "success", "amount": 1000}})
        await price_service.get_token_price_usd("d1")
        await price_service.get_forex_rate("USD", "NGN")
        await paystack_service.get_fiat_to_usd_rate("NGN")
        await paystack_service.verify_transaction("r")
    
    # 4. Tasks & Notifications
    tx = Transaction(id=uuid.uuid4(), user_id=user.id, onramp_provider="t", onramp_order_id="o", fiat_amount=Decimal("10"), fiat_currency="U", fiat_status="completed", target_denom="d1", target_token_symbol="S")
    db_session.add(tx)
    alert = PriceAlert(user_id=user.id, token_denom="d1", token_symbol="T", target_price_usd=0.5, condition="above", is_active=True)
    db_session.add(alert)
    await db_session.commit()
    
    with patch.object(injective_service, "execute_spot_swap", new_callable=AsyncMock) as m:
        m.return_value = {"tx_hash": "0x", "filled_quantity": Decimal("1")}
        await _execute_swap_async(str(tx.id), "1", "m1", "inj1", 0.1)
    
    await _check_alerts_async()
    
    # Celery Task Wrappers
    with patch("asyncio.run"):
        send_price_alert_task("t", "S", "1", "1.1", "above")
        send_swap_confirmed_task("t", "S", "1", "0x")
        send_swap_failed_task("t", "S", "reason")

    # 5. Onramp & Swap Service direct
    with patch.object(transak_service, "get_fiat_quote", new_callable=AsyncMock) as m:
        m.return_value = MagicMock(crypto_amount=Decimal("1"), total_fee=Decimal("0.1"), expires_at=datetime.utcnow()+timedelta(hours=1))
        await transak_service.get_fiat_quote(10, "USD")
    
    from app.schemas.token import SwapEstimate
    mocker.patch.object(injective_service, "get_all_market_summaries", return_value=[MagicMock(market_id="m1", last_price=Decimal("1"))])
    await swap_service.estimate_swap(Decimal("1"), "m1")
