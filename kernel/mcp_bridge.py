"""
MCP Bridge — Dynamic MCP Server Lifecycle Manager

Spawns stdio subprocess-based MCP servers and manages websocket MCP clients.
On boot, reads data/mcp_registry.json to auto-connect permanent MCPs.
Exposes discovered tools to the Orchestrator's LLM context.

Inspired by: OpenHands MCP integration, Claude Code tool discovery
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "mcp_registry.json")


class MCPBridge:
    """
    Manages the lifecycle of external MCP server connections.
    
    Supports two transport types:
    - stdio: Spawns a subprocess and communicates via stdin/stdout JSON-RPC
    - websocket: Connects to a remote MCP server via WebSocket
    
    All discovered tools are exposed to the Orchestrator for LLM tool-calling.
    """
    
    def __init__(self):
        self._connections: Dict[str, Dict[str, Any]] = {}  # name -> {process, tools, type, ...}
        self.discovered_servers: Dict[str, Dict[str, Any]] = {}
        logger.info("[MCPBridge] Initialized")
    
    async def boot_permanent_servers(self) -> None:
        """On startup, read the registry and connect all permanent MCPs."""
        registry = self._read_registry()
        for name, config in registry.items():
            if config.get("persistence") == "permanent":
                logger.info(f"[MCPBridge] Auto-connecting permanent MCP: {name}")
                try:
                    await self.connect(name, config)
                except Exception as e:
                    logger.warning(f"[MCPBridge] Failed to auto-connect {name}: {e}")
    
    async def connect(self, name: str, config: Dict[str, Any]) -> bool:
        """Connect to an MCP server (stdio or websocket)."""
        server_type = config.get("type", "stdio")
        
        if server_type == "stdio":
            return await self._connect_stdio(name, config)
        elif server_type == "websocket":
            return await self._connect_websocket(name, config)
        else:
            logger.error(f"[MCPBridge] Unknown transport type: {server_type}")
            return False
    
    async def _connect_stdio(self, name: str, config: Dict[str, Any]) -> bool:
        """Spawn an MCP server as a subprocess, communicate via stdin/stdout."""
        command = config.get("command", "")
        if not command:
            logger.error(f"[MCPBridge] No command for stdio MCP: {name}")
            return False
        
        try:
            # Determine the python executable from our venv
            venv_python = sys.executable
            
            # Parse the command — handle both "python -m ..." and "npx ..." styles
            parts = command.split()
            if parts[0] == "python":
                parts[0] = venv_python
            
            logger.info(f"[MCPBridge] Spawning stdio MCP '{name}': {' '.join(parts)}")
            
            process = subprocess.Popen(
                parts,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.path.join(os.path.dirname(__file__), "..", "..", ".."),
                env={**os.environ, "PYTHONPATH": os.path.join(os.path.dirname(__file__), "..", "..")},
            )
            
            self._connections[name] = {
                "process": process,
                "type": "stdio",
                "tools": [],
                "status": "connected",
                "config": config,
            }
            
            # Try to discover tools via JSON-RPC initialize handshake
            tools = await self._discover_tools_stdio(name, process)
            self._connections[name]["tools"] = tools
            
            self.discovered_servers[name] = {
                "url": f"stdio://{command}",
                "status": "connected",
                "tools": [t.get("name", "unknown") for t in tools],
                "type": "stdio",
            }
            
            logger.info(f"[MCPBridge] '{name}' connected with {len(tools)} tools")
            return True
            
        except Exception as e:
            logger.error(f"[MCPBridge] Failed to spawn '{name}': {e}")
            self.discovered_servers[name] = {
                "url": f"stdio://{command}",
                "status": "error",
                "tools": [],
                "error": str(e),
            }
            return False
    
    async def _connect_websocket(self, name: str, config: Dict[str, Any]) -> bool:
        """Connect to an MCP server via WebSocket."""
        url = config.get("url", "")
        if not url:
            logger.error(f"[MCPBridge] No URL for websocket MCP: {name}")
            return False
        
        try:
            # Use the existing MCPClient for websocket connections
            from project_kernel_runtime.protocols.mcp_client import MCPClient
            client = MCPClient(url)
            connected = await client.connect()
            
            if connected:
                tools = await client.list_tools()
                self._connections[name] = {
                    "client": client,
                    "type": "websocket",
                    "tools": tools,
                    "status": "connected",
                    "config": config,
                }
                self.discovered_servers[name] = {
                    "url": url,
                    "status": "connected",
                    "tools": [t.get("name", "unknown") for t in tools],
                    "type": "websocket",
                }
                logger.info(f"[MCPBridge] '{name}' connected via WebSocket with {len(tools)} tools")
                return True
            else:
                self.discovered_servers[name] = {
                    "url": url, "status": "error", "tools": [], "type": "websocket",
                }
                return False
        except Exception as e:
            logger.error(f"[MCPBridge] WebSocket connection to '{name}' failed: {e}")
            self.discovered_servers[name] = {
                "url": url, "status": "error", "tools": [], "error": str(e),
            }
            return False
    
    async def _discover_tools_stdio(self, name: str, process: subprocess.Popen) -> List[Dict]:
        """Send JSON-RPC initialize + tools/list to discover available tools."""
        try:
            # MCP JSON-RPC: initialize
            init_msg = json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "antigravity-kernel", "version": "2.0.0"}
                }
            }) + "\n"
            
            process.stdin.write(init_msg.encode())
            process.stdin.flush()
            
            # Read response with timeout
            loop = asyncio.get_event_loop()
            response_line = await asyncio.wait_for(
                loop.run_in_executor(None, process.stdout.readline),
                timeout=10.0
            )
            
            if not response_line:
                logger.warning(f"[MCPBridge] No init response from '{name}'")
                return []
            
            # Send initialized notification
            notif = json.dumps({
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }) + "\n"
            process.stdin.write(notif.encode())
            process.stdin.flush()
            
            # Request tools list
            tools_msg = json.dumps({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }) + "\n"
            process.stdin.write(tools_msg.encode())
            process.stdin.flush()
            
            tools_line = await asyncio.wait_for(
                loop.run_in_executor(None, process.stdout.readline),
                timeout=10.0
            )
            
            if tools_line:
                tools_response = json.loads(tools_line.decode())
                tools = tools_response.get("result", {}).get("tools", [])
                return tools
            
            return []
            
        except asyncio.TimeoutError:
            logger.warning(f"[MCPBridge] Timeout discovering tools from '{name}'")
            return []
        except Exception as e:
            logger.warning(f"[MCPBridge] Tool discovery error for '{name}': {e}")
            return []
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict) -> Any:
        """Call a tool on a connected MCP server."""
        conn = self._connections.get(server_name)
        if not conn:
            raise ValueError(f"MCP server '{server_name}' not connected")
        
        if conn["type"] == "stdio":
            return await self._call_tool_stdio(conn["process"], tool_name, arguments)
        elif conn["type"] == "websocket":
            return await conn["client"].call_tool(tool_name, arguments)
    
    async def _call_tool_stdio(self, process: subprocess.Popen, tool_name: str, arguments: Dict) -> Any:
        """Execute a tool call via stdio JSON-RPC."""
        msg = json.dumps({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments}
        }) + "\n"
        
        process.stdin.write(msg.encode())
        process.stdin.flush()
        
        loop = asyncio.get_event_loop()
        response_line = await asyncio.wait_for(
            loop.run_in_executor(None, process.stdout.readline),
            timeout=60.0
        )
        
        if response_line:
            response = json.loads(response_line.decode())
            return response.get("result", {})
        return {"error": "No response from MCP server"}
    
    def get_all_external_tools(self) -> List[Dict]:
        """Get all tool schemas from all connected MCP servers for LLM context injection."""
        all_tools = []
        for name, conn in self._connections.items():
            if conn.get("status") == "connected":
                for tool in conn.get("tools", []):
                    # Convert MCP tool schema to OpenAI-compatible function schema
                    all_tools.append({
                        "type": "function",
                        "function": {
                            "name": f"{name}__{tool.get('name', 'unknown')}",
                            "description": f"[MCP: {name}] {tool.get('description', '')}",
                            "parameters": tool.get("inputSchema", {"type": "object", "properties": {}}),
                        },
                        "_mcp_server": name,
                        "_mcp_tool_name": tool.get("name"),
                    })
        return all_tools
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of all MCP connections."""
        return {
            "connected_count": len([c for c in self._connections.values() if c.get("status") == "connected"]),
            "total_tools": sum(len(c.get("tools", [])) for c in self._connections.values()),
            "servers": {
                name: {
                    "status": conn.get("status", "unknown"),
                    "type": conn.get("type"),
                    "tool_count": len(conn.get("tools", [])),
                }
                for name, conn in self._connections.items()
            }
        }
    
    async def disconnect(self, name: str) -> bool:
        """Disconnect and clean up an MCP server."""
        conn = self._connections.pop(name, None)
        if not conn:
            return False
        
        if conn["type"] == "stdio" and conn.get("process"):
            try:
                conn["process"].terminate()
                conn["process"].wait(timeout=5)
            except Exception:
                conn["process"].kill()
        elif conn["type"] == "websocket" and conn.get("client"):
            try:
                await conn["client"].disconnect()
            except Exception:
                pass
        
        self.discovered_servers.pop(name, None)
        logger.info(f"[MCPBridge] Disconnected '{name}'")
        return True
    
    async def shutdown(self) -> None:
        """Disconnect all servers."""
        names = list(self._connections.keys())
        for name in names:
            await self.disconnect(name)
    
    def _read_registry(self) -> Dict[str, Any]:
        """Read the persistent MCP registry from disk."""
        path = os.path.normpath(REGISTRY_PATH)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"[MCPBridge] Failed to read registry: {e}")
        return {}
    
    async def add_server(self, url: str) -> bool:
        """Legacy compatibility: add a server by URL."""
        name = url.split("/")[-1] or "unknown"
        return await self.connect(name, {"type": "websocket", "url": url})
    
    async def reprobe_server(self, url: str) -> bool:
        """Re-probe a server to refresh its tool list."""
        for name, conn in self._connections.items():
            if conn.get("config", {}).get("url") == url:
                await self.disconnect(name)
                return await self.connect(name, conn["config"])
        return False
