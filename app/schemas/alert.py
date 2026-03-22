from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime
from uuid import UUID
from typing import Optional

class PriceAlertCreate(BaseModel):
    token_denom: str
    token_symbol: str
    target_price_usd: Decimal
    condition: str # "above", "below"

class PriceAlertResponse(BaseModel):
    id: UUID
    token_denom: str
    token_symbol: str
    target_price_usd: Decimal
    condition: str
    is_active: bool
    created_at: datetime

class WatchlistCreate(BaseModel):
    token_denom: str
    token_symbol: str

class WatchlistItemResponse(BaseModel):
    token_denom: str
    token_symbol: str
    added_at: datetime
