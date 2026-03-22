from pydantic import BaseModel, field_serializer
from decimal import Decimal
from typing import Optional, List
from datetime import datetime

class FundingInitiateRequest(BaseModel):
    amount: Decimal
    currency: str = "NGN"

class FundingInitiateResponse(BaseModel):
    authorization_url: str
    access_code: str
    reference: str

class FundingHistoryResponse(BaseModel):
    id: str
    reference: str
    amount: Decimal
    currency: str
    amount_usd: Decimal
    status: str
    created_at: datetime
    
    @field_serializer('amount', 'amount_usd')
    def serialize_decimal(self, v: Decimal, _info):
        return str(v)

class BalanceResponse(BaseModel):
    account_balance: Decimal
    currency: str = "USD"
    
    @field_serializer('account_balance')
    def serialize_balance(self, v: Decimal, _info):
        return str(v)
