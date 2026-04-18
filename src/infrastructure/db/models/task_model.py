"""
Task SQLAlchemy Model
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, JSON, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.session import Base

class TaskModel(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"task_{uuid.uuid4().hex[:12]}")
    session_id: Mapped[str] = mapped_column(String, ForeignKey("sessions.id"), index=True)
    type: Mapped[str] = mapped_column(String, default="custom")
    description: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String, default="pending", index=True)
    
    # Structured step definitions and context arrays
    steps: Mapped[list] = mapped_column(JSON, default=list)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    
    current_step_index: Mapped[int] = mapped_column(default=0)
    iteration_count: Mapped[int] = mapped_column(default=0)
    error: Mapped[str] = mapped_column(String, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
