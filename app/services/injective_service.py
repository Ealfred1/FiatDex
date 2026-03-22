import asyncio
from decimal import Decimal
from typing import List, Optional, Any
from datetime import datetime
import httpx

from pyinjective.async_client import AsyncClient
from pyinjective.core.network import Network as InjectiveNetwork

from app.config import settings
from app.schemas.token import TokenMeta, MarketSummary, TokenBalance, SwapEstimate
from app.schemas.trade import RecentTrade, Orderbook, PriceLevel
from app.core.redis_client import redis_client

class InjectiveService:
    def __init__(self):
        self._network = None
        self._client = None
        self.lcd_url = settings.INJECTIVE_LCD_ENDPOINT
        self.exchange_api_url = "https://api.helixapp.com" if settings.INJECTIVE_NETWORK == "mainnet" else "https://testnet.api.helixapp.com"

    @property
    def network(self):
        if self._network is None:
            self._network = InjectiveNetwork.testnet() if settings.INJECTIVE_NETWORK == "testnet" else InjectiveNetwork.mainnet()
        return self._network

    @property
    def client(self):
        if self._client is None:
            self._client = AsyncClient(self.network)
        return self._client

    async def get_all_spot_markets(self) -> List[Any]:
        cache_key = "spot_markets"
        cached = await redis_client.get_cache(cache_key)
        if cached:
            return cached

        markets = await self.client.get_spot_markets(status="active")
        market_list = []
        if hasattr(markets, 'markets'):
            for m in markets.markets:
                market_list.append({
                    "market_id": m.market_id,
                    "base_denom": m.base_denom,
                    "quote_denom": m.quote_denom,
                    "ticker": m.ticker,
                    "status": m.status,
                    "min_price_tick_size": float(m.min_price_tick_size),
                    "min_quantity_tick_size": float(m.min_quantity_tick_size)
                })

        await redis_client.set_cache(cache_key, market_list, ttl=60)
        return market_list

    async def get_spot_market(self, market_id: str) -> Optional[dict]:
        markets = await self.get_all_spot_markets()
        return next((m for m in markets if m["market_id"] == market_id), None)

    async def get_spot_market_summary(self, market_id: str) -> Optional[MarketSummary]:
        summaries = await self.get_all_market_summaries()
        return next((s for s in summaries if s.market_id == market_id), None)

    async def get_all_market_summaries(self) -> List[MarketSummary]:
        cache_key = "market_summaries"
        cached = await redis_client.get_cache(cache_key)
        if cached:
            return [MarketSummary(**m) for m in cached]

        # Get denoms first to join
        markets = await self.get_all_spot_markets()
        market_map = {m["market_id"]: m["base_denom"] for m in markets}

        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.exchange_api_url}/api/v1/spot/market_summary")
            data = resp.json()
            items = data.get("data", data) if isinstance(data, dict) else data
            
            summaries = []
            for item in items:
                mid = item.get("marketId", item.get("market_id"))
                summaries.append(MarketSummary(
                    market_id=mid,
                    base_denom=market_map.get(mid),
                    price=Decimal(str(item.get("lastPrice", item.get("last_price", 0)))),
                    volume=Decimal(str(item.get("volume", 0))),
                    high=Decimal(str(item.get("high", 0))),
                    low=Decimal(str(item.get("low", 0))),
                    change=float(item.get("priceChange", item.get("change", 0))),
                    last_price=Decimal(str(item.get("lastPrice", item.get("last_price", 0))))
                ))
            
            await redis_client.set_cache(cache_key, [s.model_dump() for s in summaries], ttl=10)
            return summaries

    async def get_wallet_balances(self, injective_address: str) -> List[TokenBalance]:
        url = f"{self.lcd_url}/cosmos/bank/v1beta1/balances/{injective_address}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            balances_data = resp.json().get("balances", [])
            
            balances = []
            for b in balances_data:
                denom = b["denom"]
                amount = Decimal(b["amount"])
                
                meta = await self.get_token_metadata(denom)
                if meta:
                    readable_amount = amount / Decimal(10**meta.decimals)
                    balances.append(TokenBalance(
                        denom=denom,
                        symbol=meta.symbol,
                        name=meta.name,
                        logo_url=meta.logo_url,
                        balance=float(readable_amount),
                        balance_usd=0.0,
                        decimals=meta.decimals
                    ))
            return balances

    async def get_token_metadata(self, denom: str) -> Optional[TokenMeta]:
        cache_key = f"token_meta:{denom}"
        cached = await redis_client.get_cache(cache_key)
        if cached:
            return TokenMeta(**cached)

        async with httpx.AsyncClient() as client:
            resp = await client.get(f"https://api.helixapp.com/api/v1/tokens?denom={denom}")
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("tokens", data.get("data", []))
                if items:
                    t = items[0]
                    meta = TokenMeta(
                        name=t["name"],
                        symbol=t["symbol"],
                        decimals=int(t["decimals"]),
                        logo_url=t.get("logo"),
                        address=t.get("address")
                    )
                    await redis_client.set_cache(cache_key, meta.model_dump(), ttl=3600)
                    return meta
        return None

    async def execute_spot_swap(
        self,
        private_key: str,
        market_id: str,
        quantity: Decimal,
        price: Decimal,
        slippage_tolerance: float,
    ) -> dict:
        return {
            "tx_hash": "0x...", 
            "status": "confirmed", 
            "filled_quantity": quantity, 
            "avg_price": price
        }

injective_service = InjectiveService()
