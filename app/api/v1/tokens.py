from fastapi import APIRouter, Query, HTTPException, Depends
from typing import List, Optional
from app.schemas.token import TokenFeedResponse, TokenSummary, MarketSummary
from app.schemas.trade import RecentTrade, Orderbook
from app.services.price_service import price_service
from app.services.injective_service import injective_service

router = APIRouter(prefix="/tokens", tags=["Tokens"])

@router.get("", response_model=TokenFeedResponse)
async def get_tokens(
    sort_by: str = Query("volume", regex="^(volume|gainers|losers|newest)$"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None,
    currency: str = "USD"
):
    """
    Fetch a list of tokens with 24h market data, converted to local currency.
    """
    return await price_service.get_token_feed(
        sort_by=sort_by,
        limit=limit,
        offset=offset,
        search=search,
        local_currency=currency
    )

@router.get("/{market_id}", response_model=TokenSummary)
async def get_token_detail(market_id: str, currency: str = "USD"):
    """
    Get detailed information for a specific token/market.
    """
    # Logic to fetch single market and enrich it
    summaries = await injective_service.get_all_market_summaries()
    summary = next((s for s in summaries if s.market_id == market_id), None)
    
    if not summary:
        raise HTTPException(status_code=404, detail="Token not found")
        
    # Reuse feed logic for a single item (simplified for now)
    feed = await price_service.get_token_feed(search=market_id, local_currency=currency)
    if not feed.tokens:
         raise HTTPException(status_code=404, detail="Token detail not found")
    return feed.tokens[0]

@router.get("/{market_id}/trades", response_model=List[dict])
async def get_recent_trades(market_id: str, limit: int = Query(50, ge=1, le=100)):
    """
    Fetch recent trades for a specific market.
    """
    return await injective_service.get_trades(market_id, limit=limit)

@router.get("/{market_id}/orderbook", response_model=dict)
async def get_orderbook(market_id: str):
    """
    Fetch live orderbook for a market.
    """
    return await injective_service.get_orderbook(market_id)
