"""
Docker Sandbox Adapter

Implements production-grade sandboxing using restricted Docker containers.
"""
import asyncio
import logging
import os
from typing import Dict, Any

from src.domain.exceptions import SandboxExecutionError

logger = logging.getLogger(__name__)

class DockerAdapter:
    def __init__(self, image: str = "python:3.11-slim"):
        self.image = image

    async def execute(self, command: str, working_dir: str = ".", 
                      timeout: int = 30, memory_limit_mb: int = 512, 
                      network_mode: str = "none") -> Dict[str, Any]:
        """Execute command inside an isolated Docker container."""
        import time
        start_time = time.time()
        
        docker_args = [
            "docker", "run", "--rm",
            f"--memory={memory_limit_mb}m",
            f"--network={network_mode}",
            "--read-only",
            "--tmpfs", "/tmp:size=100M",
            "-v", f"{os.path.abspath(working_dir)}:/workspace:rw",
            "-w", "/workspace",
            self.image, "/bin/sh", "-c", command
        ]
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *docker_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
                return {
                    "exit_code": proc.returncode,
                    "stdout": stdout.decode('utf-8', errors='replace')[:50000],
                    "stderr": stderr.decode('utf-8', errors='replace')[:50000],
                    "duration_ms": (time.time() - start_time) * 1000
                }
            except asyncio.TimeoutError:
                proc.kill()
                raise SandboxExecutionError(f"Docker execution timed out after {timeout}s.")
                
        except Exception as e:
            if isinstance(e, SandboxExecutionError):
                raise
            raise SandboxExecutionError(f"Docker error: {str(e)}")
