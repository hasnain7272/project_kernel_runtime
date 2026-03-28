# integrations Module Information

This file provides an ultra-dense context mapping for agentic AI ingestion.


## File: `a2a_handshake.py`
Imports: json, asyncio, typing.{Dict,Any,List,Optional}, a2a_protocol.{A2AHandler,A2AMessage,A2AMessageType,AgentCard}
Class `A2AHandshakeManager` (L12-44):
  > Docs: Manages the broadcast and reception of A2A handshakes.
  - `def __init__(self, handler)` (L15-18)
  - `async def start_broadcasting(self)` (L20-30) - Periodically broadcast the agent card to the local network.
  - `async def _simulate_network_broadcast(self, message_json)` (L32-35) - Simulates sending a message to the local A2A mesh.
  - `def stop(self)` (L37-38)
  - `async def handle_peer_response(self, response_json)` (L40-44) - Process a response from a peer found via handshake.

## File: `a2a_protocol.py`
Imports: json, logging, enum.{Enum}, datetime.{datetime,timezone}, typing.{Any,Dict,List,Optional}, uuid.{uuid4}
Class `A2ATaskState` (L29-36):
  > Docs: A2A v0.3 task lifecycle states.
Class `AgentSkill` (L39-54):
  > Docs: Capability advertised by an agent.
  - `def __init__(self, id, name, description, tags, examples)` (L41-47)
  - `def to_dict(self)` (L49-54)
Class `AgentCapabilities` (L57-70):
  > Docs: What the agent supports.
  - `def __init__(self, streaming, push_notifications, state_transition_history)` (L59-63)
  - `def to_dict(self)` (L65-70)
Class `AgentCard` (L73-107):
  > Docs: A2A v0.3 Agent Card — identity and capability descriptor.
  - `def __init__(self, id, name, description, url, version, capabilities, skills, default_input_modes, default_output_modes)` (L75-95)
  - `def to_dict(self)` (L97-107)
Class `A2APart` (L110-129):
  > Docs: Content part in an A2A message.
  - `def __init__(self, type, text, mime_type, data, metadata)` (L112-118)
  - `def to_dict(self)` (L120-129)
Class `A2AMessage` (L132-145):
  > Docs: A2A v0.3 message with typed parts.
  - `def __init__(self, role, parts, metadata)` (L134-138)
  - `def to_dict(self)` (L140-145)
Class `A2AArtifact` (L148-162):
  > Docs: An artifact produced by a task.
  - `def __init__(self, id, name, parts, metadata)` (L150-155)
  - `def to_dict(self)` (L157-162)
Class `A2ATask` (L165-197):
  > Docs: A2A v0.3 task with full lifecycle.
  - `def __init__(self, id, session_id)` (L167-176)
  - `def transition(self, new_state)` (L178-186) - Transition task state with history tracking.
  - `def to_dict(self)` (L188-197)
Class `A2AHandler` (L204-332):
  > Docs: Google A2A v0.3 protocol handler.
  - `def __init__(self, owner_card)` (L215-219)
  - `def get_agent_card(self)` (L223-225) - Return agent card for /.well-known/agent.json.
  - `async def handle_jsonrpc(self, method, params)` (L229-240) - Route A2A JSON-RPC methods.
  - `async def _handle_task_send(self, params)` (L242-267) - Create or update a task (tasks/send).
  - `async def _handle_task_get(self, params)` (L269-275) - Get task status (tasks/get).
  - `async def _handle_task_cancel(self, params)` (L277-284) - Cancel a task (tasks/cancel).
  - `async def _handle_task_send_subscribe(self, params)` (L286-290) - Send task and subscribe to updates (tasks/sendSubscribe).
  - `def register_peer(self, card)` (L294-296)
  - `def handle_incoming(self, raw_message)` (L298-318) - Legacy incoming message handler (backward compat).
  - `def list_peers(self)` (L320-321)
  - `def create_handshake(self)` (L323-332) - Generate handshake message.
Class `GA2AMeshV2` (L339-349):
  > Docs: Merged from a2a_protocol_v2 — mesh networking for A2A.
  - `def __init__(self, owner_card)` (L342-343)
  - `async def broadcast_presence(self)` (L345-346)
  - `def handle_message(self, raw)` (L348-349)

## File: `a2a_protocol_v2.py`
Imports: a2a_protocol.{AgentCard,A2AHandler,A2ATask,A2ATaskState,A2AMessage,A2APart,A2AArtifact,GA2AMeshV2}

## File: `browser_mcp.py`
Imports: mcp.server.fastmcp.{FastMCP}, asyncio, httpx, typing.{Dict,Any}
Func `async def browser_navigate(url)` (L14-18) - Navigates the sovereign browser instance to a specific URL.
Func `async def browser_extract(selector)` (L21-27) - Extracts data from the current page using a CSS selector.
Func `async def browser_dispatch(directive)` (L30-32) - Dispatches a complex web-mission (e.g., 'Search for 3D benchmarks').
Func `async def browser_screenshot()` (L35-37) - Captures a high-resolution buffer of the current browser viewport.

## File: `mcp_registry.yaml`
Total Lines: 54

## File: `universal_mcp.py`
Imports: asyncio, httpx, os, yaml, typing.{Dict,Any,List,Optional}, project_kernel_runtime.memory.state_hub.{state_hub}
Class `UniversalMCP` (L8-152):
  - `def __init__(self, registry_path)` (L9-14)
  - `def _load_registry(self)` (L16-21) - Load discovered MCPs from persistent storage.
  - `def _save_registry(self)` (L23-26) - Save discovered MCPs to persistent storage.
  - `def _rebuild_tool_map(self)` (L28-32) - Rebuild tool_map from discovered_servers.
  - `async def add_server(self, url)` (L34-102) - Adds and probes a new MCP server via SSE.
  - `async def initiate_mcp_discovery(self)` (L104-114) - Background task to discover local and configured MCP servers.
  - `async def execute_mcp_tool(self, tool_name, arguments)` (L116-127) - Routes execution to the target MCP server via SSE.
  - `async def reprobe_server(self, url)` (L129-135) - Manually re-probe an existing server to update status and tools.
  - `async def check_health(self)` (L137-152) - Background health check for all registered servers.