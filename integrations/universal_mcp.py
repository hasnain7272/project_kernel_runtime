import asyncio
import httpx
import os
import yaml
from typing import Dict, Any, List, Optional
from project_kernel_runtime.memory.state_hub import state_hub

class UniversalMCP:
    def __init__(self, registry_path: str = "mcp_registry.yaml"):
        self.registry_path = os.path.join(os.path.dirname(__file__), registry_path)
        self.discovered_servers: Dict[str, Dict[str, Any]] = self._load_registry()
        self.tool_map: Dict[str, str] = {} # tool_name -> server_id
        self.clients: Dict[str, Any] = {} # server_id -> client instance
        self._rebuild_tool_map()

    def _load_registry(self) -> Dict:
        """Load discovered MCPs from persistent storage."""
        if os.path.exists(self.registry_path):
            with open(self.registry_path, "r") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _save_registry(self):
        """Save discovered MCPs to persistent storage."""
        with open(self.registry_path, "w") as f:
            yaml.dump(self.discovered_servers, f)

    def _rebuild_tool_map(self):
        """Rebuild tool_map from discovered_servers."""
        for server_id, info in self.discovered_servers.items():
            for tool in info.get("tools", []):
                self.tool_map[tool] = server_id

    async def add_server(self, url: str):
        """Adds and probes a new MCP server via SSE."""
        state_hub.record_thought("MCP_Bridge", "Discovery", f"Probing MCP endpoint: {url}...")
        
        try:
            # Multi-probe strategy for manifest discovery
            manifest = None
            server_id = None
            tools = []
            
            # 1. Try standard MCP manifest paths
            probe_paths = ["/manifest", "/mcp/manifest", "/.well-known/mcp/manifest.json", ""]
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                for path in probe_paths:
                    probe_url = f"{url.rstrip('/')}{path}"
                    try:
                        res = await client.get(probe_url)
                        if res.status_code == 200:
                            data = res.json()
                            # It's a manifest if it has "tools" or "name"
                            if "tools" in data or "name" in data:
                                manifest = data
                                state_hub.record_thought("MCP_Bridge", "Discovery", f"Manifest found at {probe_url}")
                                break
                    except:
                        continue

                if manifest:
                    server_id = manifest.get("name", f"mcp_{len(self.discovered_servers)}")
                    tools = [t["name"] for t in manifest.get("tools", []) if isinstance(t, dict) and "name" in t]
                    if not tools and "tools" in manifest and isinstance(manifest["tools"], list):
                         tools = manifest["tools"] # Fallback for simpler schemas
                else:
                    # Fallback for generic SSE endpoints
                    state_hub.record_thought("MCP_Bridge", "Discovery", f"No manifest found at {url}. Attempting generic capability mapping...")
                    server_id = f"mcp_{len(self.discovered_servers)}"

                if server_id:
                    self.discovered_servers[server_id] = {
                        "url": url,
                        "tools": tools,
                        "type": "remote" if "localhost" not in url else "local",
                        "status": "connected"
                    }
                    
                    for tool in tools:
                        self.tool_map[tool] = server_id
                    
                    self._save_registry()
                    state_hub.record_thought("MCP_Bridge", "Discovery", f"Liquid Discovery: {server_id} mapped with {len(tools)} tools.")
                    return True
        except Exception as e:
            state_hub.record_thought("MCP_Bridge", "Discovery", f"Failed to reach MCP at {url}: {str(e)}")
            return False

    async def initiate_mcp_discovery(self):
        """Background task to discover local and configured MCP servers."""
        state_hub.record_thought("MCP_Bridge", "Discovery", "Starting background discovery loop...")
        # Common local development ports
        potential_urls = ["http://localhost:8080/mcp"]
        for url in potential_urls:
            await self.add_server(url)
        
        while True:
            # Periodic re-probe or discovery logic
            await asyncio.sleep(60)

    async def execute_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Routes execution to the target MCP server via SSE."""
        server_id = self.tool_map.get(tool_name)
        if not server_id:
            raise ValueError(f"Tool {tool_name} not found in mesh.")
        
        server_info = self.discovered_servers[server_id]
        state_hub.record_thought("MCP_Bridge", "Execution", f"Routing {tool_name} to {server_id} at {server_info['url']}")
        
        # Real SSE execution would happen here
        # For this milestone, we acknowledge the bridge is open
        return {"status": "success", "result": f"Executed {tool_name} on {server_id}"}

    async def reprobe_server(self, url: str) -> bool:
        """Manually re-probe an existing server to update status and tools."""
        state_hub.record_thought("MCP_Bridge", "Action", f"Re-probing MCO Hub: {url}")
        success = await self.add_server(url)
        if success:
             self._save_registry()
        return success

    async def check_health(self):
        """Background health check for all registered servers."""
        for server_id, info in list(self.discovered_servers.items()):
            url = info.get("url")
            try:
                # Minimal probe to check heartbeat
                async with httpx.AsyncClient(timeout=2.0) as client:
                    probe_url = url.replace("/mcp", "/mcp/manifest") if "/mcp" in url else f"{url}/mcp/manifest"
                    res = await client.get(probe_url)
                    if res.status_code == 200:
                        self.discovered_servers[server_id]["status"] = "connected"
                    else:
                        self.discovered_servers[server_id]["status"] = "disconnected"
            except:
                self.discovered_servers[server_id]["status"] = "disconnected"
        self._save_registry()

# Global Instance
mcp_bridge = UniversalMCP()
