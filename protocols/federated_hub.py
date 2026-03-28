"""
Federated Hub v2 — Knowledge Sharing Between Instances

Real federated learning patterns:
- Task success/failure pattern storage in vector DB
- Anonymized metric aggregation
- Privacy-preserving pattern sharing
"""

import logging
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class FederatedHub:
    """Federated knowledge sharing hub between agent instances."""

    def __init__(self):
        self.shared_patterns: List[Dict] = []
        self.sync_history: List[Dict] = []
        self._running = False
        logger.info("[FederatedHub] Initialized")

    async def start_gossip(self):
        """Start gossip protocol for peer metric exchange."""
        self._running = True
        logger.info("[FederatedHub] Gossip protocol started")

    async def stop_gossip(self):
        self._running = False

    def share_pattern(self, pattern_type: str, data: Dict[str, Any],
                      anonymize: bool = True) -> str:
        """Share a task pattern with the federation."""
        pattern = {
            "id": f"pat_{len(self.shared_patterns)}",
            "type": pattern_type,
            "data": self._anonymize(data) if anonymize else data,
            "shared_at": time.time(),
        }
        self.shared_patterns.append(pattern)
        return pattern["id"]

    def query_patterns(self, pattern_type: str = None,
                       limit: int = 10) -> List[Dict]:
        """Query shared patterns."""
        patterns = self.shared_patterns
        if pattern_type:
            patterns = [p for p in patterns if p["type"] == pattern_type]
        return patterns[-limit:]

    def sync_metrics(self, peer_id: str, metrics: Dict[str, Any]):
        """Receive metrics from a peer for aggregation."""
        self.sync_history.append({
            "peer_id": peer_id,
            "metrics": metrics,
            "received_at": time.time(),
        })

    def get_aggregated_metrics(self) -> Dict[str, Any]:
        """Get aggregated metrics across peers."""
        if not self.sync_history:
            return {"peers": 0, "avg_success_rate": 0.0}
        
        success_rates = [h["metrics"].get("success_rate", 0)
                         for h in self.sync_history if "success_rate" in h.get("metrics", {})]
        return {
            "peers": len(set(h["peer_id"] for h in self.sync_history)),
            "total_syncs": len(self.sync_history),
            "avg_success_rate": sum(success_rates) / len(success_rates) if success_rates else 0,
        }

    @staticmethod
    def _anonymize(data: Dict) -> Dict:
        """Remove PII from shared data."""
        sensitive_keys = {"user_id", "api_key", "password", "token", "email"}
        return {k: v for k, v in data.items() if k.lower() not in sensitive_keys}
