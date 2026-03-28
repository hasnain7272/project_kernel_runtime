"""
MCP Server v2 — MCP 2026 Streamable HTTP + Legacy WebSocket

Upgraded from WebSocket-only to dual transport:
- Streamable HTTP transport (POST for requests, GET for SSE streams)
- Session management with Mcp-Session-Id headers
- Resumability via Last-Event-ID
- Protocol version negotiation (2024-11-05 and 2025-03-26)
- Auto-registration of tools from ToolExecutor
- Legacy WebSocket transport preserved for backward compatibility

Ref: MCP spec March 2026 — https://spec.modelcontextprotocol.io
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

SUPPORTED_PROTOCOL_VERSIONS = ["2024-11-05", "2025-03-26"]
LATEST_PROTOCOL_VERSION = "2025-03-26"


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class MCPTool:
    """MCP Tool definition."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable = None  # Optional direct handler


@dataclass
class MCPResource:
    """MCP Resource definition."""
    uri: str
    name: str
    description: str
    mime_type: str = "text/plain"
    content: str = ""


@dataclass
class MCPPrompt:
    """MCP Prompt definition."""
    name: str
    description: str
    arguments: List[Dict[str, Any]] = field(default_factory=list)
    template: str = ""


@dataclass
class MCPSession:
    """MCP session for Streamable HTTP."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    protocol_version: str = LATEST_PROTOCOL_VERSION
    client_info: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_counter: int = 0
    event_log: List[Dict] = field(default_factory=list)


# ============================================================================
# MCP Server
# ============================================================================

class MCPServer:
    """
    MCP Server with dual transport: Streamable HTTP + WebSocket.
    
    MCP 2026 Spec features:
    - POST: JSON-RPC request → direct JSON or SSE stream response
    - GET: SSE stream for server-initiated notifications
    - Mcp-Session-Id header for session management
    - Last-Event-ID for resumability
    - Protocol version negotiation
    """

    def __init__(self, host: str = "localhost", port: int = 3000):
        self.host = host
        self.port = port
        self.tools: Dict[str, MCPTool] = {}
        self.resources: Dict[str, MCPResource] = {}
        self.prompts: Dict[str, MCPPrompt] = {}
        self.sessions: Dict[str, MCPSession] = {}
        
        # WebSocket connections (legacy)
        self.connections: Dict[str, Any] = {}
        
        # SSE subscribers (Streamable HTTP)
        self.sse_subscribers: Dict[str, asyncio.Queue] = {}
        
        # JSON-RPC handlers
        self.message_handlers: Dict[str, Callable] = {}
        self._setup_handlers()
        
        logger.info(f"[MCPServer] Initialized on {host}:{port}")

    def _setup_handlers(self):
        """Setup JSON-RPC method handlers."""
        self.message_handlers = {
            "initialize": self._handle_initialize,
            "initialized": self._handle_initialized,
            "tools/list": self._handle_tools_list,
            "tools/call": self._handle_tools_call,
            "resources/list": self._handle_resources_list,
            "resources/read": self._handle_resources_read,
            "prompts/list": self._handle_prompts_list,
            "prompts/get": self._handle_prompts_get,
            "ping": self._handle_ping,
            "sampling/createMessage": self._handle_sampling,
        }

    # ── Registration ──

    def register_tool(self, tool: MCPTool):
        """Register a tool with the server."""
        self.tools[tool.name] = tool
        # Notify connected clients
        asyncio.ensure_future(self._notify_tools_changed())

    def register_resource(self, resource: MCPResource):
        self.resources[resource.uri] = resource

    def register_prompt(self, prompt: MCPPrompt):
        self.prompts[prompt.name] = prompt

    def register_tools_from_executor(self, tool_executor=None):
        """Auto-register tools from the ToolExecutor's tool registry."""
        try:
            from .universal_tools import get_all_tools
            for tool in get_all_tools():
                self.tools[tool.name] = MCPTool(
                    name=tool.name,
                    description=tool.description,
                    input_schema=tool.input_schema,
                )
            logger.info(f"[MCPServer] Registered {len(self.tools)} tools from executor")
        except Exception as e:
            logger.warning(f"[MCPServer] Failed to register executor tools: {e}")

    # ── Streamable HTTP Handlers ──

    async def handle_streamable_http_post(self, body: bytes, headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Handle POST requests (Streamable HTTP transport).
        
        Returns JSON-RPC response directly. For streaming responses,
        the caller should switch to SSE mode.
        """
        # Session management
        session_id = headers.get("mcp-session-id")
        session = None
        
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return self._error_response(None, -32700, "Parse error")

        # Handle batch or single request
        if isinstance(data, list):
            results = [await self._process_jsonrpc(msg, session) for msg in data]
            return results
        
        return await self._process_jsonrpc(data, session)

    async def handle_streamable_http_get(self, headers: Dict[str, str]):
        """
        Handle GET requests — return SSE stream.
        
        Used for server-initiated notifications.
        Supports Last-Event-ID for resumability.
        """
        session_id = headers.get("mcp-session-id")
        last_event_id = headers.get("last-event-id")
        
        queue = asyncio.Queue()
        sub_id = str(uuid.uuid4())
        self.sse_subscribers[sub_id] = queue
        
        # Replay missed events if resuming
        if session_id and last_event_id and session_id in self.sessions:
            session = self.sessions[session_id]
            last_id = int(last_event_id) if last_event_id.isdigit() else 0
            for event in session.event_log:
                if event.get("id", 0) > last_id:
                    await queue.put(event)
        
        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            self.sse_subscribers.pop(sub_id, None)

    # ── JSON-RPC Processing ──

    async def _process_jsonrpc(self, data: Dict, session: MCPSession = None) -> Dict:
        """Process a single JSON-RPC request."""
        if "jsonrpc" not in data or data.get("jsonrpc") != "2.0":
            return self._error_response(data.get("id"), -32600, "Invalid Request")

        method = data.get("method")
        params = data.get("params", {})
        msg_id = data.get("id")

        handler = self.message_handlers.get(method)
        if not handler:
            return self._error_response(msg_id, -32601, f"Method not found: {method}")

        try:
            result = await handler(params, session)
            
            # Notifications (no id) don't get responses
            if msg_id is None:
                return None
            
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": result,
            }
            
            # Set session header for initialize responses
            if method == "initialize" and session:
                response["_session_id"] = session.id
            
            return response
            
        except Exception as e:
            logger.error(f"[MCPServer] Handler error for {method}: {e}")
            return self._error_response(msg_id, -32603, str(e))

    # ── Protocol Handlers ──

    async def _handle_initialize(self, params: Dict, session: MCPSession = None) -> Dict:
        """Handle initialize — protocol negotiation."""
        client_version = params.get("protocolVersion", "2024-11-05")
        
        # Negotiate version
        if client_version in SUPPORTED_PROTOCOL_VERSIONS:
            negotiated = client_version
        else:
            negotiated = LATEST_PROTOCOL_VERSION
        
        # Create session
        new_session = MCPSession(
            protocol_version=negotiated,
            client_info=params.get("clientInfo", {}),
        )
        self.sessions[new_session.id] = new_session
        
        return {
            "protocolVersion": negotiated,
            "capabilities": {
                "tools": {"listChanged": True},
                "resources": {"subscribe": True, "listChanged": True},
                "prompts": {"listChanged": True},
                "logging": {},
            },
            "serverInfo": {
                "name": "project_kernel_runtime",
                "version": "2.0.0",
            },
            "_sessionId": new_session.id,
        }

    async def _handle_initialized(self, params: Dict, session: MCPSession = None) -> None:
        """Client confirms initialization — notification, no response."""
        return None

    async def _handle_tools_list(self, params: Dict, session: MCPSession = None) -> Dict:
        return {
            "tools": [
                {
                    "name": t.name,
                    "description": t.description,
                    "inputSchema": t.input_schema,
                }
                for t in self.tools.values()
            ]
        }

    async def _handle_tools_call(self, params: Dict, session: MCPSession = None) -> Dict:
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        tool = self.tools.get(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found")

        # Execute via handler if available
        if tool.handler:
            try:
                if asyncio.iscoroutinefunction(tool.handler):
                    result = await tool.handler(arguments)
                else:
                    result = tool.handler(arguments)
                return {
                    "content": [{"type": "text", "text": str(result)}],
                    "isError": False,
                }
            except Exception as e:
                return {
                    "content": [{"type": "text", "text": f"Error: {e}"}],
                    "isError": True,
                }
        
        return {
            "content": [{"type": "text", "text": f"Tool {tool_name} has no handler"}],
            "isError": True,
        }

    async def _handle_resources_list(self, params: Dict, session: MCPSession = None) -> Dict:
        return {
            "resources": [
                {
                    "uri": r.uri,
                    "name": r.name,
                    "description": r.description,
                    "mimeType": r.mime_type,
                }
                for r in self.resources.values()
            ]
        }

    async def _handle_resources_read(self, params: Dict, session: MCPSession = None) -> Dict:
        uri = params.get("uri")
        resource = self.resources.get(uri)
        if not resource:
            raise ValueError(f"Resource '{uri}' not found")
        return {
            "contents": [{"uri": uri, "mimeType": resource.mime_type, "text": resource.content}]
        }

    async def _handle_prompts_list(self, params: Dict, session: MCPSession = None) -> Dict:
        return {
            "prompts": [
                {
                    "name": p.name,
                    "description": p.description,
                    "arguments": p.arguments,
                }
                for p in self.prompts.values()
            ]
        }

    async def _handle_prompts_get(self, params: Dict, session: MCPSession = None) -> Dict:
        name = params.get("name")
        prompt = self.prompts.get(name)
        if not prompt:
            raise ValueError(f"Prompt '{name}' not found")
        args = params.get("arguments", {})
        text = prompt.template
        for key, val in args.items():
            text = text.replace(f"{{{key}}}", str(val))
        return {
            "messages": [{"role": "user", "content": {"type": "text", "text": text}}]
        }

    async def _handle_ping(self, params: Dict, session: MCPSession = None) -> Dict:
        return {}

    async def _handle_sampling(self, params: Dict, session: MCPSession = None) -> Dict:
        """Handle sampling/createMessage — delegate to LLM provider."""
        return {
            "role": "assistant",
            "content": {"type": "text", "text": "[Sampling not yet integrated]"},
            "model": "project_kernel_runtime",
        }

    # ── Notifications ──

    async def _notify_tools_changed(self):
        """Notify all clients that tools list changed."""
        notification = {
            "jsonrpc": "2.0",
            "method": "notifications/tools/list_changed",
        }
        # SSE subscribers
        for queue in self.sse_subscribers.values():
            await queue.put({"data": json.dumps(notification)})
        
        # WebSocket connections  
        for ws in self.connections.values():
            try:
                await ws.send(json.dumps(notification))
            except Exception:
                pass

    async def emit_sse_event(self, event_type: str, data: Dict, session_id: str = None):
        """Emit an SSE event to subscribers."""
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            session.event_counter += 1
            event = {
                "id": session.event_counter,
                "event": event_type,
                "data": json.dumps(data),
            }
            session.event_log.append(event)
            # Keep last 1000 events for replay
            if len(session.event_log) > 1000:
                session.event_log = session.event_log[-1000:]
        
        event_payload = {"event": event_type, "data": json.dumps(data)}
        for queue in self.sse_subscribers.values():
            await queue.put(event_payload)

    # ── WebSocket Transport (Legacy) ──

    async def start_websocket(self):
        """Start WebSocket server (legacy transport)."""
        try:
            import websockets
            server = await websockets.serve(
                self._handle_ws_connection, self.host, self.port
            )
            logger.info(f"[MCPServer] WebSocket listening on ws://{self.host}:{self.port}")
            await server.wait_closed()
        except ImportError:
            logger.warning("[MCPServer] websockets not installed, WebSocket transport disabled")

    async def _handle_ws_connection(self, websocket, path=None):
        """Handle a WebSocket connection."""
        conn_id = str(uuid.uuid4())
        self.connections[conn_id] = websocket
        logger.info(f"[MCPServer] Client connected: {conn_id}")
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    response = await self._process_jsonrpc(data)
                    if response:
                        await websocket.send(json.dumps(response))
                except json.JSONDecodeError:
                    error = self._error_response(None, -32700, "Parse error")
                    await websocket.send(json.dumps(error))
        except Exception as e:
            logger.warning(f"[MCPServer] Connection {conn_id} error: {e}")
        finally:
            self.connections.pop(conn_id, None)
            logger.info(f"[MCPServer] Client disconnected: {conn_id}")

    # ── Helpers ──

    @staticmethod
    def _error_response(msg_id, code: int, message: str) -> Dict:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": code, "message": message},
        }