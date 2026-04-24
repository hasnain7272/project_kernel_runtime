"""
MCP (Model Context Protocol) Hub

Manages dynamic loading and proxying of third-party external tools (plugins).
Allows hot-plugging new tools into the registry without restarting the server.
"""
import logging
import httpx
from typing import Dict, Any, List
from src.tools.core.base import BaseTool, ToolParameter
from src.tools.registry import _tool_instances

logger = logging.getLogger(__name__)

class MCPProxyTool(BaseTool):
    """A wrapper that makes an external HTTP endpoint look like a local tool."""
    def __init__(self, name: str, description: str, parameters: List[Dict[str, Any]], endpoint_url: str):
        self.name = name
        self.description = description
        
        # Convert dictionary schemas to ToolParameter objects
        self.parameters = []
        for p in parameters:
            self.parameters.append(ToolParameter(
                name=p.get("name", ""),
                type=p.get("type", "string"),
                description=p.get("description", ""),
                required=p.get("required", True),
                default=p.get("default")
            ))
            
        self.endpoint_url = endpoint_url
        self.requires_sandbox = False

    async def execute(self, session_id: str, **kwargs) -> Dict[str, Any]:
        logger.info(f"[MCP Hub] Executing remote tool {self.name} at {self.endpoint_url}")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.endpoint_url,
                    json={"session_id": session_id, "args": kwargs},
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"[MCP Hub] Remote execution failed for {self.name}: {e}")
            return {"error": f"Failed to execute {self.name}: {e}"}


class MCPHub:
    """Central registry for dynamic third-party MCP plugins."""
    
    @staticmethod
    def register_plugin(plugin_def: Dict[str, Any]):
        """Register a new remote tool and inject it into the main registry."""
        name = plugin_def.get("name")
        description = plugin_def.get("description", "Dynamic MCP Tool")
        parameters = plugin_def.get("parameters", [])
        endpoint_url = plugin_def.get("endpoint_url")
        
        if not name or not endpoint_url:
            raise ValueError("Plugin must have 'name' and 'endpoint_url'")
            
        proxy = MCPProxyTool(name, description, parameters, endpoint_url)
        _tool_instances[name] = proxy
        logger.info(f"[MCP Hub] Hot-loaded plugin: {name}")

    @staticmethod
    def list_plugins() -> List[str]:
        return [name for name, tool in _tool_instances.items() if isinstance(tool, MCPProxyTool)]

mcp_hub = MCPHub()
