"""Data models for Kubernetes sandbox execution."""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from .config import (
    DEFAULT_CPU_LIMIT,
    DEFAULT_CPU_REQUEST,
    DEFAULT_MEMORY_LIMIT,
    DEFAULT_MEMORY_REQUEST,
    DEFAULT_TIMEOUT,
    K8S_IMAGE,
)


@dataclass
class SandboxResult:
    """Result of sandboxed execution."""
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    job_name: str
    pod_name: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    resource_usage: Optional[Dict[str, Any]] = None


@dataclass
class SandboxConfig:
    """Configuration for sandbox execution."""
    command: str
    working_dir: str = "/workspace"
    timeout: int = DEFAULT_TIMEOUT
    cpu_limit: str = DEFAULT_CPU_LIMIT
    memory_limit: str = DEFAULT_MEMORY_LIMIT
    cpu_request: str = DEFAULT_CPU_REQUEST
    memory_request: str = DEFAULT_MEMORY_REQUEST
    image: str = K8S_IMAGE
    environment: Optional[Dict[str, str]] = None
    allow_network: bool = False
    session_id: Optional[str] = None
    user_id: Optional[str] = None
