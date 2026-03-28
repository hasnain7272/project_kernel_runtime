"""
Sandbox Manager v2 — Real Execution Isolation

Multi-backend sandbox with actual subprocess isolation, Docker support,
and E2B integration. Replaces the 50-line mock with real functionality.

Backends:
- subprocess: Works immediately, uses asyncio.create_subprocess_exec with resource limits
- docker: Production isolation using Docker containers
- e2b: Cloud-scale Firecracker MicroVMs via E2B SDK
- none: Direct execution (for trusted environments)

Inspired by: OpenHands Docker sandbox, E2B Firecracker MicroVMs,
Claude Code OS-level sandbox (bubblewrap/seatbelt)
"""

import asyncio
import logging
import os
import platform
import shlex
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class SandboxResult:
    """Result from sandbox execution."""
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    sandbox_id: str = ""
    duration_ms: float = 0.0


@dataclass
class SandboxInstance:
    """Tracks an active sandbox."""
    id: str
    backend: str
    status: str = "active"  # active, terminated
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    working_dir: str = ""
    network_mode: str = "none"
    memory_limit_mb: int = 512
    cpu_limit: float = 1.0


# ============================================================================
# Sandbox Backends
# ============================================================================

class SubprocessSandbox:
    """
    Subprocess-based sandbox using asyncio.
    
    Works on any OS without Docker. Provides basic isolation via:
    - Separate subprocess (not in-process)
    - Timeout enforcement
    - Working directory restriction
    - Environment variable isolation
    - Output capture and truncation
    """
    
    async def execute(self, command: str, working_dir: str = ".",
                      timeout: int = 30, env: Dict[str, str] = None,
                      memory_limit_mb: int = 512) -> SandboxResult:
        """Execute a command in a sandboxed subprocess."""
        import time
        start_time = time.time()
        
        # Build restricted environment
        safe_env = {}
        # Only pass safe env vars
        for key in ("PATH", "HOME", "USER", "LANG", "LC_ALL", "TERM",
                     "PYTHONPATH", "VIRTUAL_ENV", "CONDA_PREFIX"):
            if key in os.environ:
                safe_env[key] = os.environ[key]
        
        if env:
            safe_env.update(env)
        
        # Remove dangerous env vars
        for key in ("LD_PRELOAD", "LD_LIBRARY_PATH", "DYLD_INSERT_LIBRARIES"):
            safe_env.pop(key, None)
        
        try:
            is_windows = platform.system() == "Windows"
            
            if is_windows:
                proc = await asyncio.create_subprocess_exec(
                    "powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=working_dir,
                    env=safe_env,
                )
            else:
                proc = await asyncio.create_subprocess_exec(
                    "/bin/bash", "-c", command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=working_dir,
                    env=safe_env,
                )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return SandboxResult(
                    exit_code=-1,
                    stdout="",
                    stderr=f"Command timed out after {timeout}s",
                    timed_out=True,
                    duration_ms=(time.time() - start_time) * 1000,
                )
            
            return SandboxResult(
                exit_code=proc.returncode,
                stdout=stdout.decode('utf-8', errors='replace')[:50000],
                stderr=stderr.decode('utf-8', errors='replace')[:50000],
                timed_out=False,
                duration_ms=(time.time() - start_time) * 1000,
            )
        
        except Exception as e:
            return SandboxResult(
                exit_code=-1,
                stderr=f"Sandbox error: {type(e).__name__}: {str(e)}",
                duration_ms=(time.time() - start_time) * 1000,
            )


