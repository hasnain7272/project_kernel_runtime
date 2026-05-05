"""
Stdio MCP Lifecycle - Server registration and lifecycle management.
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional

from src.services.mcp.stdio_models import StdioMCPServer, ServerStatus
from src.services.mcp.stdio_messages import MCPProtocolError
from src.services.mcp.stdio_spawner import initialize_server
from src.tools.stdio_adapter import stdio_adapter_registry

logger = logging.getLogger(__name__)


class StdioMCPLifecycleMixin:
    async def register_server(
        self: Any,
        tenant_id: str,
        name: str,
        command: str,
        args: List[str],
        working_dir: Optional[str] = None,
        description: str = "",
    ) -> StdioMCPServer:
        servers = self._get_tenant_servers(tenant_id)
        if name in servers:
            raise ValueError(f"Server '{name}' already registered for tenant '{tenant_id}'")

        server = StdioMCPServer(
            name=name,
            command=command,
            args=args,
            working_dir=working_dir,
            description=description,
            tenant_id=tenant_id,
            status=ServerStatus.STARTING,
        )
        servers[name] = server

        try:
            await self._start_server(server)
        except Exception as e:
            server.status = ServerStatus.ERROR
            server.error_message = str(e)
            del servers[name]
            raise

        self._start_health_check_loop()
        return server

    async def _start_server(self: Any, server: StdioMCPServer) -> None:
        client_info = {
            "name": "project-kernel-runtime",
            "version": "3.0.0",
            "capabilities": {"tools": {}},
        }

        try:
            protocol, server_info = await initialize_server(
                command=server.command,
                args=server.args,
                client_info=client_info,
                cwd=server.working_dir,
            )
            server.protocol = protocol
            server.status = ServerStatus.RUNNING

            tools = await protocol.list_tools()
            server.tools = tools

            self._register_mcp_tools(server)

            logger.info(
                f"[StdioMCP] Started server '{server.name}' for tenant '{server.tenant_id}' "
                f"with {len(tools)} tools"
            )

        except Exception as e:
            server.status = ServerStatus.ERROR
            server.error_message = f"Failed to start: {e}"
            if server.process and server.process.returncode is None:
                try:
                    server.process.terminate()
                except Exception:
                    pass
            raise MCPProtocolError(f"Failed to start server '{server.name}': {e}") from e

    def _register_mcp_tools(self: Any, server: StdioMCPServer) -> None:
        adapters = stdio_adapter_registry.register_adapters(
            tenant_id=server.tenant_id,
            server_name=server.name,
            tools=server.tools,
        )
        for adapter in adapters:
            stdio_adapter_registry.register_with_tool_registry(adapter)
        for tool in server.tools:
            adapter_name = f"mcp_{server.name}_{tool.name}"
            self._tool_name_to_server[adapter_name] = f"{server.tenant_id}:{server.name}"

    async def unregister_server(self: Any, tenant_id: str, name: str) -> bool:
        servers = self._get_tenant_servers(tenant_id)
        server = servers.get(name)

        if not server:
            return False

        server.status = ServerStatus.STOPPING

        if server.protocol:
            try:
                await server.protocol.close()
            except Exception as e:
                logger.warning(f"[StdioMCP] Error closing server '{name}': {e}")

        if server.process and server.process.returncode is None:
            try:
                server.process.terminate()
                await asyncio.wait_for(server.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                server.process.kill()
                await server.process.wait()
            except Exception as e:
                logger.warning(f"[StdioMCP] Error terminating server '{name}': {e}")

        self._unregister_mcp_tools(server)

        del servers[name]
        logger.info(f"[StdioMCP] Stopped server '{name}' for tenant '{tenant_id}'")

        if not servers and tenant_id in self._tenant_servers:
            del self._tenant_servers[tenant_id]

        return True

    def _unregister_mcp_tools(self: Any, server: StdioMCPServer) -> None:
        for tool in server.tools:
            adapter_name = f"mcp_{server.name}_{tool.name}"
            stdio_adapter_registry.unregister_from_tool_registry(adapter_name)
        stdio_adapter_registry.unregister_adapters(server.tenant_id, server.name)
        for tool in server.tools:
            adapter_name = f"mcp_{server.name}_{tool.name}"
            self._tool_name_to_server.pop(adapter_name, None)
