from pydantic import BaseModel, EmailStr, field_validator, field_serializer, ConfigDict
import re
import uuid
from decimal import Decimal
from datetime import datetime
from typing import Optional

class EmailSignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    country: str                   # ISO 2-letter: NG, GH, KE, ZA, etc.

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one number")
        return v

    @field_validator("country")
    @classmethod
    def valid_country(cls, v):
        allowed = {"NG", "GH", "KE", "ZA", "US", "GB", "CA", "AU"}
        if v.upper() not in allowed:
            raise ValueError(f"Country must be one of: {', '.join(allowed)}")
        return v.upper()

class EmailLoginRequest(BaseModel):
    email: EmailStr
    password: str

class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp_code: str                  # 6-digit string

class ResendOTPRequest(BaseModel):
    email: EmailStr

class PasswordResetRequestSchema(BaseModel):
    email: EmailStr

class PasswordResetConfirmSchema(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

class UserPublic(BaseModel):
    id: uuid.UUID
    email: Optional[str] = None
    full_name: Optional[str] = None
    country: Optional[str] = None
    wallet_address: Optional[str] = None
    auth_method: str
    email_verified: bool
    preferred_currency: str
    account_balance: Decimal           # Will be serialized to string
    created_at: datetime

    @field_serializer('id', 'account_balance')
    def serialize_to_str(self, v, _info):
        return str(v)

    model_config = ConfigDict(from_attributes=True)

class SignupResponse(BaseModel):
    message: str
    email: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
