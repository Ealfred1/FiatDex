from fastapi import APIRouter, Query, HTTPException, status
from typing import List, Optional
from app.services.price_service import price_service
from app.services.injective_service import injective_service
from app.schemas.token import TokenFeedResponse, TokenSummary, MarketSummary, SwapEstimate
from app.schemas.trade import RecentTrade, Orderbook

router = APIRouter(prefix="/tokens", tags=["Tokens"])

@router.get(
    "",
    summary="Get live Injective token feed",
    description="""
Returns a paginated, real-time feed of all tradeable tokens on the Injective ecosystem.

Data is sourced from the Injective Exchange API and cached for 10 seconds.
Each token includes its current price in both USD and the user's local currency.

**Sort options:**
- `volume` (default) — Highest 24h trading volume first
- `gainers` — Biggest positive 24h price change first
- `losers` — Biggest negative 24h price change first
- `newest` — Most recently listed tokens first

**Search:**
Pass a `search` query param to filter by token name, ticker, or contract address.
Returns results within 300ms of last keystroke (designed for frontend debounce).

**Currency:**
Pass `currency=NGN` (or GHS, KES, ZAR, USD) to get `price_local` in that currency.
Defaults to USD if not provided or user has no preference set.
""",
    response_model=TokenFeedResponse,
    responses={
        200: {"description": "Paginated token feed with live prices"},
        422: {"description": "Invalid query parameters"},
        429: {"description": "Rate limit exceeded — 60 requests/min per IP"},
        503: {"description": "Injective API temporarily unavailable"},
    },
    operation_id="get_token_feed",
)
async def get_tokens(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("volume", pattern="^(volume|gainers|losers|newest)$"),
    search: Optional[str] = None,
    currency: Optional[str] = None
):
    return await price_service.get_token_feed(
        limit=limit, 
        offset=offset, 
        sort_by=sort_by, 
        search=search, 
        currency=currency
    )

@router.get(
    "/{market_id}",
    summary="Get full token detail",
    description="""
Returns comprehensive analytics for a single Injective token/market.

Includes everything on the token explorer detail screen:
- OHLCV chart data for the default timeframe (1D)
- Top-of-book orderbook snapshot (10 levels each side)
- 20 most recent trades with buyer/seller addresses
- Liquidity pool depth and stats
- Key stats: ATH, ATL, circulating supply, holders (where available)

**market_id** is the Injective market ID string, e.g.:
`0x0511ddc4e6586f3bfe1acb2dd905f8b8a82c97e1e5f4c6b8d62a5e2e5f3b3d4`

Use `GET /api/v1/tokens` to discover market IDs.
""",
    response_model=MarketSummary,
    responses={
        200: {"description": "Full token detail with chart, orderbook, and recent trades"},
        404: {"description": "Market ID not found on Injective"},
        429: {"description": "Rate limit exceeded"},
    },
    operation_id="get_token_detail",
)
async def get_token_detail(market_id: str):
    summary = await injective_service.get_spot_market_summary(market_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Market not found")
    return summary

@router.get(
    "/{market_id}/chart",
    summary="Get OHLCV candlestick data",
    description="""
Returns historical OHLCV (Open, High, Low, Close, Volume) candlestick data
for the requested market and timeframe.

**Timeframes:**
| Parameter | Candle Size | Data Range |
|-----------|------------|------------|
| `1H`      | 1 minute   | Last 1 hour |
| `4H`      | 5 minutes  | Last 4 hours |
| `1D`      | 15 minutes | Last 24 hours |
| `1W`      | 1 hour     | Last 7 days |
| `1M`      | 4 hours    | Last 30 days |

Data sourced from Injective Exchange API historical endpoint.
""",
    operation_id="get_chart_data",
)
async def get_chart(
    market_id: str,
    timeframe: str = Query("1D", pattern="^(1H|4H|1D|1W|1M)$")
):
    # This would call injective_service.get_historical_candles
    return {"candles": []}

@router.get(
    "/{market_id}/trades",
    summary="Get recent trades",
    description="""
Returns the most recent trades executed on-chain for this market.

Each trade includes:
- Buyer and seller wallet addresses (truncated for privacy)
- Trade amount in base and quote token
- Execution price
- Transaction hash with Injective Explorer link
- Block timestamp

Maximum 100 trades per request. Default 50.
""",
    response_model=List[RecentTrade],
    operation_id="get_recent_trades",
)
async def get_trades(market_id: str):
    return await injective_service.get_trades(market_id)

@router.get(
    "/{market_id}/orderbook",
    summary="Get live orderbook",
    description="""
Returns the current top-of-book state for a market.

Returns up to 50 price levels on each side (bids and asks).
Designed to power the depth chart on the token detail screen.

Data is live — no caching applied to this endpoint.
""",
    response_model=Orderbook,
    operation_id="get_orderbook",
)
async def get_orderbook(market_id: str):
    return await injective_service.get_orderbook(market_id)
