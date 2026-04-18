"""
Bash Execute Tool (Hardened)
"""
from typing import Any, Dict, Optional

from src.tools.core.base import BaseTool, ToolParameter
from src.domain.exceptions import ToolExecutionError

class BashExecuteTool(BaseTool):
    name = "bash_execute"
    description = "Execute a shell command. THIS CODE WILL RUN IN A SECURE MICRO-VM SANDBOX."
    parameters = [
        ToolParameter(name="command", type="string", description="The bash command to run"),
        ToolParameter(name="working_dir", type="string", description="Working directory inside the sandbox", required=False),
        ToolParameter(name="timeout", type="integer", description="Execution timeout in seconds (max 120)", required=False)
    ]
    
    # Crucial security configuration. This forces the ToolExecution router 
    # to NEVER run this on the host loop, and ALWAYS pass it to sandbox.py
    requires_sandbox = True

    async def execute(self, session_id: str, command: str, working_dir: str = "/home/user", timeout: int = 30, **kwargs) -> Dict[str, Any]:
        """
        Implementation note: Because `requires_sandbox=True`, the data-plane router 
        will intercept this call and feed the parameters to the Sandbox Adapter. 
        This execute block may actually never run directly on the host, 
        and acts as a schema definition for the Orchestrator.
        """
        # Fallback mechanism if router misfires (defense in depth)
        raise ToolExecutionError(
            "Bash execution intercepted: Command was not routed to the Sandboxing layer.", 
            self.name
        )
