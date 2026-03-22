from sqlalchemy import String, Boolean, DateTime, UUID, Numeric, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
import uuid
from decimal import Decimal
from datetime import datetime
from app.core.database import Base

class AccountFunding(Base):
    __tablename__ = "account_fundings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    
    # Paystack specific
    reference: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    paystack_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 8))         # Amount in fiat
    currency: Mapped[str] = mapped_column(String(10))              # NGN, GHS, etc.
    amount_usd: Mapped[Decimal] = mapped_column(Numeric(18, 8))     # Equivalent USD for internal balance
    
    status: Mapped[str] = mapped_column(String(32), default="pending") # pending, success, failed
    channel: Mapped[str | None] = mapped_column(String(32), nullable=True) # card, bank, etc.
    
    metadata_json: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<AccountFunding(reference={self.reference}, status={self.status})>"
