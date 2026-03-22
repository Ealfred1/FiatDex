from pydantic import BaseModel, field_serializer
from decimal import Decimal
from typing import Optional
from datetime import datetime

class SellQuoteRequest(BaseModel):
    token_denom: str
    amount: Decimal

class SellQuoteResponse(BaseModel):
    token_denom: str
    token_symbol: str
    amount_to_sell: Decimal
    estimated_usd_received: Decimal
    exchange_rate: Decimal
    fee_usd: Decimal
    expires_at: datetime
    
    @field_serializer('amount_to_sell', 'estimated_usd_received', 'exchange_rate', 'fee_usd')
    def serialize_decimal(self, v: Decimal, _info):
        return str(v)

class SellExecuteRequest(BaseModel):
    token_denom: str
    amount: Decimal
    min_usd_expected: Decimal
    slippage_tolerance: float = 0.01

class SellExecuteResponse(BaseModel):
    transaction_id: str
    status: str                    # "processing", "completed", "failed"
    token_symbol: str
    usd_received: Decimal
    tx_hash: Optional[str] = None
    
    @field_serializer('usd_received')
    def serialize_decimal(self, v: Decimal, _info):
        return str(v)
