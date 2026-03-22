from sqlalchemy import String, Boolean, DateTime, UUID, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
import uuid
from decimal import Decimal
from datetime import datetime
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_address: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    wallet_type: Mapped[str | None] = mapped_column(String(32), nullable=True)  # "keplr", "metamask", "walletconnect"
    
    # Email Auth Fields
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    auth_method: Mapped[str] = mapped_column(String(16), default="wallet")  # "email", "wallet", "both"
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # OTP & Password Reset
    otp_code: Mapped[str | None] = mapped_column(String(6), nullable=True)
    otp_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_reset_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_reset_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Profile & Balance
    country: Mapped[str | None] = mapped_column(String(2), nullable=True) # ISO 2-letter
    full_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    account_balance: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=0)
    
    expo_push_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preferred_currency: Mapped[str] = mapped_column(String(10), default="USD")
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_active: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<User(email={self.email}, wallet_address={self.wallet_address})>"
