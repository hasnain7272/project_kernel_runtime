"""
Governance Policy Engine
"""
import logging
from typing import Dict, Any

from src.domain.exceptions import GovernanceDeniedError

logger = logging.getLogger(__name__)

class PolicyEngine:
    """Stateless engine to audit and validate actions against session roles."""
    
    @staticmethod
    def assert_action_allowed(session, tool_name: str, kwargs: Dict[str, Any]):
        """
        Validates if the current session role is allowed to execute the requested tool.
        Throws GovernanceDeniedError if prohibited.
        """
        # Admin Role: Everything allowed
        if session.user_role == "admin":
            return
            
        # Hard denylist for standard developers inside the sandbox
        prohibited_commands = ["rm -rf /", "mkfs", "dd if=/dev/zero"]
        
        if tool_name == "bash_execute":
            cmd = kwargs.get("command", "").lower()
            for prohibited in prohibited_commands:
                if prohibited in cmd:
                    logger.warning(f"Governance BLOCKED malicious command: {cmd}")
                    raise GovernanceDeniedError(
                        f"Command '{cmd}' is prohibited by safety policies."
                    )
        
        # Reader role cannot write files
        if session.user_role == "reader" and "write" in tool_name:
             raise GovernanceDeniedError(
                 f"Role 'reader' cannot execute modifying tool '{tool_name}'."
             )
