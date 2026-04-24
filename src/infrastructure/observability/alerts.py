"""Production alerting configuration."""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class AlertManager:
    """Manage production alerts."""
    
    SEVERITY_INFO = "info"
    SEVERITY_WARNING = "warning"
    SEVERITY_CRITICAL = "critical"
    
    def __init__(self):
        self._webhook_url = None
        self._slack_channel = None
    
    async def send_alert(self, 
        title: str, 
        message: str, 
        severity: str = SEVERITY_INFO,
        metadata: Dict[str, Any] = None
    ):
        """Send alert to configured channels."""
        alert = {
            "title": title,
            "message": message,
            "severity": severity,
            "metadata": metadata or {},
        }
        
        # Log alert
        log_method = {
            self.SEVERITY_INFO: logger.info,
            self.SEVERITY_WARNING: logger.warning,
            self.SEVERITY_CRITICAL: logger.error,
        }.get(severity, logger.info)
        
        log_method(f"[ALERT] {title}: {message}")
        
        # TODO: Implement webhook/Slack/PagerDuty integration
        # if self._webhook_url:
        #     await self._send_webhook(alert)
    
    async def alert_high_error_rate(self, error_rate: float, threshold: float = 0.05):
        """Alert on high error rate."""
        if error_rate > threshold:
            await self.send_alert(
                title="High Error Rate",
                message=f"Error rate is {error_rate:.2%}, threshold is {threshold:.2%}",
                severity=self.SEVERITY_WARNING,
                metadata={"error_rate": error_rate, "threshold": threshold}
            )
    
    async def alert_high_latency(self, latency: float, threshold: float = 1.0):
        """Alert on high latency."""
        if latency > threshold:
            await self.send_alert(
                title="High Latency",
                message=f"P95 latency is {latency:.2f}s, threshold is {threshold}s",
                severity=self.SEVERITY_WARNING,
                metadata={"latency": latency, "threshold": threshold}
            )
    
    async def alert_queue_depth(self, queue_name: str, depth: int, threshold: int = 1000):
        """Alert on queue depth."""
        if depth > threshold:
            await self.send_alert(
                title="High Queue Depth",
                message=f"Queue {queue_name} has {depth} items, threshold is {threshold}",
                severity=self.SEVERITY_WARNING,
                metadata={"queue": queue_name, "depth": depth, "threshold": threshold}
            )
    
    async def alert_circuit_breaker_open(self, service: str):
        """Alert on circuit breaker open."""
        await self.send_alert(
            title="Circuit Breaker Open",
            message=f"Circuit breaker for {service} is open",
            severity=self.SEVERITY_CRITICAL,
            metadata={"service": service}
        )
    
    async def alert_disk_space(self, usage_percent: float, threshold: float = 85.0):
        """Alert on disk space."""
        if usage_percent > threshold:
            await self.send_alert(
                title="Low Disk Space",
                message=f"Disk usage is {usage_percent:.1f}%, threshold is {threshold}%",
                severity=self.SEVERITY_WARNING,
                metadata={"usage": usage_percent, "threshold": threshold}
            )
    
    async def alert_memory_usage(self, usage_percent: float, threshold: float = 90.0):
        """Alert on memory usage."""
        if usage_percent > threshold:
            await self.send_alert(
                title="High Memory Usage",
                message=f"Memory usage is {usage_percent:.1f}%, threshold is {threshold}%",
                severity=self.SEVERITY_WARNING,
                metadata={"usage": usage_percent, "threshold": threshold}
            )


# Singleton instance
_alert_manager = None

def get_alert_manager() -> AlertManager:
    """Get alert manager singleton."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager