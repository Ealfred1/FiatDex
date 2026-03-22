from sqlalchemy import String, Boolean, DateTime, UUID, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
import uuid
from datetime import datetime
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_address: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    wallet_type: Mapped[str] = mapped_column(String(32), nullable=False)  # "keplr", "metamask", "walletconnect"
    expo_push_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preferred_currency: Mapped[str] = mapped_column(String(10), default="USD")
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_active: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<User(wallet_address={self.wallet_address})>"