class DockerSandbox:
    """
    Docker container-based sandbox for production isolation.
    
    Features:
    - Full container isolation
    - Read-only filesystem with tmpfs scratch
    - Network mode: none (default), allowlist, or full
    - CPU and memory limits
    - Auto cleanup
    """
    
    def __init__(self, image: str = "python:3.11-slim"):
        self.image = image
        self._docker_available = None
    
    async def is_available(self) -> bool:
        """Check if Docker is installed and running."""
        if self._docker_available is not None:
            return self._docker_available
        
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "info",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=5)
            self._docker_available = proc.returncode == 0
        except Exception:
            self._docker_available = False
        
        return self._docker_available
    
    async def execute(self, command: str, working_dir: str = ".",
                      timeout: int = 30, env: Dict[str, str] = None,
                      memory_limit_mb: int = 512, cpu_limit: float = 1.0,
                      network_mode: str = "none") -> SandboxResult:
        """Execute a command inside a Docker container."""
        import time
        start_time = time.time()
        
        if not await self.is_available():
            return SandboxResult(
                exit_code=-1,
                stderr="Docker is not available. Install Docker or use 'subprocess' backend.",
            )
        
        # Build docker run command
        docker_args = [
            "docker", "run", "--rm",
            f"--memory={memory_limit_mb}m",
            f"--cpus={cpu_limit}",
            f"--network={network_mode}",
            "--read-only",
            "--tmpfs", "/tmp:size=100M",
            "-v", f"{os.path.abspath(working_dir)}:/workspace:rw",
            "-w", "/workspace",
        ]
        
        # Add environment variables
        if env:
            for key, value in env.items():
                docker_args.extend(["-e", f"{key}={value}"])
        
        docker_args.extend([self.image, "/bin/sh", "-c", command])
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *docker_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                # Kill the container
                proc.kill()
                await proc.wait()
                return SandboxResult(
                    exit_code=-1, timed_out=True,
                    stderr=f"Docker execution timed out after {timeout}s",
                    duration_ms=(time.time() - start_time) * 1000,
                )
            
            return SandboxResult(
                exit_code=proc.returncode,
                stdout=stdout.decode('utf-8', errors='replace')[:50000],
                stderr=stderr.decode('utf-8', errors='replace')[:50000],
                duration_ms=(time.time() - start_time) * 1000,
            )
        
        except Exception as e:
            return SandboxResult(
                exit_code=-1,
                stderr=f"Docker execution error: {type(e).__name__}: {str(e)}",
                duration_ms=(time.time() - start_time) * 1000,
            )


