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
        self.network = InjectiveNetwork.testnet() if settings.INJECTIVE_NETWORK == "testnet" else InjectiveNetwork.mainnet()
        self.client = AsyncClient(self.network)
        # LCD client for some REST endpoints
        self.lcd_url = settings.INJECTIVE_LCD_ENDPOINT

    async def get_all_spot_markets(self) -> List[Any]:
        """
        Fetch all active spot markets from Injective Exchange API.
        Cache result for 60 seconds in Redis.
        """
        cache_key = "spot_markets"
        cached = await redis_client.get_cache(cache_key)
        if cached:
            return cached

        # Using Exchange gRPC via AsyncClient
        markets = await self.client.get_spot_markets(status="active")
        # In a real scenario, we'd parse the gRPC response into a list of dicts/objects
        # For this implementation, we'll assume the response is serializable or we'd map it.
        # Simplified for now:
        market_list = []
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

    async def get_all_market_summaries(self) -> List[MarketSummary]:
        """
        Batch fetch summaries for all markets in one call.
        Cache for 10 seconds in Redis (key: "market_summaries").
        """
        cache_key = "market_summaries"
        cached = await redis_client.get_cache(cache_key)
        if cached:
            return [MarketSummary(**m) for m in cached]

        # Injective doesn't have a single "all summaries" gRPC call in basic client usually, 
        # but Helix API or a specific Exchange REST endpoint does.
        # We'll use the Helix-like endpoint if available, otherwise iterate.
        # Following the prompt: GET /api/v1/spot/market_summary
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.network.exchange_endpoint}/api/v1/spot/market_summary")
            data = resp.json()
            
            summaries = []
            for item in data:
                summaries.append(MarketSummary(
                    market_id=item["marketId"],
                    price=Decimal(item["lastPrice"]),
                    volume=Decimal(item["volume"]),
                    high=Decimal(item["high"]),
                    low=Decimal(item["low"]),
                    change=float(item["priceChange"]),
                    last_price=Decimal(item["lastPrice"])
                ))
            
            await redis_client.set_cache(cache_key, [s.model_dump() for s in summaries], ttl=10)
            return summaries

    async def get_wallet_balances(self, injective_address: str) -> List[TokenBalance]:
        """
        Fetch all token balances for a wallet address.
        Uses Bank module: GET /cosmos/bank/v1beta1/balances/{address}
        Enrich each balance with token metadata.
        """
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
                    # Convert to human readable amount
                    readable_amount = amount / Decimal(10**meta.decimals)
                    # For balance_usd, we'd multiply by price from PriceService
                    # But InjectiveService is low-level, so we'll leave balance_usd to PriceService or caller
                    balances.append(TokenBalance(
                        denom=denom,
                        symbol=meta.symbol,
                        name=meta.name,
                        logo_url=meta.logo_url,
                        balance=readable_amount,
                        balance_usd=Decimal(0), # To be filled by caller
                        decimals=meta.decimals
                    ))
            return balances

    async def get_token_metadata(self, denom: str) -> Optional[TokenMeta]:
        """
        Get token metadata (name, symbol, decimals, logo_url) for a denom.
        Cache per denom for 1 hour.
        """
        cache_key = f"token_meta:{denom}"
        cached = await redis_client.get_cache(cache_key)
        if cached:
            return TokenMeta(**cached)

        # Fallback to hardcoded or common registry if registry API lookup fails
        # In productive version, use Injective token registry (GitHub or Helix API)
        async with httpx.AsyncClient() as client:
            # Helix API example
            resp = await client.get(f"https://api.helixapp.com/api/v1/tokens?denom={denom}")
            if resp.status_code == 200:
                data = resp.json()
                if data.get("tokens"):
                    t = data["tokens"][0]
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
        """
        Execute a market buy order on Injective spot DEX.
        """
        # Note: Implementation would involve using Transaction object and signing
        # with private key. This is a simplified placeholder structure.
        # In a real environment, we'd use:
        # composer = Composer(network=self.network.network)
        # msg = composer.MsgCreateSpotMarketOrder(...)
        # tx = Transaction(...)
        # tx.add_message(msg)
        # signed_tx = tx.sign(private_key)
        # resp = await self.client.broadcast_tx(signed_tx)
        
        # Simulated response
        return {
            "tx_hash": "0x...", 
            "status": "confirmed", 
            "filled_quantity": quantity, 
            "avg_price": price
        }

injective_service = InjectiveService()
