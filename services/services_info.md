# services Module Information

This file provides an ultra-dense context mapping for agentic AI ingestion.


## File: `fastapi_server.py`
Imports: fastapi.{FastAPI,WebSocket,HTTPException,Depends}, fastapi.middleware.cors.{CORSMiddleware}, fastapi.responses.{JSONResponse}, uvicorn, json, typing.{List,Dict,Any,Optional}, datetime.{datetime}, asyncio, contextlib.{asynccontextmanager}, sys, os, project_kernel_runtime.kernel.task_state_machine.{TaskStatus}, project_kernel_runtime.services.research_api.{router}, project_kernel_runtime.memory.state_hub.{state_hub}, fastapi.responses.{RedirectResponse}, fastapi.staticfiles.{StaticFiles}, os, project_kernel_runtime.services.router_agent.{router}, project_kernel_runtime.services.router_mcp.{router}
Func `async def lifespan(app)` (L37-45) - Lifecycle event handler for the FastAPI app.
Func `async def websocket_ui(websocket)` (L77-84) - WebSocket endpoint for real-time UI control panel.
Func `async def get_ui_schema()` (L88-155) - Get UI schema for dynamic control panel.
Func `async def get_all_params()` (L159-181) - Get all parameters.
Func `async def get_param(param_id)` (L184-204) - Get a single parameter.
Func `async def set_param(param_id, value)` (L207-230) - Set a parameter value.
Func `async def root_redirect()` (L242-243)
Func `async def list_mcp_servers()` (L247-251) - List all MCP servers.
Func `async def start_mcp_server(name)` (L254-259) - Start an MCP server.
Func `async def stop_mcp_server(name)` (L262-267) - Stop an MCP server.
Func `async def get_mcp_server_status(name)` (L270-277) - Get MCP server status.
Func `async def list_a2a_peers()` (L281-285) - List all A2A peers.
Func `async def get_a2a_status()` (L288-295) - Get A2A mesh status.
Func `async def delegate_a2a_task(request)` (L298-302) - Delegate a task to another agent.
Func `async def get_governance_status()` (L306-313) - Get governance status.
Func `async def get_governance_audit(limit)` (L316-321) - Get governance audit log.
Func `async def list_sessions()` (L324-328) - List all sessions.
Func `async def create_session(request)` (L331-334) - Create a new session.
Func `async def health_check()` (L342-366) - Health check endpoint
Func `async def websocket_endpoint(websocket, user_id)` (L370-418) - WebSocket endpoint for real-time communication
Func `async def handle_websocket_message(user_id, message)` (L420-572) - Handle WebSocket message
Func `async def prometheus_metrics()` (L582-590) - Prometheus-compatible metrics endpoint.
Func `async def full_system_status()` (L594-624) - Comprehensive system status including all subsystems.
Func `async def global_exception_handler(request, exc)` (L628-646) - Global exception handler
Func `def run_server(host, port)` (L648-662) - Run the FastAPI server

## File: `research_api.py`
Imports: fastapi.{APIRouter,HTTPException}, typing.{Dict,Any}, project_kernel_runtime.kernel.orchestrator.{Orchestrator}
Func `async def start_research(body)` (L9-22)
Func `async def list_sessions(user_id)` (L26-33)
Func `async def add_source(session_id, body)` (L37-56)
Func `async def list_reports(session_id, user_id)` (L60-70)
Func `async def summarize(session_id, body)` (L74-92)
Func `async def get_session(session_id, user_id)` (L96-108)
Func `async def get_progress(session_id, user_id)` (L112-121)
Func `async def get_sources(session_id, user_id)` (L125-135)
Func `async def end_session(session_id, body)` (L139-152)
Func `async def export_report(session_id, report_id, user_id, format)` (L156-164)

