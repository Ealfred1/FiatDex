from fastapi import APIRouter
from app.api.v1 import tokens, wallet, onramp, portfolio, alerts

api_router = APIRouter()

api_router.include_router(tokens.router)
api_router.include_router(wallet.router)
api_router.include_router(onramp.router)
api_router.include_router(portfolio.router)
api_router.include_router(alerts.router)
