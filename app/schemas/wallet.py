from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from decimal import Decimal
from app.schemas.token import TokenBalance

class WalletAuthRequest(BaseModel):
    wallet_address: str
    wallet_type: str # "keplr", "metamask", "walletconnect"

class WalletNonceResponse(BaseModel):
    nonce: str
    message: str
    expires_in: int = 300

class WalletVerifyRequest(BaseModel):
    wallet_address: str
    wallet_type: str
    signature: str
    nonce: str

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    wallet_address: Optional[str] = None
    wallet_type: Optional[str] = None
    preferred_currency: str
    is_active: bool

class TokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class WalletBalance(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    total_value_usd: Decimal
    total_value_local: Decimal
    local_currency: str
    tokens: List[TokenBalance]
