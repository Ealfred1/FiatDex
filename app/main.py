from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.core.database import engine
from app.core.redis_client import redis_client
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize connections
    yield
    # Shutdown: Close connections
    await redis_client.close()
    await engine.dispose()

from app.api.v1.router import api_router

from scalar_fastapi import get_scalar_api_reference

app = FastAPI(
    title="FiatDex API",
    description="""
## FiatDex — Buy Any Injective Token Straight From Your Wallet

FiatDex is a non-custodial mobile-first DEX explorer and fiat onramp built natively on the **Injective blockchain**.

### Key Capabilities
- 🔍 **Token Explorer** — Live price feeds, charts, orderbooks for all Injective tokens
- 💳 **Fiat Onramp** — Purchase tokens with NGN, GHS, KES, ZAR via Transak/Kado
- ⚡ **Auto-Swap** — Automatically swaps INJ → target token after fiat purchase
- 👛 **Wallet Auth** — Non-custodial auth via Keplr (Cosmos) or MetaMask (EVM)
- 🔔 **Price Alerts** — Push notifications when tokens hit target prices

### Authentication
Most endpoints require a **Bearer JWT token**. Obtain one via:
1. `POST /api/v1/wallet/auth/nonce` — Get message to sign
2. `POST /api/v1/wallet/auth/verify` — Submit signed message, receive JWT

### Networks
- **Mainnet:** `https://sentry.lcd.injective.network`
- **Testnet:** `https://testnet.sentry.lcd.injective.network`

### Support
Built for the **Injective Africa Buildathon 2026**
    """,
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json",
    contact={
        "name": "FiatDex Team",
        "url": "https://github.com/fiatdex",
    },
    license_info={
        "name": "MIT",
    },
    openapi_tags=[
        {
            "name": "Tokens",
            "description": "Real-time Injective token explorer — prices, charts, trades, orderbooks.",
        },
        {
            "name": "Onramp",
            "description": "Fiat-to-crypto onramp via Transak and Kado. Handles quotes, sessions, and webhooks.",
        },
        {
            "name": "Wallet",
            "description": "Non-custodial wallet authentication, balance queries, and user preferences.",
        },
        {
            "name": "Portfolio",
            "description": "User portfolio holdings, valuations, and transaction history.",
        },
        {
            "name": "Alerts",
            "description": "Price alerts and watchlist management with push notification delivery.",
        },
        {
            "name": "Health",
            "description": "API health and connectivity checks.",
        },
    ],
    lifespan=lifespan
)

# Mount Scalar at /docs
@app.get("/docs", include_in_schema=False)
async def scalar_html():
    return get_scalar_api_reference(
        openapi_url="/openapi.json",
        title="FiatDex API",
        scalar_theme="moon",
        scalar_favicon_url="https://injective.com/favicon.ico",
    )

# v1 Routes
app.include_router(api_router, prefix="/api/v1")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Middleware
from app.core.middleware import RateLimitMiddleware, SecurityHeadersMiddleware
app.add_middleware(RateLimitMiddleware, limit=60, window=60)
app.add_middleware(SecurityHeadersMiddleware)

# Exception Handlers
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from app.core.exceptions import (
    global_exception_handler, 
    validation_exception_handler, 
    sqlalchemy_exception_handler,
    FiatDexException,
    fiatdex_exception_handler
)

app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(FiatDexException, fiatdex_exception_handler)

@app.get("/health")
async def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT}

@app.get("/")
async def root():
    return {"message": "Welcome to FiatDex API — Injective Africa Buildathon 2026"}
