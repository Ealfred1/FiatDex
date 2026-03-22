import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from unittest.mock import AsyncMock, MagicMock
import respx
from faker import Faker
import json

from app.main import app
from app.core.database import Base, get_db
from app.core.redis_client import redis_client
from app.models.user import User
from app.models.transaction import Transaction
from app.models.alert import PriceAlert
from app.services.auth_service import auth_service

fake = Faker()

# ── Database ──────────────────────────────────────────────────────────────────

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(test_engine):
    async_session = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        # Mock commit to be a flush during tests
        # This allows us to rollback everything at the end
        session.commit = session.flush
        
        yield session
        await session.rollback()
        await session.close()

# ── Redis Mock ────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_redis(mocker):
    # Instead of AsyncMock, we can mock the methods on the existing redis_client
    mocker.patch.object(redis_client, "get_cache", return_value=None)
    mocker.patch.object(redis_client, "set_cache", return_value=True)
    mocker.patch.object(redis_client, "delete_cache", return_value=True)
    
    # Mock the internal client's ping
    mock_ping = AsyncMock(return_value=True)
    mocker.patch.object(redis_client.client, "ping", mock_ping)
    
    return redis_client

# ── App Client ────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(db_session, mock_redis):
    app.dependency_overrides[get_db] = lambda: db_session
    # We don't need override for get_redis if we patched redis_client globally
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()

# ── Users ─────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def test_user(db_session) -> User:
    user = User(
        wallet_address="inj1test123456789abcdefghijklmnopqrstuvwxyz",
        wallet_type="keplr",
        preferred_currency="NGN",
        expo_push_token="ExponentPushToken[test-token-abc123]",
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user

@pytest.fixture
def auth_headers(test_user) -> dict:
    token = auth_service.create_access_token(
        data={"sub": test_user.wallet_address}
    )
    return {"Authorization": f"Bearer {token}"}

@pytest_asyncio.fixture
async def metamask_user(db_session) -> User:
    user = User(
        wallet_address="0xAbCd1234567890EfGh1234567890AbCd12345678",
        wallet_type="metamask",
        preferred_currency="USD",
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user

# ── Sample Data ───────────────────────────────────────────────────────────────

@pytest.fixture
def sample_market_summaries() -> list[dict]:
    """Realistic list of 20 Injective market summaries."""
    return [
        {
            "market_id": f"0x{i:064x}",
            "ticker": f"TOKEN{i}/USDT",
            "base_denom": f"factory/inj1abc{i}/token{i}",
            "quote_denom": "peggy0xdAC17F958D2ee523a2206206994597C13D831ec7",
            "last_price": str(round(0.001 * (i + 1) * 1.5, 6)),
            "volume": str(100000 * (20 - i)),
            "change": str(round((-5 + i * 0.5), 2)),
            "high": str(round(0.002 * (i + 1), 6)),
            "low": str(round(0.0005 * (i + 1), 6)),
        }
        for i in range(20)
    ]

@pytest.fixture
def sample_orderbook() -> dict:
    return {
        "bids": [
            {"price": str(round(1.0 - i * 0.001, 4)), "quantity": str(1000 * (i + 1))}
            for i in range(10)
        ],
        "asks": [
            {"price": str(round(1.0 + i * 0.001, 4)), "quantity": str(800 * (i + 1))}
            for i in range(10)
        ],
    }

@pytest.fixture
def sample_recent_trades() -> list[dict]:
    return [
        {
            "trade_id": f"trade_{i}",
            "price": str(round(1.0 + i * 0.0001, 6)),
            "quantity": str(500 + i * 50),
            "trade_direction": "buy" if i % 2 == 0 else "sell",
            "executed_at": f"2026-03-22T10:{i:02d}:00Z",
            "tx_hash": f"0xabc{i:060x}",
        }
        for i in range(20)
    ]

@pytest.fixture
def sample_transak_webhook_payload() -> dict:
    return {
        "eventID": "ORDER_COMPLETED",
        "data": {
            "id": "transak-order-abc123",
            "status": "COMPLETED",
            "fiatAmount": 5000,
            "fiatCurrency": "NGN",
            "cryptoAmount": 2.45,
            "cryptoCurrency": "INJ",
            "walletAddress": "inj1test123456789abcdefghijklmnopqrstuvwxyz",
            "transactionHash": "0xdeadbeef1234567890",
        }
    }

@pytest_asyncio.fixture
async def pending_transaction(db_session, test_user) -> Transaction:
    tx = Transaction(
        user_id=test_user.id,
        onramp_provider="transak",
        onramp_order_id="transak-order-abc123",
        fiat_amount=5000,
        fiat_currency="NGN",
        fiat_status="pending",
        target_denom="factory/inj1abc/token1",
        target_token_symbol="TOKEN1",
        swap_slippage_tolerance=0.01,
    )
    db_session.add(tx)
    await db_session.commit()
    await db_session.refresh(tx)
    return tx

@pytest_asyncio.fixture
async def completed_transaction(db_session, test_user) -> Transaction:
    tx = Transaction(
        user_id=test_user.id,
        onramp_provider="transak",
        onramp_order_id="transak-order-xyz789",
        fiat_amount=10000,
        fiat_currency="NGN",
        fiat_status="completed",
        inj_amount=4.9,
        target_denom="factory/inj1abc/token2",
        target_token_symbol="TOKEN2",
        swap_tx_hash="0xswaptxhash123",
        swap_status="confirmed",
        swap_amount_received=125.5,
    )
    db_session.add(tx)
    await db_session.commit()
    await db_session.refresh(tx)
    return tx
