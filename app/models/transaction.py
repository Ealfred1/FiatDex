from sqlalchemy import String, DateTime, UUID, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
import uuid
from decimal import Decimal
from datetime import datetime
from app.core.database import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    
    # Fiat onramp phase
    onramp_provider: Mapped[str] = mapped_column(String(32))  # "transak", "kado"
    onramp_order_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    fiat_amount: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    fiat_currency: Mapped[str] = mapped_column(String(10))  # NGN, GHS, KES, ZAR, USD
    fiat_status: Mapped[str] = mapped_column(String(32), default="pending")  # pending, completed, failed
    
    # INJ received
    inj_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    inj_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Swap phase
    target_denom: Mapped[str] = mapped_column(String(128))
    target_token_symbol: Mapped[str] = mapped_column(String(32))
    swap_tx_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    swap_status: Mapped[str] = mapped_column(String(32), default="pending")  # pending, submitted, confirmed, failed
    swap_amount_received: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    swap_slippage_tolerance: Mapped[float] = mapped_column(default=0.01)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, status={self.fiat_status}/{self.swap_status})>"
