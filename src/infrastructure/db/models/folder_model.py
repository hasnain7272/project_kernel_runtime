"""
Folder SQLAlchemy Model — Multi-tenant workspace isolation.

Folders are first-class resources with permissions per tenant.
Users can't see or access folders they don't own/aren't shared with.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.session import Base


class FolderModel(Base):
    __tablename__ = "folders"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Folder name
    name: Mapped[str] = mapped_column(String, nullable=False)
    
    # Multi-tenant isolation
    tenant_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    
    # Owner within tenant
    owner_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    
    # Path relative to workspace root (not exposed directly)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    
    # Permissions: 'owner', 'editor', 'viewer'
    permission: Mapped[str] = mapped_column(String, default="viewer")
    
    # Shared with other users (comma-separated user IDs)
    shared_with: Mapped[str] = mapped_column(String, default="")
    
    # Folder metadata
    color: Mapped[str] = mapped_column(String, default="cyan")
    description: Mapped[str] = mapped_column(String, default="")
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index("idx_folders_tenant", "tenant_id"),
        Index("idx_folders_tenant_owner", "tenant_id", "owner_id"),
    )