from sqlalchemy import String, DateTime, UUID, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
import uuid
from datetime import datetime
from app.core.database import Base

class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    token_denom: Mapped[str] = mapped_column(String(128), nullable=False)
    token_symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "token_denom", name="uix_user_token_watchlist"),
    )

    def __repr__(self) -> str:
        return f"<WatchlistItem(user_id={self.user_id}, token={self.token_symbol})>"
