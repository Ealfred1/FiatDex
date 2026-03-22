from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime
from typing import Optional

class AlertCreate(BaseModel):
    token_denom: str
    token_symbol: str
    target_price_usd: float
    condition: str # "above", "below"

class AlertResponse(BaseModel):
    id: str
    token_denom: str
    token_symbol: str
    target_price_usd: float
    condition: str
    is_active: bool
    created_at: datetime

class WatchlistAddItem(BaseModel):
    token_denom: str
    token_symbol: str

class WatchlistResponse(BaseModel):
    token_denom: str
    token_symbol: str
    added_at: datetime
