"""Kubernetes Sandbox module - exports and factory.

This module provides enterprise-grade sandbox execution using Kubernetes Jobs.
It replaces direct docker subprocess calls with secure, multi-tenant isolation.

Security Features:
- Runs as non-root user
- Read-only root filesystem
- EmptyDir volumes for ephemeral storage
- Network policies (no outbound by default)
- Resource quotas (CPU/Memory)
- Security contexts (drop all capabilities)
- Automatic job cleanup
"""
import logging
import os
from typing import Optional

from .config import DEFAULT_TIMEOUT
from .exceptions import SandboxExecutionError
from .executor import KubernetesSandboxExecutor
from .local import LocalSandboxExecutor
from .models import SandboxConfig, SandboxResult

__all__ = [
    "KubernetesSandboxExecutor",
    "LocalSandboxExecutor",
    "SandboxConfig",
    "SandboxResult",
    "SandboxExecutionError",
    "get_sandbox_executor",
    "execute_sandboxed",
]

logger = logging.getLogger(__name__)

_sandbox_executor: Optional[KubernetesSandboxExecutor] = None


async def get_sandbox_executor():
    """Get the appropriate sandbox executor."""
    global _sandbox_executor

    if _sandbox_executor is None:
        # Check if we're in Kubernetes
        token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
        if os.path.exists(token_path):
            _sandbox_executor = KubernetesSandboxExecutor()
            logger.info("[Sandbox] Using Kubernetes executor")
        elif os.environ.get("KUBERNETES_SERVICE_HOST"):
            _sandbox_executor = KubernetesSandboxExecutor()
            logger.info("[Sandbox] Using Kubernetes executor (env detected)")
        else:
            _sandbox_executor = LocalSandboxExecutor()
            logger.warning("[Sandbox] Using local executor (DEVELOPMENT ONLY)")

    return _sandbox_executor


async def execute_sandboxed(
    command: str,
    working_dir: str = "/workspace",
    timeout: int = DEFAULT_TIMEOUT,
    **kwargs
) -> SandboxResult:
    """Execute command in sandbox."""
    executor = await get_sandbox_executor()
    config = SandboxConfig(
        command=command,
        working_dir=working_dir,
        timeout=timeout,
        **kwargs
    )
    return await executor.execute(config)
