from sqlalchemy import String, Boolean, DateTime, UUID, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
import uuid
from decimal import Decimal
from datetime import datetime
from app.core.database import Base

class PriceAlert(Base):
    __tablename__ = "price_alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    token_denom: Mapped[str] = mapped_column(String(128), nullable=False)
    token_symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    target_price_usd: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    condition: Mapped[str] = mapped_column(String(16), nullable=False)  # "above", "below"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<PriceAlert(token={self.token_symbol}, target={self.target_price_usd})>"
