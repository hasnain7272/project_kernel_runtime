"""
Session Model — Multi-Tenant with Workspace Bindings

Each session is bound to one or more workspaces (local folders or git repos).
The user MUST select at least one workspace to start a session.
This is the core of the SaaS isolation model.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import String, Boolean, DateTime, Index, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.session import Base
from src.infrastructure.db.models.session_workspace import session_workspace


class SessionModel(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # ── Multi-Tenant Isolation ──────────────────────────
    tenant_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    user_id: Mapped[str] = mapped_column(String, index=True, default="system")

    # ── Session Identity ────────────────────────────────
    name: Mapped[str] = mapped_column(String(128), default="New Session")
    mode: Mapped[str] = mapped_column(String(16), default="web")
    user_role: Mapped[str] = mapped_column(String(32), default="developer")

    # ── Agent State ─────────────────────────────────────
    # Persisted context: model config (BYOK), agent memory, preferences
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    risk_mode: Mapped[str] = mapped_column(String(16), default="auto")

    # ── Lifecycle ───────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # ── Workspace Relationships (Normalized) ─────────────
    workspaces: Mapped[List["WorkspaceModel"]] = relationship(
        "WorkspaceModel",
        secondary=session_workspace,
        lazy="selectin"
    )

    __table_args__ = (
        Index("idx_sessions_tenant", "tenant_id"),
        Index("idx_sessions_org", "tenant_id", "organization_id"),
        Index("idx_sessions_user", "tenant_id", "user_id"),
        Index("idx_sessions_active", "tenant_id", "is_active"),
    )

    @property
    def mounted_folders(self) -> List[str]:
        """Get workspace slugs for backwards compatibility (derives from normalized workspaces)."""
        return [ws.slug for ws in (self.workspaces or [])]
    
    @mounted_folders.setter
    def mounted_folders(self, value: List[str]):
        """Setter for backwards compatibility — will be deprecated when all code uses workspaces."""
        pass  # No-op: ignored when using normalized relationship

    @property
    def active_workspace_slugs(self) -> list[str]:
        """Get all workspace slugs for path resolution."""
        return [ws.slug for ws in (self.workspaces or []) if ws.is_active]
