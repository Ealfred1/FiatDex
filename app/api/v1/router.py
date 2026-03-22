from fastapi import APIRouter
from app.api.v1 import tokens, wallet, onramp, portfolio, alerts, health, auth, funding, sell

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(funding.router, prefix="/funding", tags=["Fiat Funding"])
api_router.include_router(sell.router, prefix="/sell", tags=["Sell Tokens"])
api_router.include_router(tokens.router, prefix="/tokens", tags=["Tokens"])
api_router.include_router(wallet.router, prefix="/wallet", tags=["Wallet"])
api_router.include_router(onramp.router, prefix="/onramp", tags=["Onramp"])
api_router.include_router(portfolio.router, prefix="/portfolio", tags=["Portfolio"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(health.router, prefix="/health", tags=["Health"])
