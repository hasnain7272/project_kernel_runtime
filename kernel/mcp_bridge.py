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
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "mcp_registry.json")
RUNTIME_YAML_PATH = Path(__file__).resolve().parent.parent / "runtime.yaml"


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
        """On startup, read disk registries and auto-connect configured MCPs."""
        registry = self._read_registry()
        registry.update(self._read_runtime_registry())
        for name, config in registry.items():
            if config.get("disabled"):
                continue
            if config.get("persistence") == "permanent" or config.get("auto_start"):
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
            
            args = config.get("args", [])
            if isinstance(args, str):
                args = [part for part in args.split() if part]
            parts = [command, *args]
            parts = self._normalize_command(parts, venv_python)
            
            logger.info(f"[MCPBridge] Spawning stdio MCP '{name}': {' '.join(parts)}")
            
            process = subprocess.Popen(
                parts,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.path.join(os.path.dirname(__file__), "..", "..", ".."),
                env={
                    **os.environ,
                    "PYTHONPATH": os.path.join(os.path.dirname(__file__), "..", ".."),
                    **config.get("env", {}),
                },
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
                "url": f"stdio://{' '.join(parts)}",
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
            
            # Agentic Auto-Booter Feature
            fallback_command = config.get("auto_boot_command")
            max_retries = config.get("max_retries", 1)
            retry_count_attr = f"_{name}_retry_count"
            current_retries = getattr(self, retry_count_attr, 0)
            
            if fallback_command and current_retries < max_retries:
                logger.info(f"[MCPBridge] Auto-booting failed MCP '{name}' with: {fallback_command}")
                setattr(self, retry_count_attr, current_retries + 1)
                
                try:
                    parts = fallback_command.split()
                    if parts[0] == "python":
                        parts[0] = sys.executable
                        
                    subprocess.Popen(
                        parts,
                        cwd=os.path.join(os.path.dirname(__file__), "..", "..", ".."),
                        env={**os.environ, "PYTHONPATH": os.path.join(os.path.dirname(__file__), "..", "..")}
                    )
                    logger.info(f"[MCPBridge] Spawned '{name}', waiting 3 seconds before auto-reconnect...")
                    await asyncio.sleep(3)
                    
                    # Retry connection
                    return await self._connect_websocket(name, config)
                except Exception as boot_err:
                    logger.error(f"[MCPBridge] Auto-boot failed for '{name}': {boot_err}")
            
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
                timeout=30.0
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
                timeout=30.0
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
    
    async def _try_recovery(self, server_name: str) -> bool:
        """Attempt to recover/find an MCP server via local auto-start or A2A mesh discovery."""
        logger.info(f"[MCPBridge] Starting intelligent recovery reasoning for '{server_name}'...")
        
        # 1. Local Auto-Restart
        try:
            registry = self._read_registry()
            registry.update(self._read_runtime_registry())
            config = registry.get(server_name)
            
            if config:
                success = await self.connect(server_name, config)
                if success:
                    logger.info(f"[MCPBridge] Local restart SUCCESS for '{server_name}'")
                    return True
        except Exception as e:
            logger.debug(f"[MCPBridge] Local restart failed: {e}")

        # 2. A2A Mesh Discovery (Reasoning Path)
        try:
            # We use a deferred import to avoid circular dependencies
            from project_kernel_runtime.kernel.orchestrator import get_orchestrator
            orch = get_orchestrator()
            if orch and orch.mesh_p2p:
                peers = orch.mesh_p2p.discover_peers()
                for peer in peers:
                    if server_name in getattr(peer, 'offered_tools', []):
                        logger.info(f"[MCPBridge] Found '{server_name}' on remote peer '{peer.id}'. Initiating A2A proxy...")
                        # Logic to bind a proxy connection here
                        return True
        except Exception as e:
            logger.debug(f"[MCPBridge] A2A mesh discovery error: {e}")
            
        logger.error(f"[MCPBridge] Recovery FAILED: '{server_name}' is unreachable locally or in the mesh.")
        return False

    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict) -> Any:
        """Call a tool on a connected MCP server with Intelligent Recovery."""
        conn = self._connections.get(server_name)
        
        if not conn or conn.get("status") != "connected":
            # Intelligent Reasoning Loop: Try to recover before failing
            recovered = await self._try_recovery(server_name)
            if recovered:
                conn = self._connections.get(server_name)
            else:
                raise ValueError(
                    f"MCP server '{server_name}' is DOWN or not configured. "
                    f"Action Required: Please ensure the server is started in the Network panel or check A2A mesh visibility."
                )
        
        try:
            if conn["type"] == "stdio":
                return await self._call_tool_stdio(conn["process"], tool_name, arguments)
            elif conn["type"] == "websocket":
                return await conn["client"].call_tool(tool_name, arguments)
        except Exception as e:
            logger.error(f"[MCPBridge] Call to {server_name}.{tool_name} failed: {e}")
            # Potentially try recovery once more if it's a transport error
            raise e
    
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
        """Get all tool schemas with unique UI iconography metadata."""
        all_tools = []
        for name, conn in self._connections.items():
            if conn.get("status") == "connected":
                # Determine visual category for UI iconography
                category = "default"
                n_lower = name.lower()
                if "blender" in n_lower: category = "3d"
                elif "web" in n_lower or "fetch" in n_lower or "browser" in n_lower: category = "web"
                elif "file" in n_lower or "shell" in n_lower: category = "system"
                
                for tool in conn.get("tools", []):
                    all_tools.append({
                        "type": "function",
                        "function": {
                            "name": f"{name}__{tool.get('name', 'unknown')}",
                            "description": f"[MCP: {name}] {tool.get('description', '')}",
                            "parameters": tool.get("inputSchema", {"type": "object", "properties": {}}),
                        },
                        "_mcp_server": name,
                        "_mcp_tool_name": tool.get("name"),
                        "_ui_category": category,
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

    def _read_runtime_registry(self) -> Dict[str, Any]:
        """Read MCP server definitions from runtime.yaml."""
        if not RUNTIME_YAML_PATH.exists():
            return {}

        try:
            import yaml

            data = yaml.safe_load(RUNTIME_YAML_PATH.read_text(encoding="utf-8")) or {}
        except Exception as e:
            logger.warning(f"[MCPBridge] Failed to read runtime.yaml MCP registry: {e}")
            return {}

        servers = data.get("mcpServers", {}) or {}
        normalized: Dict[str, Any] = {}
        for name, config in servers.items():
            if not isinstance(config, dict):
                continue
            normalized[name] = {
                "type": config.get("type", "stdio"),
                "command": config.get("command", ""),
                "args": config.get("args", []),
                "url": config.get("url", ""),
                "disabled": bool(config.get("disabled", False)),
                "auto_start": bool(config.get("auto_start", False)),
                "env": config.get("env", {}),
                "persistence": "permanent",
            }
        return normalized
    
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

    def _normalize_command(self, parts: List[str], venv_python: str) -> List[str]:
        if not parts:
            return parts

        command = parts[0]
        if command in {"python", "py"}:
            parts[0] = venv_python
            return parts

        if os.name == "nt":
            windows_wrappers = {
                "npx": "npx.cmd",
                "npm": "npm.cmd",
                "pnpm": "pnpm.cmd",
                "yarn": "yarn.cmd",
            }
            parts[0] = windows_wrappers.get(command, command)

        return parts
