from sqlalchemy import String, Boolean, DateTime, UUID, Numeric, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
import uuid
from decimal import Decimal
from datetime import datetime
from app.core.database import Base

class Holding(Base):
    __tablename__ = "holdings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    
    token_denom: Mapped[str] = mapped_column(String(128))
    token_symbol: Mapped[str] = mapped_column(String(32))
    
    amount: Mapped[Decimal] = mapped_column(Numeric(24, 12), default=0)
    avg_price_usd: Mapped[Decimal] = mapped_column(Numeric(24, 12), default=0)
    total_cost_usd: Mapped[Decimal] = mapped_column(Numeric(24, 12), default=0)
    
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Holding(symbol={self.token_symbol}, amount={self.amount})>"
