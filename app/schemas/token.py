from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from typing import List, Optional
from datetime import datetime

class TokenMeta(BaseModel):
    name: str
    symbol: str
    decimals: int
    logo_url: Optional[str] = None
    address: Optional[str] = None

class TokenSummary(BaseModel):
    market_id: str
    base_denom: str
    symbol: str
    name: str
    logo_url: Optional[str] = None
    price_usd: Decimal
    price_local: Decimal
    local_currency: str
    change_24h: float
    volume_24h_usd: Decimal
    market_cap_usd: Optional[Decimal] = None
    high_24h: Decimal
    low_24h: Decimal
    is_new: bool = False

class TokenFeedResponse(BaseModel):
    tokens: List[TokenSummary]
    total: int
    has_more: bool

class MarketSummary(BaseModel):
    market_id: str
    price: Decimal
    volume: Decimal
    high: Decimal
    low: Decimal
    change: float
    last_price: Decimal

class TokenBalance(BaseModel):
    denom: str
    symbol: str
    name: str
    logo_url: Optional[str] = None
    balance: Decimal
    balance_usd: Decimal
    decimals: int

class SwapEstimate(BaseModel):
    source_amount: Decimal
    target_amount: Decimal
    price_impact: float
    fee_amount: Decimal
    min_received: Decimal
    exchange_rate: Decimal
