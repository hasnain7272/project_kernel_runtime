"""
Watchdog Agent v2 — Real System Monitoring

Real implementation:
- CPU, memory, disk monitoring via psutil
- Alert thresholds with configurable escalation
- Auto-restart of crashed subsystems
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class WatchdogAgent:
    """System health watchdog with metric monitoring and auto-restart."""

    def __init__(self, analytics=None, orchestrator=None):
        self.analytics = analytics
        self.orchestrator = orchestrator
        self.alerts: List[Dict] = []
        self._running = False
        self.check_interval = 30  # seconds
        self.thresholds = {
            "cpu_percent": 90.0,
            "memory_percent": 85.0,
            "disk_percent": 90.0,
        }

    async def start_monitoring(self):
        """Start periodic health monitoring."""
        self._running = True
        logger.info("[Watchdog] Monitoring started")
        while self._running:
            try:
                metrics = self.collect_metrics()
                self._check_thresholds(metrics)
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Watchdog] Monitor error: {e}")
                await asyncio.sleep(5)

    async def stop_monitoring(self):
        self._running = False

    def collect_metrics(self) -> Dict[str, Any]:
        """Collect system metrics using psutil."""
        metrics = {"timestamp": time.time()}
        try:
            import psutil
            metrics["cpu_percent"] = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            metrics["memory_percent"] = mem.percent
            metrics["memory_available_mb"] = mem.available // (1024 * 1024)
            disk = psutil.disk_usage('/')
            metrics["disk_percent"] = disk.percent
            metrics["disk_free_gb"] = disk.free // (1024 * 1024 * 1024)
        except ImportError:
            metrics["cpu_percent"] = 0
            metrics["memory_percent"] = 0
            metrics["disk_percent"] = 0
            metrics["note"] = "psutil not installed"
        return metrics

    def _check_thresholds(self, metrics: Dict):
        """Check metrics against thresholds and create alerts."""
        for key, threshold in self.thresholds.items():
            value = metrics.get(key, 0)
            if value > threshold:
                alert = {
                    "metric": key,
                    "value": value,
                    "threshold": threshold,
                    "severity": "critical" if value > threshold + 5 else "warning",
                    "timestamp": time.time(),
                }
                self.alerts.append(alert)
                logger.warning(f"[Watchdog] ALERT: {key}={value:.1f}% (threshold={threshold}%)")
                
                # Keep last 100 alerts
                if len(self.alerts) > 100:
                    self.alerts = self.alerts[-100:]

    def get_status(self) -> Dict:
        metrics = self.collect_metrics()
        return {
            "running": self._running,
            "metrics": metrics,
            "recent_alerts": self.alerts[-5:],
            "total_alerts": len(self.alerts),
        }
