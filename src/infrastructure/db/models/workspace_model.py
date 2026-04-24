"""
Workspace Model — Normalized workspace bindings for sessions.

Each workspace can be bound to multiple sessions (many-to-many).
Supports both local folders and git repositories.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import String, Boolean, DateTime, Index, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.session import Base
from src.infrastructure.db.models.session_workspace import session_workspace


class WorkspaceModel(Base):
    """Workspace definition for local folders or git repositories."""
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    
    # Tenant isolation (denormalized for performance)
    tenant_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    
    # Workspace identification
    slug: Mapped[str] = mapped_column(String(63), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Workspace type: local or git
    type: Mapped[str] = mapped_column(
        String(10), nullable=False,  # "local" or "git"
        index=True
    )
    
    # For local workspaces
    path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # For git workspaces
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    branch: Mapped[str] = mapped_column(String(50), default="main")
    
    # Metadata
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    sessions: Mapped[List["SessionModel"]] = relationship(
        "SessionModel",
        secondary=session_workspace,
        back_populates="workspaces"
    )
    
    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_workspace_tenant_slug"),
        Index("idx_workspaces_tenant", "tenant_id"),
        Index("idx_workspaces_type", "type"),
    )