"""
Credits Engine v2 — SQLite-backed Usage Metering

Real usage tracking:
- Per-tenant token & tool metering
- SQLite persistence
- Quota enforcement
- Usage reports
"""

import logging
import os
import sqlite3
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class CreditsEngine:
    """Per-tenant usage metering and billing."""

    def __init__(self, db_path: str = "./data/credits.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or '.', exist_ok=True)
        self._init_db()
        logger.info("[CreditsEngine] Initialized")

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    usage_type TEXT NOT NULL,
                    quantity INTEGER DEFAULT 1,
                    timestamp REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS quotas (
                    tenant_id TEXT PRIMARY KEY,
                    max_tool_calls INTEGER DEFAULT 10000,
                    max_tokens INTEGER DEFAULT 1000000,
                    max_compute_sec INTEGER DEFAULT 3600
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_tenant ON usage(tenant_id)")

    def record_usage(self, tenant_id: str, usage_type: str, quantity: int = 1):
        """Record a usage event."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO usage (tenant_id, usage_type, quantity, timestamp) VALUES (?, ?, ?, ?)",
                    (tenant_id, usage_type, quantity, time.time()),
                )
        except Exception as e:
            logger.error(f"[CreditsEngine] Record failed: {e}")

    def get_usage(self, tenant_id: str, since: float = None) -> Dict[str, int]:
        """Get usage totals for a tenant."""
        since = since or (time.time() - 86400 * 30)  # Default: last 30 days
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute(
                    "SELECT usage_type, SUM(quantity) FROM usage WHERE tenant_id = ? AND timestamp > ? GROUP BY usage_type",
                    (tenant_id, since),
                ).fetchall()
                return {row[0]: row[1] for row in rows}
        except Exception:
            return {}

    def check_quota(self, tenant_id: str, usage_type: str) -> bool:
        """Check if tenant is within quota."""
        usage = self.get_usage(tenant_id)
        current = usage.get(usage_type, 0)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT * FROM quotas WHERE tenant_id = ?", (tenant_id,)
                ).fetchone()
                if not row:
                    return True
                
                quota_map = {"tool_call": row[1], "tokens": row[2], "wasm_compute_sec": row[3]}
                limit = quota_map.get(usage_type, float('inf'))
                return current < limit
        except Exception:
            return True

    def set_quota(self, tenant_id: str, max_tool_calls: int = 10000,
                  max_tokens: int = 1000000, max_compute_sec: int = 3600):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO quotas VALUES (?, ?, ?, ?)",
                (tenant_id, max_tool_calls, max_tokens, max_compute_sec),
            )

    def get_report(self, tenant_id: str) -> Dict:
        usage = self.get_usage(tenant_id)
        return {"tenant_id": tenant_id, "usage": usage, "period": "last_30d"}


# Global instance
credits_engine = CreditsEngine()
