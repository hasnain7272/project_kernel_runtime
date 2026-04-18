"""
Message SQLAlchemy Model — Persistent LLM Conversation Turns

Every LLM call's input/output is persisted here so the agent
never loses context across restarts or step boundaries.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.session import Base


class MessageModel(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        String, primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String, ForeignKey("sessions.id"), index=True
    )
    task_id: Mapped[str] = mapped_column(
        String, ForeignKey("tasks.id"), index=True, nullable=True
    )
    role: Mapped[str] = mapped_column(String, index=True)  # system | user | assistant | tool
    content: Mapped[str] = mapped_column(Text, default="")
    tool_call_id: Mapped[str] = mapped_column(String, nullable=True)
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
