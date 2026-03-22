from pydantic import BaseModel, Field, field_serializer, ConfigDict
from decimal import Decimal
from typing import List, Optional, Dict
from datetime import datetime

class OnrampQuoteRequest(BaseModel):
    fiat_amount: float
    fiat_currency: str
    target_market_id: str
    payment_method: str = "credit_debit_card"

class OnrampQuoteResponse(BaseModel):
    provider: str
    fiat_amount: float
    fiat_currency: str
    estimated_inj_amount: float
    estimated_target_amount: float
    fees: float
    expires_at: Optional[datetime] = None

class OnrampSessionRequest(BaseModel):
    provider: str
    fiat_amount: float
    fiat_currency: str
    target_denom: str
    payment_method: str = "credit_debit_card"
    slippage_tolerance: float = 0.01

class OnrampSessionResponse(BaseModel):
    transaction_id: str
    widget_url: str

class BuyFromBalanceRequest(BaseModel):
    amount_usd: Decimal
    target_denom: str
    target_token_symbol: str
    slippage_tolerance: float = 0.01

class BuyFromBalanceResponse(BaseModel):
    transaction_id: str
    status: str                    # "processing", "completed", "failed"
    estimated_amount: Decimal
    target_symbol: str

    @field_serializer('estimated_amount')
    def serialize_decimal(self, v: Decimal, _info):
        return str(v)

    model_config = ConfigDict(from_attributes=True)

class OnrampOrderResult(BaseModel):
    transaction_id: str
    onramp_status: str
    swap_status: str
    inj_received: Optional[float] = None
    target_received: Optional[float] = None
    explorer_url: Optional[str] = None

# Legacy/Service Internal schemas
class FiatOnrampQuote(BaseModel):
    provider: str
    fiat_amount: Decimal
    fiat_currency: str
    crypto_amount: Decimal
    crypto_currency: str = "INJ"
    total_fee: Decimal
    network_fee: Decimal
    service_fee: Decimal
    conversion_price: Decimal
    expires_at: datetime

    @field_serializer('fiat_amount', 'crypto_amount', 'total_fee', 'network_fee', 'service_fee', 'conversion_price')
    def serialize_decimal(self, v: Decimal, _info):
        return str(v)

class OnrampQuote(BaseModel):
    provider: str
    fiat_amount: Decimal
    fiat_currency: str
    estimated_inj_amount: Decimal
    estimated_target_token_amount: Decimal
    exchange_rate: Decimal
    fees: Dict[str, Decimal]
    min_amount: Decimal
    max_amount: Decimal
    supported_payment_methods: List[str]

    @field_serializer('fiat_amount', 'estimated_inj_amount', 'estimated_target_token_amount', 'exchange_rate', 'min_amount', 'max_amount')
    def serialize_decimal(self, v: Decimal, _info):
        return str(v)

class OnrampSession(BaseModel):
    transaction_id: str
    widget_url: str
    provider: str
    order_id: str
    expires_at: datetime

class TransakOrderResult(BaseModel):
    order_id: str
    status: str
    fiat_amount: Decimal
    crypto_amount: Decimal
    wallet_address: str
    tx_hash: Optional[str] = None

    @field_serializer('fiat_amount', 'crypto_amount')
    def serialize_decimal(self, v: Decimal, _info):
        return str(v)

class KadoOrderResult(BaseModel):
    order_id: str
    status: str
    fiat_amount: Decimal
    crypto_amount: Decimal
    wallet_address: str
    tx_hash: Optional[str] = None

    @field_serializer('fiat_amount', 'crypto_amount')
    def serialize_decimal(self, v: Decimal, _info):
        return str(v)
