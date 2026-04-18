"""
Governance policy engine.
"""
import logging
from typing import Any, Dict

from src.domain.exceptions import GovernanceDeniedError
from src.infrastructure.runtime.paths import resolve_workspace_path

logger = logging.getLogger(__name__)


class PolicyEngine:
    @staticmethod
    def assert_action_allowed(session, tool_name: str, kwargs: Dict[str, Any]):
        if session.user_role == "admin":
            return

        prohibited_commands = [
            "rm -rf /", "mkfs", "dd if=/dev/zero", "shutdown", "reboot",
            "format c:", "del /f /s /q c:", "takeown", "icacls",
        ]

        if tool_name == "bash_execute":
            cmd = kwargs.get("command", "").lower()
            for prohibited in prohibited_commands:
                if prohibited in cmd:
                    logger.warning(f"Governance blocked malicious command: {cmd}")
                    raise GovernanceDeniedError(f"Command '{cmd}' is prohibited by safety policies.")
            resolve_workspace_path(kwargs.get("working_dir", "."))

        if tool_name in {"read_file", "write_file"}:
            resolve_workspace_path(kwargs.get("filepath"))

        if session.user_role == "reader" and "write" in tool_name:
            raise GovernanceDeniedError(
                f"Role 'reader' cannot execute modifying tool '{tool_name}'."
            )
