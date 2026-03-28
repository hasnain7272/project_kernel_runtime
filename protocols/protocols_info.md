# protocols Module Information

This file provides an ultra-dense context mapping for agentic AI ingestion.


## File: `federated_hub.py`
Imports: logging, time, typing.{Any,Dict,List}
Class `FederatedHub` (L17-79):
  > Docs: Federated knowledge sharing hub between agent instances.
  - `def __init__(self)` (L20-24)
  - `async def start_gossip(self)` (L26-29) - Start gossip protocol for peer metric exchange.
  - `async def stop_gossip(self)` (L31-32)
  - `def share_pattern(self, pattern_type, data, anonymize)` (L34-44) - Share a task pattern with the federation.
  - `def query_patterns(self, pattern_type, limit)` (L46-52) - Query shared patterns.
  - `def sync_metrics(self, peer_id, metrics)` (L54-60) - Receive metrics from a peer for aggregation.
  - `def get_aggregated_metrics(self)` (L62-73) - Get aggregated metrics across peers.
  - `def _anonymize(data)` (L76-79) - Remove PII from shared data.

## File: `mcp_client.py`
Imports: asyncio, json, typing.{Dict,List,Optional,Any,Callable}, dataclasses.{dataclass}, websockets, websockets.exceptions.{ConnectionClosedError}
Class `MCPTool` (L15-19):
  > Docs: MCP Tool definition
Class `MCPResource` (L22-27):
  > Docs: MCP Resource definition
Class `MCPPrompt` (L30-34):
  > Docs: MCP Prompt definition
Class `MCPClient` (L36-281):
  > Docs: Client for MCP server communication
  - `def __init__(self, server_url)` (L39-46)
  - `async def connect(self)` (L48-57) - Connect to MCP server
  - `async def disconnect(self)` (L59-63) - Disconnect from MCP server
  - `async def _initialize(self)` (L65-94) - Initialize MCP connection
  - `async def _list_tools(self)` (L96-113) - List available tools
  - `async def _list_resources(self)` (L115-133) - List available resources
  - `async def _list_prompts(self)` (L135-152) - List available prompts
  - `async def call_tool(self, tool_name, arguments)` (L154-173) - Call an MCP tool
  - `async def read_resource(self, uri)` (L175-193) - Read an MCP resource
  - `async def get_prompt(self, prompt_name, arguments)` (L195-223) - Get an MCP prompt
  - `def _next_id(self)` (L225-228) - Get next message ID
  - `async def _send_request(self, request)` (L230-247) - Send JSON-RPC request and wait for response
  - `async def _message_handler(self)` (L249-268) - Handle incoming messages from MCP server
  - `async def _handle_notification(self, notification)` (L270-281) - Handle MCP notifications

## File: `mcp_server.py`
Imports: asyncio, json, logging, uuid, dataclasses.{dataclass,field}, datetime.{datetime,timezone}, typing.{Any,Callable,Dict,List,Optional}
Class `MCPTool` (L34-39):
  > Docs: MCP Tool definition.
Class `MCPResource` (L43-49):
  > Docs: MCP Resource definition.
Class `MCPPrompt` (L53-58):
  > Docs: MCP Prompt definition.
Class `MCPSession` (L62-70):
  > Docs: MCP session for Streamable HTTP.
Class `MCPServer` (L77-464):
  > Docs: MCP Server with dual transport: Streamable HTTP + WebSocket.
  - `def __init__(self, host, port)` (L89-107)
  - `def _setup_handlers(self)` (L109-122) - Setup JSON-RPC method handlers.
  - `def register_tool(self, tool)` (L126-130) - Register a tool with the server.
  - `def register_resource(self, resource)` (L132-133)
  - `def register_prompt(self, prompt)` (L135-136)
  - `def register_tools_from_executor(self, tool_executor)` (L138-150) - Auto-register tools from the ToolExecutor's tool registry.
  - `async def handle_streamable_http_post(self, body, headers)` (L154-175) - Handle POST requests (Streamable HTTP transport).
  - `async def handle_streamable_http_get(self, headers)` (L177-204) - Handle GET requests — return SSE stream.
  - `async def _process_jsonrpc(self, data, session)` (L208-242) - Process a single JSON-RPC request.
  - `async def _handle_initialize(self, params, session)` (L246-276) - Handle initialize — protocol negotiation.
  - `async def _handle_initialized(self, params, session)` (L278-280) - Client confirms initialization — notification, no response.
  - `async def _handle_tools_list(self, params, session)` (L282-292)
  - `async def _handle_tools_call(self, params, session)` (L294-322)
  - `async def _handle_resources_list(self, params, session)` (L324-335)
  - `async def _handle_resources_read(self, params, session)` (L337-344)
  - `async def _handle_prompts_list(self, params, session)` (L346-356)
  - `async def _handle_prompts_get(self, params, session)` (L358-369)
  - `async def _handle_ping(self, params, session)` (L371-372)
  - `async def _handle_sampling(self, params, session)` (L374-380) - Handle sampling/createMessage — delegate to LLM provider.
  - `async def _notify_tools_changed(self)` (L384-399) - Notify all clients that tools list changed.
  - `async def emit_sse_event(self, event_type, data, session_id)` (L401-418) - Emit an SSE event to subscribers.
  - `async def start_websocket(self)` (L422-432) - Start WebSocket server (legacy transport).
  - `async def _handle_ws_connection(self, websocket, path)` (L434-454) - Handle a WebSocket connection.
  - `def _error_response(msg_id, code, message)` (L459-464)

## File: `mesh_p2p.py`
Imports: logging, time, typing.{Any,Dict,List,Optional}, uuid.{uuid4}
Class `PeerInfo` (L18-37):
  > Docs: Information about a peer in the mesh.
  - `def __init__(self, peer_id, address, port, capabilities, metadata)` (L20-30)
  - `def to_dict(self)` (L32-37)
Class `GlobalMeshP2P` (L40-112):
  > Docs: Peer-to-peer mesh network for agent discovery and coordination.
  - `def __init__(self, heartbeat_timeout)` (L43-47)
  - `def register_self(self, address, port, capabilities)` (L49-54) - Register this node in the mesh.
  - `def register_peer(self, peer_id, address, port, capabilities)` (L56-61)
  - `def heartbeat(self, peer_id)` (L63-71) - Record heartbeat from peer.
  - `def health_check(self)` (L73-81) - Check health of all peers, mark stale ones.
  - `def discover_peers(self, capability)` (L83-88) - Find peers, optionally filtered by capability.
  - `def remove_stale_peers(self)` (L90-96) - Remove peers that haven't sent heartbeats.
  - `def federated_sync(self, metrics)` (L98-104) - Sync metrics with mesh (called by orchestrator).
  - `def get_mesh_status(self)` (L106-112)