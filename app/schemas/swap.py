from pydantic import BaseModel
from decimal import Decimal
from typing import Optional
from uuid import UUID

class SwapRequest(BaseModel):
    target_market_id: str
    inj_amount: Decimal
    slippage_tolerance: float = 0.01

class SwapResult(BaseModel):
    tx_hash: str
    status: str
    amount_received: Decimal
    price: Decimal

class SwapStatus(BaseModel):
    tx_hash: str
    status: str # "pending", "confirmed", "failed"
    explorer_url: str
