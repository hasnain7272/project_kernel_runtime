"""
Session SQLAlchemy Model
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.session import Base

class SessionModel(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, default="New Session")
    user_id: Mapped[str] = mapped_column(String, index=True, default="system")
    workspace_path: Mapped[str] = mapped_column(String, default=".")
    mode: Mapped[str] = mapped_column(String, default="cli")
    user_role: Mapped[str] = mapped_column(String, default="developer")
    risk_mode: Mapped[str] = mapped_column(String, default="auto")
    
    # Store dynamic dict data securely (In PostgreSQL this maps to JSONB, in sqlite JSON)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