## File: `router_agent.py`
Imports: fastapi.{APIRouter,HTTPException,Depends}, typing.{Dict,Any,Optional}, datetime.{datetime}, project_kernel_runtime.memory.state_hub.{state_hub}, fastapi.responses.{StreamingResponse}, asyncio, json
Func `async def patch_system_provider(request)` (L9-53) - Hot-swap the system inference provider (Ollama, OpenAI, Anthropic) with custom h
Func `async def create_session(request)` (L56-81)
Func `async def end_session(user_id)` (L84-94)
Func `async def get_session(user_id)` (L97-120)
Func `async def create_task(request)` (L123-159)
Func `async def execute_task(task_id, request)` (L162-180)
Func `async def stop_task(task_id, request)` (L183-211)
Func `async def get_task_status(task_id, user_id)` (L214-249)
Func `async def get_task_trace(task_id)` (L252-265)
Func `async def list_tasks(user_id, status)` (L268-298)
Func `async def inject_memory(request)` (L305-322)
Func `async def search_memory(request)` (L325-342)
Func `async def tweak_governance(request)` (L345-359)
Func `async def get_governance()` (L362-366)
Func `async def call_tool(request)` (L369-389)
Func `async def get_available_skills(user_id)` (L392-402)
Func `async def get_intelligence_status(user_id)` (L405-448)
Func `async def get_thought_stream()` (L451-454)
Func `async def hot_reload_logic(data)` (L457-466)
Func `async def trigger_gtm_campaign(data)` (L469-479)
Func `async def reprobe_mcp(data)` (L482-490)
Func `async def launch_app(data)` (L493-501)
Func `async def dispatch_scratchpad(data)` (L504-519)
Func `async def get_mcp_discovery()` (L522-536)
Func `async def get_vision_config()` (L539-543)
Func `async def update_vision_config(data)` (L546-553)
Func `async def get_credits_balance(tenant_id)` (L556-560)
Func `async def get_intelligence_status(user_id)` (L563-606)
Func `async def get_thought_stream()` (L609-612)
Func `async def hot_reload_logic(data)` (L615-624)
Func `async def trigger_gtm_campaign(data)` (L627-637)
Func `async def reprobe_mcp(data)` (L640-648)
Func `async def launch_app(data)` (L651-659)
Func `async def dispatch_scratchpad(data)` (L662-677)
Func `async def get_mcp_discovery()` (L680-694)
Func `async def get_vision_config()` (L697-701)
Func `async def update_vision_config(data)` (L704-711)
Func `async def get_credits_balance(tenant_id)` (L714-718)
Func `async def list_mcps()` (L721-735) - List all mounted MCP servers (both memory and permanent registry).
Func `async def mount_new_mcp(data)` (L738-789) - Mount a new MCP protocol and optionally save to persistence.
Func `async def execute_agent_stream(description, user_id, max_iterations)` (L799-888) - SSE endpoint that streams every step of the agentic loop to the UI in real-time.
Func `async def get_mcp_discovery()` (L891-905)
Func `async def get_vision_config()` (L908-912)
Func `async def update_vision_config(data)` (L915-922)
Func `async def get_credits_balance(tenant_id)` (L925-929)
Func `async def a2a_agent_card()` (L932-937)
Func `async def execute_agentic_loop(request)` (L941-966)
Func `async def fork_reality(request)` (L969-990)
Func `async def sre_auto_heal(request)` (L994-1010)

## File: `router_mcp.py`
Imports: fastapi.{APIRouter,HTTPException,Request}, typing.{Dict,Any}, json
Func `async def mcp_streamable_http_post(request)` (L8-23)
Func `async def mcp_streamable_http_get()` (L27-36)
Func `async def a2a_jsonrpc(request)` (L44-58)

## File: `ui_websocket.py`
Imports: asyncio, json, logging, uuid, yaml, datetime.{datetime,timezone}, pathlib.{Path}, typing.{Any,Dict,List,Optional,Set}, dataclasses.{dataclass,field}, enum.{Enum}, fastapi.{WebSocket,WebSocketDisconnect,Query}
Class `MessageType` (L26-32):
Class `WebSocketClient` (L36-41):
  > Docs: Connected UI client.
Class `ConfigManager` (L44-149):
  > Docs: Standalone config manager without kernel dependencies.
  - `def __init__(self)` (L47-50)
  - `def load(self)` (L52-55)
  - `def get(self, param_id, default)` (L57-65)
  - `def set(self, param_id, value)` (L67-81)
  - `def get_all(self)` (L83-93)
  - `def get_schema(self)` (L95-149)
Class `UIEventBroadcaster` (L152-200):
  > Docs: Broadcasts events to connected UI clients.
  - `def __init__(self, max_buffer_size)` (L155-158)
  - `async def connect(self, client_id, websocket)` (L160-164)
  - `async def disconnect(self, client_id)` (L166-169)
  - `async def send_to(self, client_id, message)` (L171-181)
  - `async def broadcast(self, message, event_type)` (L183-193)
  - `async def get_buffered_events(self, limit)` (L195-196)
  - `def client_count(self)` (L199-200)
Class `UIWebSocketHandler` (L203-318):
  > Docs: Handles UI WebSocket connections.
  - `def __init__(self)` (L206-208)
  - `async def handle_connection(self, websocket, client_id)` (L210-232)
  - `async def _handle_message(self, client, data)` (L234-269)
  - `async def _handle_get_schema(self, client, params)` (L271-272)
  - `async def _handle_get_param(self, client, params)` (L274-279)
  - `async def _handle_get_all_params(self, client, params)` (L281-282)
  - `async def _handle_set_param(self, client, params)` (L284-299)
  - `async def _handle_subscribe(self, client, params)` (L301-305)
  - `async def _handle_unsubscribe(self, client, params)` (L307-311)
  - `async def _handle_get_status(self, client, params)` (L313-318)
Func `def get_ui_websocket_handler()` (L323-327)
Func `async def ui_websocket_endpoint(websocket, client_id)` (L330-335)