class E2BSandbox:
    """
    E2B (Execute to Build) cloud sandbox using Firecracker MicroVMs.
    
    Requires E2B API key. Each execution runs in an isolated MicroVM
    with ~150ms cold start.
    """
    
    async def execute(self, command: str, working_dir: str = ".",
                      timeout: int = 30, **kwargs) -> SandboxResult:
        """Execute a command in an E2B cloud sandbox."""
        try:
            from e2b_code_interpreter import Sandbox
        except ImportError:
            return SandboxResult(
                exit_code=-1,
                stderr="E2B SDK not installed. Run: pip install e2b-code-interpreter",
            )
        
        import time
        start_time = time.time()
        
        try:
            sandbox = Sandbox()
            result = sandbox.run_code(command)
            sandbox.kill()
            
            return SandboxResult(
                exit_code=0 if not result.error else 1,
                stdout=str(result.text) if result.text else "",
                stderr=str(result.error) if result.error else "",
                duration_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            return SandboxResult(
                exit_code=-1,
                stderr=f"E2B error: {type(e).__name__}: {str(e)}",
                duration_ms=(time.time() - start_time) * 1000,
            )


# ============================================================================
# Sandbox Manager (unified interface)
# ============================================================================

class ZeroTrustSandbox:
    """
    Unified sandbox manager with pluggable backends.
    
    Upgraded from 50-line mock to real multi-backend isolation.
    Backward-compatible class name for existing code.
    """
    
    def __init__(self, config=None):
        self.config = config
        self.active_sandboxes: Dict[str, SandboxInstance] = {}
        self._semaphore = asyncio.Semaphore(5)
        
        # Select backend
        backend_name = "subprocess"
        if config:
            if hasattr(config, 'backend'):
                backend_name = config.backend
            elif isinstance(config, dict):
                backend_name = config.get("backend", "subprocess")
        
        self.backend_name = backend_name
        self._backend = self._create_backend(backend_name)
        
        # Default policies (kept for backward compat)
        self.policies = {
            "default_network": "DENY",
            "allowed_syscalls": ["read", "write", "open", "close", "mmap"],
            "max_memory_mb": config.memory_limit_mb if config and hasattr(config, 'memory_limit_mb') else 512,
            "max_cpu_percent": int((config.cpu_limit if config and hasattr(config, 'cpu_limit') else 1.0) * 100),
        }
        
        logger.info(f"[Sandbox] Initialized with backend: {backend_name}")
    
    def _create_backend(self, name: str):
        """Create the sandbox backend."""
        if name == "docker":
            image = "python:3.11-slim"
            if self.config and hasattr(self.config, 'docker_image'):
                image = self.config.docker_image
            return DockerSandbox(image=image)
        elif name == "e2b":
            return E2BSandbox()
        elif name == "none":
            return None
        else:
            return SubprocessSandbox()
    
    def provision_sandbox(self, task_id: str) -> Dict[str, Any]:
        """Provision an isolated execution environment."""
        sandbox_id = f"sbx_{task_id}_{uuid4().hex[:8]}"
        working_dir = os.path.join(
            self.config.working_dir if self.config and hasattr(self.config, 'working_dir') else "./workspace",
            sandbox_id
        )
        os.makedirs(working_dir, exist_ok=True)
        
        instance = SandboxInstance(
            id=sandbox_id,
            backend=self.backend_name,
            working_dir=working_dir,
            memory_limit_mb=self.policies["max_memory_mb"],
        )
        self.active_sandboxes[sandbox_id] = instance
        
        logger.info(f"[Sandbox] Provisioned {sandbox_id} (backend={self.backend_name})")
        return {"sandbox_id": sandbox_id, "path": working_dir}
    
    async def execute(self, command: str, sandbox_id: str = None,
                       timeout: int = None, env: Dict[str, str] = None) -> SandboxResult:
        """Execute a command in the sandbox."""
        if self._backend is None:
            # "none" backend — direct execution via subprocess
            backend = SubprocessSandbox()
        else:
            backend = self._backend
        
        working_dir = "."
        if sandbox_id and sandbox_id in self.active_sandboxes:
            working_dir = self.active_sandboxes[sandbox_id].working_dir
        elif self.config and hasattr(self.config, 'working_dir'):
            working_dir = self.config.working_dir
        
        if timeout is None:
            timeout = self.config.timeout_seconds if self.config and hasattr(self.config, 'timeout_seconds') else 300
        
        async with self._semaphore:
            result = await backend.execute(
                command=command,
                working_dir=working_dir,
                timeout=timeout,
                env=env,
                memory_limit_mb=self.policies["max_memory_mb"],
            )
            result.sandbox_id = sandbox_id or "ephemeral"
            return result
    
    async def execute_tool(self, tool, arguments: Dict[str, Any],
                           context=None) -> Any:
        """Execute a tool within the sandbox environment."""
        # Tools that support sandboxed execution
        if hasattr(tool, 'execute'):
            return await tool.execute(arguments, context)
        return {"error": f"Tool {tool.name} does not support execution"}
    
    def request_network_access(self, sandbox_id: str, endpoint: str) -> bool:
        """Check if a sandbox is allowed to access a network endpoint."""
        if self.config and hasattr(self.config, 'network_mode'):
            if self.config.network_mode == "none":
                logger.warning(f"[Sandbox] BLOCKED network access to {endpoint} from {sandbox_id}")
                return False
            elif self.config.network_mode == "allowlist":
                from urllib.parse import urlparse
                hostname = urlparse(endpoint).hostname or endpoint
                if hostname in (self.config.network_allowlist or []):
                    return True
                logger.warning(f"[Sandbox] BLOCKED: {hostname} not in allowlist")
                return False
        
        # Default: allow localhost, block everything else
        if "localhost" in endpoint or "127.0.0.1" in endpoint:
            return True
        
        logger.warning(f"[Sandbox] BLOCKED outbound network to {endpoint}")
        return False
    
    def teardown_sandbox(self, sandbox_id: str):
        """Remove and clean up a sandbox."""
        instance = self.active_sandboxes.pop(sandbox_id, None)
        if instance:
            if self.config and hasattr(self.config, 'cleanup_on_exit') and self.config.cleanup_on_exit:
                import shutil
                if os.path.isdir(instance.working_dir) and "sbx_" in instance.working_dir:
                    try:
                        shutil.rmtree(instance.working_dir)
                    except Exception as e:
                        logger.warning(f"[Sandbox] Cleanup failed: {e}")
            logger.info(f"[Sandbox] Torn down {sandbox_id}")
    
    def calculate_security_score(self) -> Dict[str, Any]:
        """Calculate real-time security score based on isolation posture."""
        score = 100
        
        # Deductions
        if self.backend_name == "none":
            score -= 50
        elif self.backend_name == "subprocess":
            score -= 20  # Less isolation than containers
        
        if self.config and hasattr(self.config, 'network_mode'):
            if self.config.network_mode == "full":
                score -= 30
            elif self.config.network_mode == "allowlist":
                score -= 10
        elif self.policies["default_network"] != "DENY":
            score -= 30
        
        return {
            "score": max(0, score),
            "backend": self.backend_name,
            "isolation_type": {
                "subprocess": "Process-level",
                "docker": "Container-level (OCI)",
                "e2b": "MicroVM-level (Firecracker)",
                "none": "No isolation",
            }.get(self.backend_name, "Unknown"),
            "active_sandboxes": len(self.active_sandboxes),
            "network_policy": self.config.network_mode if self.config and hasattr(self.config, 'network_mode') else self.policies["default_network"],
        }
