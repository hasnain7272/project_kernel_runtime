"""
Stdio MCP Protocol - JSON-RPC 2.0 over stdio

Implements the Model Context Protocol for communication with MCP servers
via stdin/stdout using JSON-RPC 2.0 message format.
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

from src.services.mcp.stdio_messages import (
    MCPProtocolError,
    MCPRequestError,
    JSONRPCRequest,
    JSONRPCResponse,
    ToolManifest,
)

from src.services.mcp.stdio_writer import StdinStdoutWriter

logger = logging.getLogger(__name__)

class MCPStdioProtocol:
    def __init__(self, process: asyncio.subprocess.Process):
        self._process = process
        self._writer = StdinStdoutWriter(process)
        self._request_id = 0
        self._lock = asyncio.Lock()
        self._initialized = False
        self._capabilities: Dict[str, Any] = {}

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def capabilities(self) -> Dict[str, Any]:
        return self._capabilities

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    async def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        async with self._lock:
            request = JSONRPCRequest(
                id=self._next_id(),
                method=method,
                params=params,
            )
            await self._writer.write(request.to_json())

            response_line = await self._writer.read_line()
            response = JSONRPCResponse.from_json(response_line)

            if response.is_error:
                error = response.error or {}
                raise MCPRequestError(
                    code=error.get("code", -32603),
                    message=error.get("message", "Unknown error"),
                    data=error.get("data"),
                )

            return response.result

    async def initialize(self, client_info: Dict[str, Any]) -> Dict[str, Any]:
        result = await self._send_request(
            "initialize",
            {
                "clientInfo": client_info,
                "protocolVersion": "2024-11-05",
            }
        )

        self._capabilities = result.get("capabilities", {})
        self._initialized = True

        await self._send_request("notifications/initialized", {})

        logger.info(f"[MCP Stdio] Initialized server: {result.get('serverInfo', {})}")
        return result

    async def list_tools(self) -> List[ToolManifest]:
        result = await self._send_request("tools/list")
        tools = result.get("tools", [])
        return [ToolManifest.from_dict(t) for t in tools]

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        result = await self._send_request(
            "tools/call",
            {
                "name": tool_name,
                "arguments": arguments,
            }
        )
        return result

    async def ping(self) -> bool:
        try:
            await self._send_request("ping")
            return True
        except Exception:
            return False

    async def close(self) -> None:
        if self._process.returncode is None:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()
                await self._process.wait()
        logger.info("[MCP Stdio] Connection closed")
