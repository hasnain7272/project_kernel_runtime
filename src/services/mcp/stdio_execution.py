"""
Stdio MCP Execution - Tools, listing and execution tracking.
"""
import time
from typing import Any, Dict, List

from src.services.mcp.stdio_models import ServerStatus
from src.services.mcp.stdio_messages import MCPProtocolError


class StdioMCPExecutionMixin:
    def list_servers(self: Any, tenant_id: str) -> List[Dict[str, Any]]:
        servers = self._get_tenant_servers(tenant_id)
        return [
            {
                "name": name,
                "description": s.description,
                "command": s.command,
                "args": s.args,
                "working_dir": s.working_dir,
                "status": s.status.value,
                "tool_count": len(s.tools),
                "created_at": s.created_at,
                "error_message": s.error_message,
            }
            for name, s in servers.items()
        ]

    async def get_tools(self: Any, tenant_id: str, name: str) -> List[Dict[str, Any]]:
        servers = self._get_tenant_servers(tenant_id)
        server = servers.get(name)

        if not server:
            raise ValueError(f"Server '{name}' not found")

        if server.status != ServerStatus.RUNNING or not server.protocol:
            return []

        return [{"name": t.name, "description": t.description, "inputSchema": t.input_schema} for t in server.tools]

    async def execute_tool(
        self: Any, tenant_id: str, server_name: str, tool_name: str, arguments: Dict[str, Any]
    ) -> Any:
        servers = self._get_tenant_servers(tenant_id)
        server = servers.get(server_name)

        if not server:
            raise ValueError(f"Server '{server_name}' not found")

        if server.status != ServerStatus.RUNNING or not server.protocol:
            raise MCPProtocolError(f"Server '{server_name}' is not running (status: {server.status.value})")

        start_time = time.time()
        server.metrics.total_calls += 1
        server.metrics.last_called = start_time

        try:
            result = await server.protocol.call_tool(tool_name, arguments)
            latency = (time.time() - start_time) * 1000
            server.metrics.total_latency_ms += latency
            return result
        except Exception as e:
            server.metrics.failed_calls += 1
            raise MCPProtocolError(f"Tool execution failed: {e}") from e

    def get_all_metrics(self: Any) -> Dict[str, Dict[str, Any]]:
        metrics = {}
        for tenant_servers in self._tenant_servers.values():
            for name, server in tenant_servers.items():
                metrics[f"{server.tenant_id}:{name}"] = {
                    "total_calls": server.metrics.total_calls,
                    "failed_calls": server.metrics.failed_calls,
                    "success_rate": server.metrics.success_rate,
                    "avg_latency_ms": server.metrics.avg_latency_ms,
                    "last_called": server.metrics.last_called,
                    "restart_count": server.metrics.restart_count,
                    "status": server.status.value,
                }
        return metrics
