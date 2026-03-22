import asyncio
from decimal import Decimal
from typing import List, Optional
from app.services.injective_service import injective_service
from app.schemas.token import TokenFeedResponse, TokenSummary, MarketSummary
from app.core.redis_client import redis_client
import httpx

class PriceService:
    async def get_token_feed(
        self,
        sort_by: str = "volume",
        limit: int = 50,
        offset: int = 0,
        search: str | None = None,
        local_currency: str = "USD",
        currency: str | None = None
    ) -> TokenFeedResponse:
        """
        Primary endpoint data builder.
        Enriches market summaries with metadata and converts to local currency.
        """
        # Use currency if provided, otherwise local_currency
        target_currency = currency or local_currency
        
        # Cache key includes search and local_currency for granularity
        cache_key = f"token_feed:{sort_by}:{search}:{target_currency}"
        cached = await redis_client.get_cache(cache_key)
        
        from app.schemas.token import TokenSummary
        
        if cached:
            if isinstance(cached, dict) and "tokens" in cached:
                try:
                    total = int(cached.get("total", 0))
                except (TypeError, ValueError, AttributeError):
                    total = 0
                
                return TokenFeedResponse(
                    tokens=[TokenSummary(**t) for t in cached["tokens"]],
                    total=total,
                    has_more=bool(cached.get("has_more", False))
                )
            return TokenFeedResponse.model_validate(cached)

        # 1. Fetch all market summaries
        all_summaries = await injective_service.get_all_market_summaries()
        # 2. Fetch all spot markets to get denoms
        spot_markets = await injective_service.get_all_spot_markets()
        market_map = {m["market_id"]: m for m in spot_markets}

        # 3. Get forex rate
        forex_rate = await self.get_forex_rate("USD", target_currency)
        
        tokens = []
        for s in all_summaries:
            market_info = market_map.get(s.market_id)
            if not market_info:
                continue

            # Filter by search if provided
            if search and search.lower() not in market_info["ticker"].lower():
                continue

            meta = await injective_service.get_token_metadata(market_info["base_denom"])
            if not meta:
                continue

            tokens.append(TokenSummary(
                market_id=s.market_id,
                base_denom=market_info["base_denom"],
                symbol=meta.symbol,
                name=meta.name,
                logo_url=meta.logo_url,
                price_usd=s.last_price,
                price_local=float(s.last_price * Decimal(str(forex_rate))),
                local_currency=target_currency,
                change_24h=s.change,
                volume_24h_usd=s.volume,
                market_cap_usd=None, # Injective API doesn't provide this directly
                high_24h=s.high,
                low_24h=s.low,
                is_new=False # Logic to determine if new (e.g. check created_at)
            ))

        # 4. Sort
        if sort_by == "volume":
            tokens.sort(key=lambda x: x.volume_24h_usd, reverse=True)
        elif sort_by == "gainers":
            tokens.sort(key=lambda x: x.change_24h, reverse=True)
        elif sort_by == "losers":
            tokens.sort(key=lambda x: x.change_24h)
        # elif sort_by == "newest": ...

        # 5. Paginate
        paginated_tokens = tokens[offset : offset + limit]
        
        response = TokenFeedResponse(
            tokens=paginated_tokens,
            total=len(tokens),
            has_more=len(tokens) > offset + limit
        )

        await redis_client.set_cache(cache_key, response.model_dump(), ttl=10)
        return response

    async def get_forex_rate(self, from_currency: str, to_currency: str) -> float:
        """
        Get current exchange rate between two fiat currencies.
        """
        if from_currency == to_currency:
            return 1.0
            
        cache_key = f"forex_rate:{from_currency}:{to_currency}"
        cached = await redis_client.get_cache(cache_key)
        if cached:
            return float(cached)

        # Using frankfurter.app as a free API
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://api.frankfurter.app/latest?from={from_currency}&to={to_currency}",
                    timeout=5.0
                )
                if resp.status_code == 200:
                    rate = resp.json()["rates"][to_currency]
                    await redis_client.set_cache(cache_key, rate, ttl=3600)
                    return float(rate)
        except Exception:
            pass

        # Fallback for common African currencies
        fallbacks = {
            "NGN": 1500.0,
            "GHS": 14.0,
            "KES": 130.0,
            "ZAR": 19.0
        }
        return fallbacks.get(to_currency, 1.0)

    async def get_token_price_usd(self, denom: str) -> Optional[Decimal]:
        """
        Get current USD price for any Injective token denom.
        """
        # Find which market uses this denom as base
        markets = await injective_service.get_all_spot_markets()
        market_id = next((m["market_id"] for m in markets if m["base_denom"] == denom), None)
        
        if market_id:
            summaries = await injective_service.get_all_market_summaries()
            summary = next((s for s in summaries if s.market_id == market_id), None)
            if summary:
                return summary.last_price
        return None

price_service = PriceService()
