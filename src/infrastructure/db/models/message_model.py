"""
Message SQLAlchemy Model — Multi-tenant LLM conversation turns.

Stores all LLM input/output with tenant isolation.
Sequence handles ordering within tenant+session+task.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.session import Base


class MessageModel(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        String, primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    
    # Tenant isolation (denormalized for performance)
    tenant_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(
        String, ForeignKey("sessions.id"), index=True
    )
    task_id: Mapped[str] = mapped_column(
        String, ForeignKey("tasks.id"), index=True, nullable=True
    )
    
    role: Mapped[str] = mapped_column(String, index=True)
    content: Mapped[str] = mapped_column(Text, default="")
    tool_call_id: Mapped[str] = mapped_column(String, nullable=True)
    tool_calls: Mapped[dict | list] = mapped_column(Text, nullable=True) # JSON dump
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    
    __table_args__ = (
        Index("idx_messages_tenant", "tenant_id"),
        Index("idx_messages_tenant_session", "tenant_id", "session_id"),
        Index("idx_messages_sequence", "tenant_id", "session_id", "sequence"),
    )
