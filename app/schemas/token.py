from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from typing import List, Optional
from datetime import datetime

class TokenMeta(BaseModel):
    name: str # Token Name
    symbol: str # Ticker symbol (e.g. INJ)
    decimals: int
    logo_url: Optional[str] = None
    address: Optional[str] = None # Contract address if relevant

class TokenSummary(BaseModel):
    market_id: str
    base_denom: str
    symbol: str
    name: str
    logo_url: Optional[str] = None
    price_usd: float
    price_local: float
    local_currency: str
    change_24h: float
    volume_24h_usd: float
    market_cap_usd: Optional[float] = None
    high_24h: float
    low_24h: float
    is_new: bool = False

class TokenFeedResponse(BaseModel):
    tokens: List[TokenSummary]
    total: int
    has_more: bool

class MarketSummary(BaseModel):
    market_id: str
    base_denom: Optional[str] = None # Added for convenience
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
    balance: float
    balance_usd: float
    decimals: int

class SwapEstimate(BaseModel):
    source_amount: float
    target_amount: float
    price_impact: float
    fee_amount: float
    min_received: float
    exchange_rate: float
