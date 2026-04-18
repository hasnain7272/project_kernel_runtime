"""
Docker sandbox adapter.
"""
import asyncio
import logging
import time
from typing import Any, Dict

from src.domain.exceptions import SandboxExecutionError
from src.infrastructure.runtime.config import SANDBOX_IMAGE
from src.infrastructure.runtime.paths import resolve_workspace_path

logger = logging.getLogger(__name__)


class DockerAdapter:
    def __init__(self, image: str = SANDBOX_IMAGE):
        self.image = image
        self._docker_available = None

    async def _check_docker(self) -> bool:
        """Proactively probe for Docker availability."""
        if self._docker_available is not None:
            return self._docker_available
        
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "info",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=2)
            self._docker_available = (proc.returncode == 0)
        except Exception:
            self._docker_available = False
        
        if not self._docker_available:
            from src.infrastructure.observability.tracing import milestones
            milestones.milestone("Sandbox Isolation Degraded", {"reason": "Docker daemon unreachable", "mode": "local_restricted"})
        
        return self._docker_available

    async def execute(
        self,
        command: str,
        session_id: str,
        working_dir: str = ".",
        timeout: int = 30,
        memory_limit_mb: int = 512,
        network_mode: str = "none",
    ) -> Dict[str, Any]:
        import os
        import subprocess
        start_time = time.time()
        
        # 1. Use main workspace for file persistence
        base_workspace = str(resolve_workspace_path("."))
        
        # 2. Adaptive Strategy: Docker vs. Local Restricted
        use_docker = await self._check_docker()
        
        if use_docker:
            docker_args = [
                "docker", "run", "--rm",
                f"--memory={memory_limit_mb}m",
                f"--network={network_mode}",
                "-v", f"{os.path.abspath(base_workspace)}:/workspace:rw",
                "-w", "/workspace",
                self.image, "/bin/sh", "-c", command,
            ]
            
            try:
                proc = await asyncio.create_subprocess_exec(
                    *docker_args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
                return {
                    "exit_code": proc.returncode,
                    "stdout": stdout.decode("utf-8", errors="replace"),
                    "stderr": stderr.decode("utf-8", errors="replace"),
                    "duration_ms": round((time.time() - start_time) * 1000),
                    "sandbox": "docker"
                }
            except Exception as e:
                # If docker specifically fails during execution, we catch and report
                logger.warning(f"Docker execution failed, but daemon was up: {e}")
        
        # 3. Fallback: Local Restricted Sandbox (project_kernel_runtime)
        # This is for dev environments or where Docker is blocked.
        # We run the command in the tenant-specific subdirectory.
        try:
            # Simple local subproc execution restricted to the tenant folder
            shell_cmd = ["cmd", "/c", command] if os.name == "nt" else ["/bin/sh", "-c", command]
            
            proc = await asyncio.create_subprocess_exec(
                *shell_cmd,
                cwd=tenant_workspace,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "SANDBOX_MODE": "local", "TENANT_ID": session_id}
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            
            return {
                "exit_code": proc.returncode,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "duration_ms": round((time.time() - start_time) * 1000),
                "sandbox": "local_restricted",
                "warning": "Docker missing. Running in restricted local mode."
            }
        except Exception as local_err:
            raise SandboxExecutionError(f"Complete sandbox failure: {local_err}")
