"""
Bash execute tool.
"""
import asyncio
import re
import time
from typing import Any, Dict

from src.infrastructure.runtime.paths import resolve_workspace_path
from src.tools.core.base import BaseTool, ToolParameter

BLOCKED_PATTERNS = [
    "rm -rf /", "mkfs", "dd if=", ":(){", "fork bomb",
    "shutdown", "reboot", "format c:", "del /f /s /q c:", "takeown", "icacls",
    "curl | sh", "wget -O- |", "chmod 777", "chown -r", "nc -e", "/dev/tcp",
]

DANGEROUS_CHARS = re.compile(r'[;&|`$()]')


class BashExecuteTool(BaseTool):
    name = "bash_execute"
    description = "Execute a shell command in the workspace. Returns stdout, stderr, and exit code."
    parameters = [
        ToolParameter(name="command", type="string", description="The shell command to run"),
        ToolParameter(name="working_dir", type="string", description="Working directory (defaults to workspace root)", required=False),
        ToolParameter(name="timeout", type="integer", description="Execution timeout in seconds (max 120)", required=False),
    ]
    requires_sandbox = True

    def _validate_command(self, command: str) -> tuple[bool, str]:
        cmd_lower = command.lower()
        for pattern in BLOCKED_PATTERNS:
            if pattern in cmd_lower:
                return False, f"BLOCKED: Command matches dangerous pattern '{pattern}'"
        
        if DANGEROUS_CHARS.search(command):
            return False, "BLOCKED: Command contains dangerous shell characters"
        
        if len(command) > 10000:
            return False, "BLOCKED: Command exceeds maximum length"
        
        return True, ""

    async def execute(self, session_id: str, **kwargs) -> Dict[str, Any]:
        command = kwargs.get("command", "")
        working_dir = kwargs.get("working_dir", ".")
        timeout = kwargs.get("timeout", 30)
        
        is_valid, error_msg = self._validate_command(command)
        if not is_valid:
            return {"success": False, "error": error_msg}

        timeout = min(max(timeout, 1), 120)
        safe_working_dir = str(resolve_workspace_path(working_dir))
        start = time.time()
        
        cmd_parts = command.split()
        if not cmd_parts:
            return {"success": False, "error": "Empty command"}
        
        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=safe_working_dir,
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
            if proc and proc.returncode is None:
                proc.kill()
            return {"success": False, "error": f"Command timed out after {timeout}s"}
        except FileNotFoundError:
            return {"success": False, "error": f"Command not found: {cmd_parts[0]}"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}
