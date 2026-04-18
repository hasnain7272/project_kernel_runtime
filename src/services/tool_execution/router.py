"""
Tool execution router.
"""
import logging
from typing import Any, Dict

from src.domain.exceptions import ToolExecutionError
from src.infrastructure.runtime.config import SANDBOX_MODE, KUBERNETES_MODE, ALLOW_ANON_LOCAL
from src.infrastructure.sandbox.docker_adapter import DockerAdapter
from src.infrastructure.sandbox.kubernetes_executor import KubernetesSandboxExecutor
from src.tools.core.base import BaseTool

logger = logging.getLogger(__name__)


class ToolExecutionRouter:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._docker = DockerAdapter()
        self._kubernetes = KubernetesSandboxExecutor() if KUBERNETES_MODE else None
        
    def _get_sandbox(self):
        if KUBERNETES_MODE and self._kubernetes:
            return self._kubernetes
        return self._docker

    async def execute_tool(self, tool_: BaseTool, session_id: str, kwargs: Dict[str, Any]) -> Any:
        logger.info(f"Routing tool execution: {tool_.name}")
        
        # Bash execution requires sandbox - block host execution entirely in production
        if tool_.name == "bash_execute":
            # In production (non-local), always require sandbox
            is_local_dev = ALLOW_ANON_LOCAL and SANDBOX_MODE == "host"
            
            if not is_local_dev:
                sandbox = self._get_sandbox()
                command = kwargs.get("command")
                if not command:
                    raise ToolExecutionError("Missing command for bash execute", tool_.name)

                try:
                    return await sandbox.execute(
                        command=command,
                        session_id=session_id,
                        working_dir=kwargs.get("working_dir", "."),
                        timeout=kwargs.get("timeout", 30),
                    )
                except Exception as exc:
                    logger.error(f"[Router] Sandbox execution failed: {exc}")
                    raise ToolExecutionError(
                        f"Sandbox execution failed. Cannot run on host in production.",
                        tool_.name
                    )
            else:
                # Dev mode - allow host execution
                logger.warning("[Router] DEV MODE: Running bash on host")
                return await tool_.execute(session_id=session_id, **kwargs)

        # Other tools - execute normally
        return await tool_.execute(session_id=session_id, **kwargs)
