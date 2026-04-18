"""
Tool Execution Router
"""
import logging
from typing import Dict, Any

from src.tools.core.base import BaseTool
from src.infrastructure.sandbox.docker_adapter import DockerAdapter
from src.domain.exceptions import SandboxExecutionError, ToolExecutionError

logger = logging.getLogger(__name__)

class ToolExecutionRouter:
    """Routes tool execution between the host process and the sandbox layer."""
    
    def __init__(self):
        # We inject the docker adapter for local execution, or E2B for cloud.
        self.sandbox = DockerAdapter()
        
    async def execute_tool(self, tool_: BaseTool, session_id: str, kwargs: Dict[str, Any]) -> Any:
        logger.info(f"Routing tool execution: {tool_.name}")
        
        if getattr(tool_, "requires_sandbox", False):
            # Intercept and route to sandbox
            logger.info("Sandbox required. Intercepting host process.")
            if tool_.name == "bash_execute":
                command = kwargs.get("command")
                if not command:
                    raise ToolExecutionError("Missing command for bash execute", tool_.name)
                    
                working_dir = kwargs.get("working_dir", "/workspace")
                timeout = kwargs.get("timeout", 30)
                
                try:
                    return await self.sandbox.execute(command, working_dir, timeout)
                except SandboxExecutionError as e:
                    return {"success": False, "error": f"Sandbox blocked execution: {e}"}
            else:
                raise ToolExecutionError(f"Tool {tool_.name} demands sandbox but is unmapped in router", tool_.name)
                
        else:
            # Safe Native Python Execution
            return await tool_.execute(session_id=session_id, **kwargs)
