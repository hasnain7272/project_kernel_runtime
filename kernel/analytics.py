"""
Analytics Service: Performance tracking and bottleneck identification.
Part of Phase 9-10 (Enterprise Features).
"""

import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TaskMetric:
    task_id: str
    start_time: float
    end_time: Optional[float] = None
    step_timings: Dict[str, float] = field(default_factory=dict)
    error_count: int = 0
    resource_usage: Dict[str, Any] = field(default_factory=dict)


class AnalyticsService:
    """Tracks and analyzes system performance metrics."""

    def __init__(self):
        self.metrics: Dict[str, TaskMetric] = {}
        self.system_uptime_start = time.time()

    def start_task_tracking(self, task_id: str):
        """Initialize tracking for a new task."""
        self.metrics[task_id] = TaskMetric(task_id=task_id, start_time=time.time())

    def record_step_timing(self, task_id: str, step_id: str, duration: float):
        """Record how long a specific step took."""
        if task_id in self.metrics:
            self.metrics[task_id].step_timings[step_id] = duration

    def end_task_tracking(self, task_id: str, success: bool = True):
        """Finalize tracking for a task."""
        if task_id in self.metrics:
            metric = self.metrics[task_id]
            metric.end_time = time.time()
            if not success:
                metric.error_count += 1

    def get_bottlenecks(self) -> List[Dict[str, Any]]:
        """Identify slow steps across all tasks."""
        all_steps = {}
        for metric in self.metrics.values():
            for step_id, duration in metric.step_timings.items():
                if step_id not in all_steps:
                    all_steps[step_id] = []
                all_steps[step_id].append(duration)
        
        bottlenecks = []
        for step_id, timings in all_steps.items():
            avg = sum(timings) / len(timings)
            if avg > 5.0:  # Threshold for "slow" step
                bottlenecks.append({
                    "step_id": step_id,
                    "avg_duration": avg,
                    "count": len(timings)
                })
        
        return sorted(bottlenecks, key=lambda x: x['avg_duration'], reverse=True)

    def get_task_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Retrieve metrics for all tasks currently being tracked."""
        serialized = {}
        for task_id, metric in self.metrics.items():
            avg_duration = 0
            if metric.step_timings:
                avg_duration = sum(metric.step_timings.values()) / len(metric.step_timings)
            
            serialized[task_id] = {
                "start_time": metric.start_time,
                "end_time": metric.end_time,
                "error_count": metric.error_count,
                "avg_duration": avg_duration
            }
        return serialized

    def get_system_summary(self) -> Dict[str, Any]:
        """Overall system efficiency summary."""
        total_tasks = len(self.metrics)
        completed_tasks = len([m for m in self.metrics.values() if m.end_time is not None])
        error_rate = sum(m.error_count for m in self.metrics.values()) / max(1, total_tasks)
        
        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "error_rate": error_rate,
            "uptime": time.time() - self.system_uptime_start
        }
