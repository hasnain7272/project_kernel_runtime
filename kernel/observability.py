"""
Observability v2 — Structured Logging + Decision Tracing

Upgraded from 80-line tracer to full observability stack:
- structlog configuration (json + console output)
- Decision tree tracing (preserved from v1)
- Prometheus-compatible metrics export
- Request ID tracking via context vars
"""

import json
import logging
import os
import time
import uuid
from contextvars import ContextVar
from typing import Any, Dict, List, Optional

# Context variable for request tracking
request_id_var: ContextVar[str] = ContextVar('request_id', default='')

logger = logging.getLogger(__name__)


# ============================================================================
# Structlog Configuration
# ============================================================================

def configure_logging(log_level: str = "INFO", json_output: bool = False):
    """Configure structured logging for the runtime."""
    try:
        import structlog
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
        ]
        
        if json_output:
            processors.append(structlog.processors.JSONRenderer())
        else:
            processors.append(structlog.dev.ConsoleRenderer())

        structlog.configure(
            processors=processors,
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, log_level.upper(), logging.INFO)
            ),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
        logger.info(f"[Observability] structlog configured (level={log_level})")
    except ImportError:
        logging.basicConfig(level=getattr(logging, log_level.upper(), logging.INFO))
        logger.info("[Observability] Using stdlib logging (structlog not installed)")


def get_logger(name: str = ""):
    """Get a structlog logger instance."""
    try:
        import structlog
        return structlog.get_logger(name)
    except ImportError:
        return logging.getLogger(name)


# ============================================================================
# Decision Tracing (preserved from v1)
# ============================================================================

class DecisionNode:
    """A single step in an agent's reasoning path."""
    def __init__(self, step_id: str, logic: str, parent_id: Optional[str] = None):
        self.step_id = step_id
        self.logic = logic
        self.parent_id = parent_id
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.metadata: Dict[str, Any] = {}
        self.children: List['DecisionNode'] = []


class NeuralTracer:
    """Traces reasoning and decision-making causality."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.root_nodes: List[DecisionNode] = []
        self.active_nodes: Dict[str, DecisionNode] = {}

    def start_decision(self, logic: str, parent_id: Optional[str] = None) -> str:
        node_id = str(uuid.uuid4())[:8]
        node = DecisionNode(node_id, logic, parent_id)
        self.active_nodes[node_id] = node
        
        if parent_id and parent_id in self.active_nodes:
            self.active_nodes[parent_id].children.append(node)
        else:
            self.root_nodes.append(node)
        
        logger.debug(f"[TRACE] Decision {node_id}: {logic}")
        return node_id

    def end_decision(self, node_id: str, result_summary: str,
                     metadata: Optional[Dict] = None):
        if node_id in self.active_nodes:
            node = self.active_nodes[node_id]
            node.end_time = time.time()
            node.metadata = {**(metadata or {}), "summary": result_summary}

    def get_full_trace(self) -> List[Dict[str, Any]]:
        def serialize_node(node: DecisionNode):
            duration = 0
            if node.end_time and node.start_time:
                duration = (node.end_time - node.start_time) * 1000
            return {
                "id": node.step_id, "logic": node.logic,
                "duration_ms": round(duration, 2),
                "metadata": node.metadata,
                "children": [serialize_node(c) for c in node.children],
            }
        return [serialize_node(root) for root in self.root_nodes]

    def save_trace(self, path: str):
        from datetime import datetime, timezone
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        with open(path, "w") as f:
            json.dump({
                "session_id": self.session_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "trace": self.get_full_trace(),
            }, f, indent=2)


# ============================================================================
# Metrics
# ============================================================================

class MetricsCollector:
    """Simple metrics collection for Prometheus-compatible export."""

    def __init__(self):
        self.counters: Dict[str, int] = {}
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = {}

    def inc(self, name: str, value: int = 1, labels: Dict = None):
        key = self._key(name, labels)
        self.counters[key] = self.counters.get(key, 0) + value

    def set(self, name: str, value: float, labels: Dict = None):
        key = self._key(name, labels)
        self.gauges[key] = value

    def observe(self, name: str, value: float, labels: Dict = None):
        key = self._key(name, labels)
        if key not in self.histograms:
            self.histograms[key] = []
        self.histograms[key].append(value)
        # Keep last 1000 observations
        if len(self.histograms[key]) > 1000:
            self.histograms[key] = self.histograms[key][-1000:]

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus text format."""
        lines = []
        for name, value in self.counters.items():
            lines.append(f"{name} {value}")
        for name, value in self.gauges.items():
            lines.append(f"{name} {value}")
        for name, values in self.histograms.items():
            if values:
                avg = sum(values) / len(values)
                lines.append(f"{name}_avg {avg:.4f}")
                lines.append(f"{name}_count {len(values)}")
        return "\n".join(lines)

    @staticmethod
    def _key(name: str, labels: Dict = None) -> str:
        if not labels:
            return name
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"


# Global metrics instance
metrics = MetricsCollector()
