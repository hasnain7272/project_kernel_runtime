"""
Stdio MCP Health - Background health checks and auto-restart logic.
"""
import asyncio
import logging
import time
from typing import Any

from src.services.mcp.stdio_models import StdioMCPServer, ServerStatus

logger = logging.getLogger(__name__)


class StdioMCPHealthMixin:
    def _start_health_check_loop(self: Any) -> None:
        if self._health_check_task is None or self._health_check_task.done():
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            logger.info("[StdioMCP] Started background health check loop")

    async def _health_check_loop(self: Any) -> None:
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                await self._check_all_servers()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[StdioMCP] Error in health check loop: {e}")

    async def _check_all_servers(self: Any) -> None:
        current_time = time.time()
        for tenant_id, servers in list(self._tenant_servers.items()):
            for name, server in list(servers.items()):
                if server.status != ServerStatus.RUNNING:
                    continue

                server.last_health_check = current_time
                is_healthy = False

                if server.protocol and server.process and server.process.returncode is None:
                    try:
                        is_healthy = await asyncio.wait_for(server.protocol.ping(), timeout=5.0)
                    except Exception:
                        is_healthy = False
                else:
                    is_healthy = False

                if not is_healthy:
                    logger.warning(
                        f"[StdioMCP] Health check failed for '{server.name}' (tenant: {tenant_id})"
                    )
                    server.status = ServerStatus.ERROR
                    
                    if server.metrics.restart_count < self._max_restart_attempts:
                        await self._restart_server(server)
                    else:
                        logger.error(
                            f"[StdioMCP] Server '{server.name}' exceeded max restart attempts."
                        )

    async def _restart_server(self: Any, server: StdioMCPServer) -> None:
        logger.info(
            f"[StdioMCP] Attempting restart {server.metrics.restart_count + 1}/{self._max_restart_attempts} "
            f"for server '{server.name}'"
        )
        
        server.status = ServerStatus.RESTARTING
        server.metrics.restart_count += 1
        
        if server.protocol:
            try:
                await server.protocol.close()
            except Exception:
                pass
                
        if server.process and server.process.returncode is None:
            try:
                server.process.terminate()
            except Exception:
                pass

        try:
            self._unregister_mcp_tools(server)
            await self._start_server(server)
            logger.info(f"[StdioMCP] Successfully restarted server '{server.name}'")
        except Exception as e:
            logger.error(f"[StdioMCP] Failed to restart server '{server.name}': {e}")
            server.status = ServerStatus.ERROR
