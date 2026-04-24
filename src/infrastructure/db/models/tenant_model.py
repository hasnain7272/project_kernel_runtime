"""
Tenant Model — Multi-tenant hierarchy with RLS support.

Architecture: Pool Model (shared tables with tenant_id)
- Each tenant has isolated data via tenant_id column
- RLS policies enforce isolation at DB level
- Supports scaling to 10k+ tenants
"""
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, Integer, Numeric, Float, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.session import Base


class TierLevel(str, Enum):
    STARTER = "starter"      # < 5 users, 1k msg/mo
    PRO = "pro"             # < 25 users, 10k msg/mo
    BUSINESS = "business"   # < 100 users, unlimited
    ENTERPRISE = "enterprise"  # Custom limits


class TenantStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"


class TenantModel(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(
        String, primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    slug: Mapped[str] = mapped_column(
        String(63), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Hierarchy: enterprise has multiple orgs, org has users
    parent_id: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, index=True
    )
    tier: Mapped[str] = mapped_column(
        String(20), default=TierLevel.PRO.value
    )
    status: Mapped[str] = mapped_column(
        String(20), default=TenantStatus.PENDING.value
    )
    
    # Limits (enforced at API level)
    max_users: Mapped[int] = mapped_column(Integer, default=25)
    max_tokens_monthly: Mapped[int] = mapped_column(Integer, default=100000)
    rate_limit_rpm: Mapped[int] = mapped_column(Integer, default=60)
    rate_limit_rph: Mapped[int] = mapped_column(Integer, default=500)
    
    # Usage tracking
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    cost_cents: Mapped[int] = mapped_column(Integer, default=0)
    quota_usd: Mapped[float] = mapped_column(Float, default=50.00)
    
    # Per-tenant config (API keys, custom prompts, etc.)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Security
    api_key_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    
    __table_args__ = (
        Index("idx_tenants_tier", "tier"),
        Index("idx_tenants_status", "status"),
    )


class OrganizationModel(Base):
    """Organization within a tenant (for enterprise tier)."""
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(
        String, primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        String, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(63), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )


class UserModel(Base):
    """User within a tenant/organization."""
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String, primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        String, nullable=False, index=True
    )
    organization_id: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, index=True
    )
    
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(
        String(20), default="developer"
    )  # admin, developer, viewer
    
    # Auth
    password_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Limits
    max_tokens_monthly: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Activity
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    
    __table_args__ = (
        Index("idx_users_tenant_email", "tenant_id", "email", unique=True),
        Index("idx_users_org", "tenant_id", "organization_id"),
    )