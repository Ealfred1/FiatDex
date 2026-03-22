from pydantic import BaseModel
from decimal import Decimal
from typing import List, Optional
from datetime import datetime
from uuid import UUID

class Holding(BaseModel):
    denom: str
    symbol: str
    amount: Decimal
    value_usd: Decimal
    value_local: Decimal
    change_24h_pct: float

class TransactionSummary(BaseModel):
    id: UUID
    onramp_status: str
    swap_status: str
    fiat_amount: Decimal
    fiat_currency: str
    target_token_symbol: str
    created_at: datetime

class Portfolio(BaseModel):
    total_value_usd: Decimal
    total_value_local: Decimal
    change_24h_pct: float
    holdings: List[Holding]
    recent_transactions: List[TransactionSummary]
