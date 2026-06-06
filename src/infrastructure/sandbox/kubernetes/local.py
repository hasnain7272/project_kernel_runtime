"""Local Development Fallback - NOT for production."""
import asyncio
import logging
import os
import subprocess
import time
import uuid
from datetime import datetime, timedelta

from .config import MAX_OUTPUT_SIZE
from .exceptions import SandboxExecutionError
from .models import SandboxConfig, SandboxResult

logger = logging.getLogger(__name__)


class LocalSandboxExecutor:
    """
    Local development sandbox using subprocess (NOT for production).
    This is ONLY for development when Kubernetes is not available.
    """

    def __init__(self):
        self._use_docker = os.environ.get("USE_DOCKER_SANDBOX", "false").lower() == "true"

    async def execute(self, config: SandboxConfig | str = None, **kwargs) -> SandboxResult:
        """Execute in local subprocess (limited security)."""
        if isinstance(config, str):
            config = SandboxConfig(command=config, **kwargs)
        elif config is None and "command" in kwargs:
            config = SandboxConfig(command=kwargs.pop("command"), **kwargs)
        elif not isinstance(config, SandboxConfig):
            raise TypeError("Expected SandboxConfig or command string")

        start_time = time.time()
        job_name = f"local-{uuid.uuid4().hex[:8]}"

        if self._use_docker:
            # Docker fallback for local dev
            cmd = [
                "docker", "run", "--rm",
                f"--memory={config.memory_limit}",
                "--network=none",
                "--read-only",
                "--user=1000:1000",
                "-v", f"{config.working_dir}:/workspace:ro",
                config.image,
                "/bin/sh", "-c", config.command
            ]
        else:
            # Direct subprocess (VERY LIMITED SECURITY - dev only)
            logger.warning("[LocalSandbox] Using direct subprocess - NO SECURITY ISOLATION")
            if os.name == "nt":
                cmd = [os.environ.get("COMSPEC", "cmd.exe"), "/c", config.command]
            else:
                cmd = ["/bin/sh", "-c", config.command]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=config.working_dir if not self._use_docker else None
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=config.timeout
            )

            duration_ms = (time.time() - start_time) * 1000

            return SandboxResult(
                exit_code=proc.returncode or 0,
                stdout=stdout.decode('utf-8', errors='replace')[:MAX_OUTPUT_SIZE],
                stderr=stderr.decode('utf-8', errors='replace')[:MAX_OUTPUT_SIZE],
                duration_ms=duration_ms,
                job_name=job_name,
                started_at=datetime.utcnow() - timedelta(milliseconds=duration_ms),
                completed_at=datetime.utcnow()
            )

        except asyncio.TimeoutError:
            proc.kill()
            raise SandboxExecutionError(f"Execution timed out after {config.timeout}s")
        except Exception as e:
            raise SandboxExecutionError(f"Execution failed: {e}")
