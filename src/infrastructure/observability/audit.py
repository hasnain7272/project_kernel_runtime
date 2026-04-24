"""
Audit Logging — Per-tenant security and compliance.

Records all security-relevant events:
- Authentication attempts
- Authorization failures
- Resource access
- Data exports
- Configuration changes

Pattern: Append-only log per tenant in Redis (near-realtime)
or batched to object storage (long-term).
"""
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Audit event types."""
    # Auth events
    LOGIN = "auth.login"
    LOGIN_FAILED = "auth.login_failed"
    LOGOUT = "auth.logout"
    TOKEN_ISSUED = "auth.token_issued"
    TOKEN_REFRESHED = "auth.token_refreshed"
    TOKEN_REVOKED = "auth.token_revoked"
    API_KEY_USED = "auth.api_key_used"
    
    # Access events
    RESOURCE_READ = "access.read"
    RESOURCE_WRITE = "access.write"
    RESOURCE_DELETE = "access.delete"
    
    # Tool events
    TOOL_EXECUTED = "tool.executed"
    TOOL_DENIED = "tool.denied"
    COMMAND_BLOCKED = "tool.blocked"
    
    # Data events
    EXPORT_REQUESTED = "data.export_requested"
    EXPORT_COMPLETED = "data.export_completed"
    DELETE_REQUESTED = "data.delete_requested"
    DELETE_COMPLETED = "data.delete_completed"
    
    # Admin events
    CONFIG_CHANGED = "admin.config_changed"
    USER_CREATED = "admin.user_created"
    USER_DELETED = "admin.user_deleted"
    TENANT_UPDATED = "admin.tenant_updated"


class AuditSeverity(str, Enum):
    """Event severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Audit event record."""
    event_type: str
    tenant_id: str
    user_id: str
    
    # Context
    organization_id: Optional[str] = None
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    
    # Resource
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    
    # Details
    severity: str = AuditSeverity.INFO.value
    action: str = ""
    details: dict = field(default_factory=dict)
    
    # Metadata
    timestamp: float = field(default_factory=time.time)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None


class AuditLogger:
    """Per-tenant audit logger.
    
    Uses Redis streams for near-realtime queries,
    can be extended to object storage for long-term.
    """
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis = None
    
    async def _get_client(self):
        if self._redis is None:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(
                self.redis_url,
                decode_responses=True,
            )
        return self._redis
    
    async def log(self, event: AuditEvent):
        """Log audit event."""
        redis = await self._get_client()
        
        record = {
            "event_type": event.event_type,
            "tenant_id": event.tenant_id,
            "user_id": event.user_id,
            "organization_id": event.organization_id or "",
            "session_id": event.session_id or "",
            "task_id": event.task_id or "",
            "resource_type": event.resource_type or "",
            "resource_id": event.resource_id or "",
            "severity": event.severity,
            "action": event.action,
            "details": json.dumps(event.details),
            "timestamp": str(event.timestamp),
            "ip_address": event.ip_address or "",
            "user_agent": event.user_agent or "",
            "request_id": event.request_id or "",
        }
        
        # Append to tenant-specific stream
        stream = f"audit:{event.tenant_id}"
        await redis.xadd(stream, record)
        
        # Also append to global cross-tenant stream (limited data)
        global_stream = "audit:global"
        global_record = {k: v for k, v in record.items() if k in [
            "event_type", "tenant_id", "severity", "timestamp", "request_id"
        ]}
        global_record["details"] = json.dumps({"type": event.event_type})
        await redis.xadd(global_stream, global_record)
        
        logger.info(
            f"[Audit] {event.event_type} by {event.user_id} "
            f"(tenant={event.tenant_id}, severity={event.severity})"
        )
    
    async def log_auth(
        self,
        tenant_id: str,
        user_id: str,
        event_type: str,
        success: bool,
        details: Optional[dict] = None,
    ):
        """Log authentication event."""
        event = AuditEvent(
            event_type=event_type,
            tenant_id=tenant_id,
            user_id=user_id,
            severity=AuditSeverity.INFO.value if success else AuditSeverity.WARNING.value,
            details=details or {},
        )
        await self.log(event)
    
    async def log_tool_execution(
        self,
        tenant_id: str,
        user_id: str,
        tool_name: str,
        allowed: bool,
        reason: Optional[str] = None,
    ):
        """Log tool execution attempt."""
        event = AuditEvent(
            event_type=AuditEventType.TOOL_EXECUTED.value if allowed 
                else AuditEventType.TOOL_DENIED.value,
            tenant_id=tenant_id,
            user_id=user_id,
            resource_type="tool",
            resource_id=tool_name,
            action=tool_name,
            details={"reason": reason} if reason else {},
            severity=AuditSeverity.WARNING.value if not allowed else AuditSeverity.INFO.value,
        )
        await self.log(event)
    
    async def get_tenant_logs(
        self,
        tenant_id: str,
        limit: int = 100,
        event_type: Optional[str] = None,
    ) -> list[dict]:
        """Get audit logs for tenant."""
        redis = await self._get_client()
        
        stream = f"audit:{tenant_id}"
        
        if event_type:
            # Note: xread doesn't filter by field, need xrange + filter
            records = await redis.xrange(stream, count=limit)
        else:
            records = await redis.xrange(stream, count=limit)
        
        return [
            {"id": msg_id, **fields}
            for msg_id, fields in records
        ]


# Singleton
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get audit logger singleton."""
    global _audit_logger
    
    if _audit_logger is None:
        import os
        redis_url = os.environ.get("REDIS_URL", "")
        if redis_url:
            _audit_logger = AuditLogger(redis_url)
        else:
            logger.warning("[Audit] No REDIS_URL - audit logging disabled")
            _audit_logger = None
    
    return _audit_logger