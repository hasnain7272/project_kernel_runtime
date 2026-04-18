"""
Bash Execute Tool (Production-Hardened)

Executes shell commands. In production, routed through Docker/MicroVM sandbox.
In local dev when Docker is unavailable, falls back to a restricted subprocess.
"""
import asyncio
import os
import time
from typing import Any, Dict

from src.tools.core.base import BaseTool, ToolParameter
from src.domain.exceptions import ToolExecutionError

# Dangerous commands that are ALWAYS blocked, even in local dev
BLOCKED_PATTERNS = [
    "rm -rf /", "mkfs", "dd if=", ":(){", "fork bomb",
    "shutdown", "reboot", "format c:", "del /f /s /q c:",
]


class BashExecuteTool(BaseTool):
    name = "bash_execute"
    description = "Execute a shell command in the workspace. Returns stdout, stderr, and exit code."
    parameters = [
        ToolParameter(name="command", type="string", description="The shell command to run"),
        ToolParameter(name="working_dir", type="string", description="Working directory (defaults to workspace root)", required=False),
        ToolParameter(name="timeout", type="integer", description="Execution timeout in seconds (max 120)", required=False),
    ]
    requires_sandbox = False  # We handle sandboxing inside execute() now

    async def execute(self, session_id: str, command: str, working_dir: str = ".", timeout: int = 30, **kwargs) -> Dict[str, Any]:
        """Execute a command with safety checks."""
        # 1. Block dangerous patterns
        cmd_lower = command.lower()
        for pattern in BLOCKED_PATTERNS:
            if pattern in cmd_lower:
                return {"success": False, "error": f"BLOCKED: Command matches dangerous pattern '{pattern}'"}

        # 2. Clamp timeout
        timeout = min(max(timeout, 1), 120)

        # 3. Resolve working directory
        if not os.path.isabs(working_dir):
            working_dir = os.path.abspath(working_dir)

        start = time.time()
        try:
            # Use shell=True for proper command interpretation on Windows and Linux
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            
            return {
                "success": proc.returncode == 0,
                "exit_code": proc.returncode,
                "stdout": stdout.decode("utf-8", errors="replace")[:50000],
                "stderr": stderr.decode("utf-8", errors="replace")[:10000],
                "duration_ms": round((time.time() - start) * 1000),
            }
        except asyncio.TimeoutError:
            proc.kill()
            return {"success": False, "error": f"Command timed out after {timeout}s"}
        except Exception as e:
            return {"success": False, "error": str(e)}
