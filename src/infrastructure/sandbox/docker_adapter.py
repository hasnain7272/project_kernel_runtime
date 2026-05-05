"""
Sandbox Adapter — Fail-Closed Execution Isolation

Production: Runs commands in Docker containers with resource limits.
Development: Runs commands locally but ONLY when ALLOW_ANON_LOCAL=true.
SaaS Production: Refuses execution entirely if Docker is unavailable.

The adapter NEVER silently falls back to host execution in production.
"""
import asyncio
import logging
import os
import time
from typing import Any, Dict

from src.domain.exceptions import SandboxExecutionError
from src.infrastructure.runtime.config import SANDBOX_IMAGE, ALLOW_ANON_LOCAL
from src.infrastructure.runtime.paths import get_session_root, resolve_workspace_path

logger = logging.getLogger(__name__)


class SandboxAdapter:
    """Unified sandbox for command execution with fail-closed security."""

    def __init__(self, image: str = SANDBOX_IMAGE):
        self.image = image
        self._docker_available: bool | None = None

    async def _check_docker(self) -> bool:
        """Probe Docker daemon availability (cached after first check)."""
        if self._docker_available is not None:
            return self._docker_available

        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "info",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=3)
            self._docker_available = proc.returncode == 0
        except Exception:
            self._docker_available = False

        if not self._docker_available:
            logger.warning("[Sandbox] Docker daemon not reachable")

        return self._docker_available

    async def execute(
        self,
        command: str,
        session_id: str,
        tenant_id: str,
        working_dir: str = ".",
        timeout: int = 30,
        memory_limit_mb: int = 512,
        network_mode: str = "none",
    ) -> Dict[str, Any]:
        start_time = time.time()
        session_root = get_session_root(tenant_id, session_id)
        session_root.mkdir(parents=True, exist_ok=True)
        working_path = resolve_workspace_path(
            working_dir,
            session_id=session_id,
            tenant_id=tenant_id,
        )
        try:
            relative_workdir = working_path.relative_to(session_root)
            container_workdir = "/workspace"
            if str(relative_workdir) not in {"", "."}:
                container_workdir = f"/workspace/{relative_workdir.as_posix()}"
        except ValueError:
            raise SandboxExecutionError(f"Working directory escapes session root: {working_path}")
        
        if await self._check_docker():
            return await self._run_in_docker(
                command,
                str(session_root),
                container_workdir,
                memory_limit_mb,
                network_mode,
                timeout,
                start_time,
            )

        if ALLOW_ANON_LOCAL:
            logger.warning("[Sandbox] DEV MODE: Running locally (no Docker)")
            return await self._run_local_dev(
                command,
                str(working_path),
                timeout,
                start_time,
            )

        raise SandboxExecutionError(
            "Docker is required for command execution in production. "
            "Set ALLOW_ANON_LOCAL=true for local development only."
        )

    async def _run_in_docker(
        self,
        command: str,
        workspace: str,
        container_workdir: str,
        memory_mb: int,
        network: str,
        timeout: int,
        t0: float,
    ) -> Dict[str, Any]:
        """Execute in an isolated Docker container."""
        # Optional: Enable Docker-outside-of-Docker (DooD)
        enable_dood = os.environ.get("ENABLE_SANDBOX_DOCKER", "false").lower() == "true"
        docker_socket = os.environ.get("DOCKER_SOCKET_PATH", "/var/run/docker.sock")

        # Set network mode
        actual_network = "bridge" if enable_dood else network

        docker_args = [
            "docker", "run", "--rm",
            f"--memory={memory_mb}m",
            f"--network={actual_network}",
            "--pids-limit", "256",
        ]

        if not enable_dood:
            docker_args.append("--read-only")
            docker_args.extend(["--tmpfs", "/tmp:rw,noexec,nosuid,size=64m"])
        else:
            docker_args.extend(["-v", f"{docker_socket}:{docker_socket}"])

        docker_args.extend([
            "-v", f"{os.path.abspath(workspace)}:/workspace:rw",
            "-w", container_workdir,
            self.image, "/bin/sh", "-c", command,
        ])

        try:
            proc = await asyncio.create_subprocess_exec(
                *docker_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
            return {
                "success": proc.returncode == 0,
                "exit_code": proc.returncode,
                "stdout": stdout.decode("utf-8", errors="replace")[:50000],
                "stderr": stderr.decode("utf-8", errors="replace")[:10000],
                "duration_ms": round((time.time() - t0) * 1000),
                "sandbox": "docker",
            }
        except asyncio.TimeoutError:
            return {"success": False, "error": f"Docker timeout after {timeout}s", "sandbox": "docker"}
        except Exception as e:
            raise SandboxExecutionError(f"Docker execution failed: {e}")

    async def _run_local_dev(
        self, command: str, cwd: str, timeout: int, t0: float
    ) -> Dict[str, Any]:
        """Execute locally — ONLY for development with ALLOW_ANON_LOCAL=true."""
        shell_cmd = (
            ["cmd", "/c", command] if os.name == "nt"
            else ["/bin/sh", "-c", command]
        )

        # Sanitized environment — strip sensitive vars
        safe_env = {
            k: v for k, v in os.environ.items()
            if k not in {"AWS_SECRET_ACCESS_KEY", "DATABASE_URL", "JWT_SECRET", "APP_SECRET_KEY"}
        }
        safe_env["SANDBOX_MODE"] = "local_dev"
        
        # Ensure cwd exists, fallback to current directory to prevent WinError 267
        if not os.path.exists(cwd):
            logger.warning(f"[Sandbox] cwd {cwd} does not exist, falling back to current directory")
            cwd = os.getcwd()

        try:
            proc = await asyncio.create_subprocess_exec(
                *shell_cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=safe_env,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
            return {
                "success": proc.returncode == 0,
                "exit_code": proc.returncode,
                "stdout": stdout.decode("utf-8", errors="replace")[:50000],
                "stderr": stderr.decode("utf-8", errors="replace")[:10000],
                "duration_ms": round((time.time() - t0) * 1000),
                "sandbox": "local_dev",
            }
        except asyncio.TimeoutError:
            return {"success": False, "error": f"Local timeout after {timeout}s", "sandbox": "local_dev"}
        except Exception as e:
            raise SandboxExecutionError(f"Local execution failed: {e}")
