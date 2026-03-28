# kernel Module Information

This file provides an ultra-dense context mapping for agentic AI ingestion.


## File: `analytics.py`
Imports: time, typing.{Dict,Any,List,Optional}, dataclasses.{dataclass,field}, datetime.{datetime}
Class `TaskMetric` (L13-19):
Class `AnalyticsService` (L22-94):
  > Docs: Tracks and analyzes system performance metrics.
  - `def __init__(self)` (L25-27)
  - `def start_task_tracking(self, task_id)` (L29-31) - Initialize tracking for a new task.
  - `def record_step_timing(self, task_id, step_id, duration)` (L33-36) - Record how long a specific step took.
  - `def end_task_tracking(self, task_id, success)` (L38-44) - Finalize tracking for a task.
  - `def get_bottlenecks(self)` (L46-65) - Identify slow steps across all tasks.
  - `def get_task_metrics(self)` (L67-81) - Retrieve metrics for all tasks currently being tracked.
  - `def get_system_summary(self)` (L83-94) - Overall system efficiency summary.

## File: `credits_engine.py`
Imports: logging, os, sqlite3, time, typing.{Any,Dict,Optional}
Class `CreditsEngine` (L20-103):
  > Docs: Per-tenant usage metering and billing.
  - `def __init__(self, db_path)` (L23-27)
  - `def _init_db(self)` (L29-48)
  - `def record_usage(self, tenant_id, usage_type, quantity)` (L50-59) - Record a usage event.
  - `def get_usage(self, tenant_id, since)` (L61-72) - Get usage totals for a tenant.
  - `def check_quota(self, tenant_id, usage_type)` (L74-91) - Check if tenant is within quota.
  - `def set_quota(self, tenant_id, max_tool_calls, max_tokens, max_compute_sec)` (L93-99)
  - `def get_report(self, tenant_id)` (L101-103)

## File: `evaluation.py`
Imports: time, json, typing.{Dict,Any,List,Optional}, datetime.{datetime}
Class `BenchmarkProfile` (L12-16):
  > Docs: A set of tasks to evaluate an agent's success rate.
  - `def __init__(self, name, tasks)` (L14-16)
Class `EvaluationHarness` (L19-82):
  > Docs: Benchmarks the kernel's agentic performance.
  - `def __init__(self, orchestrator)` (L22-24)
  - `async def run_benchmark(self, profile)` (L26-63) - Run all tasks in the profile and record success metrics.
  - `def get_report(self)` (L65-77) - Calculate summary statistics for the benchmark.
  - `def save_to_file(self, path)` (L79-82) - Persist results for historical comparison.

## File: `event_bus.py`
Imports: asyncio, logging, collections.{defaultdict}, dataclasses.{dataclass,field}, datetime.{datetime,timezone}, typing.{Any,Callable,Coroutine,Dict,List,Optional}, uuid.{uuid4}
Class `AgentEvent` (L27-35):
  > Docs: Base event published through the event bus.
Class `EventTypes` (L39-111):
  > Docs: Known event types in the kernel.
Class `EventBus` (L121-270):
  > Docs: Asynchronous event bus for decoupled inter-subsystem communication.
  - `def __init__(self, max_log_size)` (L133-138)
  - `def subscribe(self, event_type, handler)` (L140-148) - Subscribe a handler to an event type.
  - `def unsubscribe(self, event_type, handler)` (L150-155) - Remove a handler from an event type.
  - `async def publish(self, event)` (L157-184) - Publish an event to all matching subscribers.
  - `async def publish_and_wait(self, event)` (L186-188) - Publish and wait for all handlers to complete.
  - `def emit(self, event_type, payload, source, session_id, task_id)` (L190-203) - Convenience method to create and return an event (does not publish).
  - `async def emit_and_publish(self, event_type, payload, source, session_id, task_id)` (L205-211) - Create, publish, and return an event in one call.
  - `def replay(self, from_event_id, event_type, limit)` (L213-238) - Replay events from the log for crash recovery or debugging.
  - `def get_event_log(self, last_n)` (L240-242) - Get the last N events from the log.
  - `def subscriber_count(self)` (L245-247) - Total number of active subscriptions.
  - `def _matches(pattern, event_type)` (L250-259) - Check if event type matches a subscription pattern.
  - `async def _safe_call(handler, event)` (L262-270) - Call a handler with error isolation.

## File: `export_service.py`
Imports: json, os, datetime.{datetime}, typing.{Dict,Any,List}, research.{ResearchReport,ResearchSession}
Class `ExportService` (L11-84):
  > Docs: Service to export research reports into MD, JSON, or PDF.
  - `def to_markdown(report, session)` (L15-35) - Convert a report to a Markdown string.
  - `def to_json(report)` (L38-40) - Convert a report to a JSON string.
  - `def to_pdf(report, session, output_path)` (L43-84) - Export to PDF. 

## File: `governance.py`
Imports: asyncio, json, logging, os, sqlite3, datetime.{datetime,timezone}, enum.{Enum}, typing.{Dict,List,Optional,Set}, uuid.{uuid4}
Class `ExecutionMode` (L33-37):
Class `PolicyDecision` (L40-43):
Class `UserRole` (L46-50):
Class `AuditStore` (L118-206):
  > Docs: SQLite-backed persistent audit trail.
  - `def __init__(self, db_path)` (L121-124)
  - `def _init_db(self)` (L126-150) - Create audit table if not exists.
  - `def log(self, event)` (L152-177) - Append an audit event to the persistent log.
  - `def query(self, user_id, limit, since)` (L179-206) - Query audit log entries.
Class `GovernanceEngine` (L213-509):
  > Docs: Production governance engine with real enforcement.
  - `def __init__(self, policy_matrix, config)` (L226-247)
  - `def check_tool_allowed(self, tool_name, mode, task_id, user_role)` (L249-320) - Check if a tool is allowed in the given mode and role.
  - `def check_permission(self, tool_name, user_role, execution_mode, mutability)` (L322-354) - Unified permission check (used by ToolExecutor).
  - `def requires_approval(self, tool_name)` (L356-358) - Check if a tool requires human approval before execution.
  - `async def request_approval(self, tool_call_id, tool_name, arguments, user_id)` (L360-376) - Queue a tool call for human approval.
  - `async def resolve_approval(self, approval_id, approved, reviewer_id)` (L378-389) - Resolve a pending approval request.
  - `def check_network_access(self, url, allowlist)` (L391-412) - Check if a URL is allowed by the network policy.
  - `async def load_project_rules(self, workspace_path)` (L414-440) - Load .agentrules file from workspace (Cursor's .cursorrules equivalent).
  - `def project_rules(self)` (L443-445) - Get loaded project rules.
  - `async def check_skill_permission(self, user_id, skill_name, level)` (L447-453) - Check skill permission with real role-based logic.
  - `async def audit_log(self, user_id, action, details)` (L455-464) - Log an audit event with a real timestamp.
  - `async def load_policies(self)` (L466-475) - Load governance policies from config.
  - `def get_audit_log(self, user_id, limit)` (L477-479) - Query the audit log.
  - `def _classify_tool(self, tool_name)` (L483-485) - Classify tool by its mutability level.
  - `def _log_audit(self, tool_name, mode, decision, user_role, reason, task_id)` (L487-509) - Log an audit event to SQLite.

## File: `guardrails.py`
Imports: asyncio, logging, re, datetime.{datetime,timezone}, typing.{Any,Dict,List,Optional,Callable,Tuple}, dataclasses.{dataclass,field}, enum.{Enum}, json
Class `RailAction` (L25-30):
Class `RailSeverity` (L33-37):
Class `RailResult` (L41-47):
  > Docs: Result of a rail check.
Class `AuditEntry` (L51-72):
  > Docs: Audit log entry.
  - `def to_dict(self)` (L62-72)
Class `InputRail` (L75-143):
  > Docs: Input validation rails - applied to user input before processing.
  - `def __init__(self, strict)` (L100-103)
  - `async def check(self, content, context)` (L105-126) - Check input content.
  - `def mask_pii(self, content)` (L128-138) - Mask PII in content.
  - `async def rate_limit_check(self, user_id, limit)` (L140-143) - Check rate limiting (placeholder).
Class `OutputRail` (L146-201):
  > Docs: Output validation rails - applied to agent output before returning.
  - `def __init__(self, strict)` (L161-163)
  - `async def check(self, content, context)` (L165-185) - Check output content.
  - `def _redact_secrets(self, content)` (L187-192) - Redact secrets from content.
  - `async def fact_check(self, content, sources)` (L194-197) - Fact-check output (placeholder for integration).
  - `async def hallucination_check(self, content, context)` (L199-201) - Check for hallucinations (placeholder).
Class `ExecutionRail` (L204-280):
  > Docs: Execution safety rails - applied to tool/command execution.
  - `def __init__(self, require_approval, allowed_tools)` (L230-233)
  - `async def check_command(self, command, context)` (L235-248) - Check if command is safe to execute.
  - `async def check_tool(self, tool_name, arguments, context)` (L250-261) - Check if tool execution is allowed.
  - `async def validate_network_request(self, url, allowlist)` (L263-280) - Validate network request against allowlist.
Class `DialogRail` (L283-317):
  > Docs: Dialog flow rails - control conversation context and topic.
  - `def __init__(self, strict)` (L290-293)
  - `async def check_relevance(self, query, context)` (L295-298) - Check if query is relevant to conversation context.
  - `async def guard_topic(self, topic, allowed_topics)` (L300-306) - Guard against off-topic discussions.
  - `async def check_context_limit(self, token_count, limit)` (L308-317) - Check if context is within limits.
Class `GuardrailsManager` (L320-447):
  > Docs: Central manager for all guardrails.
  - `def __init__(self, strict_input, strict_output, strict_execution, strict_dialog, require_approval_for, network_allowlist, audit_enabled)` (L327-347)
  - `async def check_input(self, content, context)` (L349-363) - Check and optionally transform input.
  - `async def check_output(self, content, context)` (L365-376) - Check and optionally transform output.
  - `async def check_execution(self, tool_name, command, arguments, context)` (L378-401) - Check if execution is allowed.
  - `async def check_network(self, url)` (L403-411) - Check network request.
  - `def register_approval_callback(self, approval_id, callback)` (L413-415) - Register callback for approval resolution.
  - `def _audit(self, rail_type, result, content)` (L417-434) - Add entry to audit log.
  - `def get_audit_log(self, limit)` (L436-438) - Get audit log entries.
  - `def get_status(self)` (L440-447) - Get guardrails status.
Func `def get_guardrails(strict, require_approval_for, network_allowlist)` (L454-469) - Get global guardrails manager.

## File: `instance_manager.py`
Imports: psutil, subprocess, os, typing.{Optional,Dict,Any}, project_kernel_runtime.memory.state_hub.{state_hub}
Class `InstanceManager` (L7-49):
  > Docs: Manages external application instances (Blender, Unity, Browsers) required for MCP tasks.
  - `def __init__(self)` (L11-16)
  - `def is_app_running(self, app_key)` (L18-28) - Check if a specific app is currently running on the host OS.
  - `def launch_app(self, app_key, custom_path)` (L30-49) - Autonomously launch a registered application.

## File: `mcp_bridge.py`
Imports: asyncio, json, logging, os, subprocess, sys, typing.{Any,Dict,List,Optional}
Class `MCPBridge` (L24-348):
  > Docs: Manages the lifecycle of external MCP server connections.
  - `def __init__(self)` (L35-38)
  - `async def boot_permanent_servers(self)` (L40-49) - On startup, read the registry and connect all permanent MCPs.
  - `async def connect(self, name, config)` (L51-61) - Connect to an MCP server (stdio or websocket).
  - `async def _connect_stdio(self, name, config)` (L63-120) - Spawn an MCP server as a subprocess, communicate via stdin/stdout.
  - `async def _connect_websocket(self, name, config)` (L122-162) - Connect to an MCP server via WebSocket.
  - `async def _discover_tools_stdio(self, name, process)` (L164-228) - Send JSON-RPC initialize + tools/list to discover available tools.
  - `async def call_tool(self, server_name, tool_name, arguments)` (L230-239) - Call a tool on a connected MCP server.
  - `async def _call_tool_stdio(self, process, tool_name, arguments)` (L241-262) - Execute a tool call via stdio JSON-RPC.
  - `def get_all_external_tools(self)` (L264-281) - Get all tool schemas from all connected MCP servers for LLM context injection.
  - `def get_status(self)` (L283-296) - Get the current status of all MCP connections.
  - `async def disconnect(self, name)` (L298-318) - Disconnect and clean up an MCP server.
  - `async def shutdown(self)` (L320-324) - Disconnect all servers.
  - `def _read_registry(self)` (L326-335) - Read the persistent MCP registry from disk.
  - `async def add_server(self, url)` (L337-340) - Legacy compatibility: add a server by URL.
  - `async def reprobe_server(self, url)` (L342-348) - Re-probe a server to refresh its tool list.

## File: `mcp_registry.py`
Imports: asyncio, logging, json, os, signal, subprocess, yaml, pathlib.{Path}, typing.{Any,Dict,List,Optional,Callable}, dataclasses.{dataclass,field}, datetime.{datetime,timezone}, enum.{Enum}, uuid
Class `MCPServerStatus` (L31-36):
Class `MCPServerConfig` (L40-66):
  > Docs: Configuration for an MCP server.
  - `def from_dict(cls, name, config)` (L54-66)
Class `MCPServerInstance` (L70-81):
  > Docs: Runtime instance of an MCP server.
Class `MCPRegistry` (L84-333):
  > Docs: Dynamic MCP server registry and manager.
  - `def __init__(self, config_path)` (L91-96)
  - `def load_config(self)` (L98-113) - Load MCP server configurations from runtime.yaml.
  - `async def start_server(self, name)` (L115-170) - Start an MCP server.
  - `async def stop_server(self, name)` (L172-203) - Stop an MCP server.
  - `async def restart_server(self, name)` (L205-209) - Restart an MCP server.
  - `async def start_all(self)` (L211-217) - Start all auto-start servers.
  - `async def stop_all(self)` (L219-224) - Stop all running servers.
  - `def get_server_status(self, name)` (L226-241) - Get status of a server.
  - `def list_servers(self)` (L243-248) - List all registered servers.
  - `def add_server(self, name, config)` (L250-258) - Add a new server dynamically.
  - `def remove_server(self, name)` (L260-271) - Remove a server.
  - `async def discover_tools(self, name)` (L273-281) - Discover tools offered by a server.
  - `async def call_tool(self, server_name, tool_name, arguments)` (L283-295) - Call a tool on an MCP server.
  - `async def health_check_all(self)` (L297-310) - Check health of all servers.
  - `async def start_health_monitor(self)` (L312-315) - Start background health monitoring.
  - `async def stop_health_monitor(self)` (L317-321) - Stop health monitoring.
  - `async def _health_loop(self)` (L323-333) - Background health check loop.
Func `def get_mcp_registry(config_path)` (L340-345) - Get global MCP registry.
Func `def list_mcp_servers()` (L349-350)
Func `async def start_mcp_server(name)` (L352-353)
Func `async def stop_mcp_server(name)` (L355-356)

## File: `multi_tenancy.py`
Imports: logging, typing.{Any,Dict,List,Optional}, uuid.{uuid4}
Class `Tenant` (L17-32):
  > Docs: A tenant (organization/user) in the system.
  - `def __init__(self, tenant_id, name, api_key, plan, max_agents)` (L19-26)
  - `def to_dict(self)` (L28-32)
Class `TenancyManager` (L35-83):
  > Docs: Manages multi-tenant isolation.
  - `def __init__(self)` (L38-45)
  - `def register_tenant(self, tenant_id, name, plan)` (L47-53)
  - `def get_tenant(self, tenant_id)` (L55-56)
  - `def identify_by_api_key(self, api_key)` (L58-60) - Identify tenant from API key.
  - `def set_current_tenant(self, tenant_id)` (L62-63)
  - `def get_current_tenant(self)` (L65-66)
  - `def list_tenants(self)` (L68-69)
  - `def check_resource_quota(self, tenant_id, resource)` (L71-83) - Check if tenant can use a resource.

## File: `observability.py`
Imports: json, logging, os, time, uuid, contextvars.{ContextVar}, typing.{Any,Dict,List,Optional}
Func `def configure_logging(log_level, json_output)` (L29-57) - Configure structured logging for the runtime.
Func `def get_logger(name)` (L60-66) - Get a structlog logger instance.
Class `DecisionNode` (L73-82):
  > Docs: A single step in an agent's reasoning path.
  - `def __init__(self, step_id, logic, parent_id)` (L75-82)
Class `NeuralTracer` (L85-134):
  > Docs: Traces reasoning and decision-making causality.
  - `def __init__(self, session_id)` (L88-91)
  - `def start_decision(self, logic, parent_id)` (L93-104)
  - `def end_decision(self, node_id, result_summary, metadata)` (L106-111)
  - `def get_full_trace(self)` (L113-124)
  - `def save_trace(self, path)` (L126-134)
Class `MetricsCollector` (L141-185):
  > Docs: Simple metrics collection for Prometheus-compatible export.
  - `def __init__(self)` (L144-147)
  - `def inc(self, name, value, labels)` (L149-151)
  - `def set(self, name, value, labels)` (L153-155)
  - `def observe(self, name, value, labels)` (L157-164)
  - `def export_prometheus(self)` (L166-178) - Export metrics in Prometheus text format.
  - `def _key(name, labels)` (L181-185)

## File: `orchestrator.py`
Imports: asyncio, logging, functools.{cached_property}, typing.{Dict,List,Optional,Any}, datetime.{datetime,timezone}
Class `Orchestrator` (L25-810):
  > Docs: Main coordination engine — Coordinator pattern.
  - `def __init__(self, config_path)` (L34-46)
  - `def event_bus(self)` (L53-57)
  - `def governance(self)` (L60-64)
  - `def tool_executor(self)` (L67-78)
  - `def sandbox(self)` (L81-86)
  - `def tasks(self)` (L89-93)
  - `def sessions(self)` (L96-100)
  - `def llm(self)` (L103-109)
  - `def skills(self)` (L112-116)
  - `def swarm(self)` (L119-123)
  - `def performance_core(self)` (L126-130)
  - `def analytics(self)` (L133-137)
  - `def mcp_client(self)` (L140-146)
  - `def planner(self)` (L149-153)
  - `def observability(self)` (L156-160)
  - `def watchdog(self)` (L163-167)
  - `def sre(self)` (L170-174)
  - `def mesh_p2p(self)` (L177-181)
  - `def federated(self)` (L184-188)
  - `def self_attention(self)` (L191-195)
  - `def skill_compiler(self)` (L198-202)
  - `def mcp_bridge(self)` (L205-209)
  - `def predictive(self)` (L212-216)
  - `def credits(self)` (L219-221)
  - `def tenancy(self)` (L224-226)
  - `def export_service(self)` (L229-231)
  - `def export_service(self)` (L234-236)
  - `async def initialize(self)` (L242-275) - Initialize the orchestrator — only starts what's needed.
  - `async def shutdown(self)` (L277-306) - Graceful shutdown.
  - `async def _load_feature_packs(self)` (L308-319) - Dynamically load feature packs based on config.
  - `async def execute_agentic_loop(self, task_description, user_id, session_id, max_iterations)` (L325-462) - Core agentic loop — Gather → Plan → Act → Verify.
  - `def _build_system_prompt(self)` (L464-471) - Build system prompt with project context.
  - `def _get_tool_schemas(self)` (L473-498) - Get tool schemas for LLM function calling, including external MCP tools.
  - `async def start_session(self, user_id, workspace_path, mode)` (L504-514)
  - `async def end_session(self, user_id)` (L516-520)
  - `async def create_task(self, user_id, task_type, description, steps, context)` (L526-550)
  - `async def execute_task(self, user_id, task_id)` (L552-559)
  - `async def _execute_task_async(self, user_id, task)` (L561-598) - Execute task with full pipeline integration.
  - `async def cancel_task(self, user_id, task_id)` (L600-605)
  - `async def get_task_status(self, user_id, task_id)` (L607-608)
  - `async def list_user_tasks(self, user_id, status)` (L610-618)
  - `async def call_tool(self, user_id, tool_name, arguments, session_id)` (L624-650) - Execute tool through the ToolExecutor pipeline.
  - `async def start_research_session(self, user_id, query, params)` (L656-663)
  - `async def list_research_sessions(self, user_id)` (L665-666)
  - `async def add_research_source(self, user_id, session_id, source_uri, source_type)` (L668-695)
  - `async def summarize_session(self, user_id, session_id, strategy)` (L697-718)
  - `async def get_research_progress(self, user_id, session_id)` (L720-725)
  - `async def get_research_session(self, user_id, session_id)` (L727-731)
  - `async def list_research_reports(self, user_id)` (L733-736)
  - `async def export_research_report(self, user_id, session_id, report_id, format)` (L738-749)
  - `async def get_system_status(self)` (L755-766)
  - `async def get_available_skills(self, user_id)` (L768-777)
  - `def register_mcp_tools(self, mcp_server)` (L779-800) - Register orchestrator tools with MCP server.
  - `async def trigger_gtm_campaign(self, name, niche)` (L806-810)
Func `def get_orchestrator()` (L820-824)
Func `async def init_orchestrator()` (L827-832)

## File: `parameter_registry.py`
Imports: asyncio, logging, os, yaml, json, typing.{Any,Callable,Dict,List,Optional,Set}, dataclasses.{dataclass,field}, datetime.{datetime,timezone}, uuid.{uuid4}, ui_schema.{UISchemaGenerator,UIParameter,generate_ui_schema}
Class `ParameterChange` (L34-40):
  > Docs: Record of a parameter change.
Class `ParameterValidator` (L43-78):
  > Docs: Validates parameter values.
  - `def register(cls, param_id, validator)` (L49-50)
  - `def validate(cls, param_id, value)` (L53-67)
  - `def get_validation_error(cls, param_id, value)` (L70-78) - Get validation error message if invalid.
Class `ParameterRegistry` (L81-345):
  > Docs: Centralized registry for all system parameters.
  - `def __init__(self, config_path)` (L93-108)
  - `def _register_default_validators(self)` (L110-121) - Register default parameter validators.
  - `def _load_config(self)` (L123-132) - Load configuration from YAML file.
  - `def _load_schema(self)` (L134-137) - Load parameter schema.
  - `def get(self, param_id, default)` (L139-151) - Get parameter value.
  - `def set(self, param_id, value, source)` (L153-182) - Set parameter value with validation.
  - `def _add_parameter(self, param_id, value)` (L184-197) - Add a new parameter dynamically.
  - `def _record_change(self, param_id, old_value, new_value, source)` (L199-210) - Record parameter change in history.
  - `def _notify_callbacks(self, param_id, old_value, new_value)` (L212-225) - Notify all registered callbacks.
  - `def subscribe(self, param_id, callback)` (L227-231) - Subscribe to parameter changes.
  - `def unsubscribe(self, param_id, callback)` (L233-238) - Unsubscribe from parameter changes.
  - `def subscribe_global(self, callback)` (L240-242) - Subscribe to all parameter changes.
  - `def unsubscribe_global(self, callback)` (L244-247) - Unsubscribe from all parameter changes.
  - `def get_schema(self)` (L249-256) - Get UI schema for dynamic rendering.
  - `def get_all_params(self)` (L258-260) - Get all parameters as flat dictionary.
  - `def get_change_history(self, limit)` (L262-274) - Get parameter change history.
  - `def search_params(self, query)` (L276-291) - Search parameters by label or ID.
  - `def get_by_category(self, category)` (L293-299) - Get all parameters in a category.
  - `def get_categories(self)` (L301-310) - Get all categories with parameter counts.
  - `async def save_to_config(self)` (L312-320) - Save current values back to config file.
  - `def _save_config_nolock(self)` (L322-339) - Save config without locking.
  - `def reload(self)` (L341-345) - Reload configuration from file.
Func `def get_registry(config_path)` (L351-356) - Get global parameter registry instance.
Func `def get_param(param_id, default)` (L359-361) - Convenience function to get parameter.
Func `def set_param(param_id, value, source)` (L364-366) - Convenience function to set parameter.

## File: `planner.py`
Imports: os, datetime.{datetime}, typing.{List,Dict,Any}
Class `MissionPlanner` (L10-72):
  > Docs: Handles high-level architectural planning before execution.
  - `def __init__(self, workspace_path)` (L15-17)
  - `async def generate_mission_plan(self, task_id, description, mesh_context)` (L19-31) - Analyzes the task and writes a PLAN.md to the workspace.
  - `def _build_plan_template(self, task_id, description, mesh_context)` (L33-72)

## File: `predictive.py`
Imports: logging, collections.{Counter,defaultdict}, typing.{Any,Dict,List}
Class `PredictiveEngine` (L17-69):
  > Docs: Predicts next useful actions based on task history.
  - `def __init__(self)` (L20-24)
  - `def record_action(self, tool_name, context, file_ext)` (L26-38) - Record a tool action for pattern learning.
  - `def predict_next_tool(self, current_tool, file_ext)` (L40-62) - Predict next useful tools.
  - `def get_stats(self)` (L64-69)

## File: `research.py`
Imports: pydantic.{BaseModel,Field}, typing.{List,Dict,Optional,Any}, datetime.{datetime}, asyncio, requests
Class `Source` (L8-15):
Class `ResearchReport` (L18-25):
Class `ResearchSession` (L28-38):
Func `def simple_summarize(text, max_chars)` (L42-45) - Basic text summarizer fallback.

## File: `runtime.py`
Imports: pydantic.{BaseModel,Field}, typing.{List,Dict,Optional,Literal,Any,Set}, enum.{Enum}, yaml, os, logging, pathlib.{Path}, datetime.{datetime}
Class `GovernancePolicyMode` (L30-35):
  > Docs: Permission set for a specific execution mode.
Class `GovernanceConfig` (L38-63):
  > Docs: Governance and security policy configuration.
Class `MCPConfig` (L66-80):
  > Docs: MCP (Model Context Protocol) server/client configuration.
Class `SandboxConfig` (L83-94):
  > Docs: Sandbox and execution isolation configuration.
Class `LLMProviderConfig` (L97-106):
  > Docs: Configuration for a single LLM provider.
Class `LLMConfig` (L109-139):
  > Docs: LLM provider system configuration.
Class `VectorDBConfig` (L142-151):
  > Docs: Vector database / agent memory configuration.
Class `A2AConfig` (L154-162):
  > Docs: Google A2A (Agent-to-Agent) protocol configuration.
Class `ObservabilityConfig` (L165-173):
  > Docs: Observability, logging, and monitoring configuration.
Class `SkillsConfig` (L176-188):
  > Docs: Skills registry configuration.
Class `FeaturesConfig` (L191-203):
  > Docs: Feature flags for optional subsystems.
Class `ServerConfig` (L206-214):
  > Docs: HTTP server configuration.
Class `RuntimeConfig` (L221-386):
  > Docs: Root configuration model for the Antigravity Project Kernel Runtime.
  - `def from_yaml(cls, path)` (L254-280) - Load configuration from YAML file with fallback to defaults.
  - `def from_env(cls)` (L283-316) - Load from environment variables overlaid on YAML config.
  - `def _migrate_v1_to_v2(cls, data)` (L319-345) - Migrate v1 YAML config to v2 schema.
  - `def _parse_env_value(value)` (L348-369) - Parse environment variable values into appropriate Python types.
  - `def save_yaml(self, path)` (L371-375) - Save current config to YAML file.
  - `def ensure_data_dirs(self)` (L377-386) - Create required data directories.
Class `RuntimeProfile` (L393-400):
  > Docs: Backward-compatible alias for RuntimeConfig.
Class `ConfigWatcher` (L407-444):
  > Docs: Watches runtime.yaml for changes and triggers reload callback.
  - `def __init__(self, config_path, callback)` (L416-419)
  - `async def start(self)` (L421-440) - Start watching for config changes.
  - `def stop(self)` (L442-444) - Stop watching.

## File: `rust_core.py`
Imports: asyncio, logging, time, concurrent.futures.{ProcessPoolExecutor}, typing.{Any,Callable,Dict,List,Optional}, functools.{lru_cache}
Class `PerformanceCache` (L30-110):
  > Docs: Real high-performance cache with TTL expiry and LRU eviction.
  - `def __init__(self, max_size, ttl)` (L38-45)
  - `async def store_context(self, key, data)` (L47-60) - Store data in cache with TTL.
  - `async def retrieve_context(self, key)` (L62-78) - Retrieve data from cache, return empty string if expired or missing.
  - `async def delete(self, key)` (L80-83) - Remove entry from cache.
  - `async def clear(self)` (L85-90) - Clear all entries. Returns count cleared.
  - `def _evict_oldest(self)` (L92-97) - Remove the least recently accessed entry.
  - `def stats(self)` (L100-110) - Cache statistics.
Class `ConcurrentExecutor` (L117-179):
  > Docs: Bounded concurrent task executor using asyncio.Semaphore.
  - `def __init__(self, max_workers)` (L125-132)
  - `async def execute(self, coroutine)` (L134-146) - Execute a single coroutine with bounded concurrency.
  - `async def execute_batch(self, coroutines)` (L148-151) - Execute multiple coroutines concurrently with bounded parallelism.
  - `async def run_in_process(self, func)` (L153-163) - Run a CPU-bound function in a ProcessPoolExecutor.
  - `def shutdown(self)` (L165-169) - Shutdown the process pool.
  - `def stats(self)` (L172-179) - Executor statistics.
Class `GACIEngine` (L186-223):
  > Docs: General Artificial Coding Intelligence Orchestrator.
  - `def __init__(self, max_cache_size, max_workers)` (L199-202)
  - `async def process_gaci_task(self, task_id, instructions)` (L204-211) - Process a task with context caching and bounded execution.
  - `def stats(self)` (L214-219) - Combined performance statistics.
  - `def shutdown(self)` (L221-223) - Clean shutdown.

## File: `sandbox.py`
Imports: asyncio, logging, os, platform, shlex, tempfile, dataclasses.{dataclass,field}, datetime.{datetime,timezone}, typing.{Any,Dict,List,Optional}, uuid.{uuid4}
Class `SandboxResult` (L36-43):
  > Docs: Result from sandbox execution.
Class `SandboxInstance` (L47-56):
  > Docs: Tracks an active sandbox.
Class `SubprocessSandbox` (L63-145):
  > Docs: Subprocess-based sandbox using asyncio.
  - `async def execute(self, command, working_dir, timeout, env, memory_limit_mb)` (L75-145) - Execute a command in a sandboxed subprocess.
Class `DockerSandbox` (L148-248):
  > Docs: Docker container-based sandbox for production isolation.
  - `def __init__(self, image)` (L160-162)
  - `async def is_available(self)` (L164-180) - Check if Docker is installed and running.
  - `async def execute(self, command, working_dir, timeout, env, memory_limit_mb, cpu_limit, network_mode)` (L182-248) - Execute a command inside a Docker container.
Class `E2BSandbox` (L251-289):
  > Docs: E2B (Execute to Build) cloud sandbox using Firecracker MicroVMs.
  - `async def execute(self, command, working_dir, timeout)` (L259-289) - Execute a command in an E2B cloud sandbox.
Class `ZeroTrustSandbox` (L296-464):
  > Docs: Unified sandbox manager with pluggable backends.
  - `def __init__(self, config)` (L304-328)
  - `def _create_backend(self, name)` (L330-342) - Create the sandbox backend.
  - `def provision_sandbox(self, task_id)` (L344-362) - Provision an isolated execution environment.
  - `async def execute(self, command, sandbox_id, timeout, env)` (L364-391) - Execute a command in the sandbox.
  - `async def execute_tool(self, tool, arguments, context)` (L393-399) - Execute a tool within the sandbox environment.
  - `def request_network_access(self, sandbox_id, endpoint)` (L401-420) - Check if a sandbox is allowed to access a network endpoint.
  - `def teardown_sandbox(self, sandbox_id)` (L422-433) - Remove and clean up a sandbox.
  - `def calculate_security_score(self)` (L435-464) - Calculate real-time security score based on isolation posture.

## File: `session_manager.py`
Imports: typing.{Dict,List,Optional,Any}, datetime.{datetime,timezone}, json, os, sqlite3, uuid, logging
Class `SessionContext` (L25-123):
  > Docs: User session with workspace state.
  - `def __init__(self, session_id, user_id, workspace_path, mode, context)` (L27-46)
  - `def update_activity(self)` (L48-49)
  - `def add_task(self, task_id)` (L51-54)
  - `def add_file(self, file_path)` (L56-61)
  - `def add_command(self, command)` (L63-66)
  - `def add_message(self, role, content)` (L68-77) - Add a conversation message to session memory.
  - `def get_recent_files(self, limit)` (L79-80)
  - `def get_recent_tasks(self, limit)` (L82-83)
  - `def get_conversation_context(self, last_n)` (L85-87) - Get recent conversation for LLM context building.
  - `def to_dict(self)` (L89-103)
  - `def from_dict(cls, data)` (L106-123)
Class `SessionManager` (L126-328):
  > Docs: Manages user sessions with SQLite persistence.
  - `def __init__(self, storage_path, event_bus)` (L136-145)
  - `def _init_db(self)` (L147-163) - Create SQLite tables.
  - `def create_session(self, user_id, workspace_path, mode, context)` (L165-191)
  - `def get_session(self, session_id)` (L193-194)
  - `def get_active_session(self, user_id)` (L196-200)
  - `def update_session_activity(self, session_id)` (L202-206)
  - `def add_task_to_session(self, session_id, task_id)` (L208-212)
  - `def add_file_to_session(self, session_id, file_path)` (L214-218)
  - `def add_command_to_session(self, session_id, command)` (L220-224)
  - `def add_message_to_session(self, session_id, role, content)` (L226-231) - Add conversation message for context tracking.
  - `def end_session(self, session_id)` (L233-241)
  - `def list_user_sessions(self, user_id)` (L243-244)
  - `def cleanup_old_sessions(self, days)` (L246-259)
  - `def _save_to_db(self, session)` (L263-277)
  - `def load_sessions(self)` (L279-293)
  - `def _delete_from_db(self, session_id)` (L295-300)
  - `def _migrate_from_json(self, json_dir)` (L302-321) - Migrate legacy JSON file sessions to SQLite.
  - `def save_session(self, session)` (L324-325)
  - `def delete_session_file(self, session_id)` (L327-328)

## File: `skill_compiler.py`
Imports: logging, collections.{Counter}, typing.{Any,Dict,List}
Class `LearnedSkill` (L17-30):
  > Docs: A reusable pattern extracted from task history.
  - `def __init__(self, name, tool_sequence, domain, success_count)` (L19-24)
  - `def to_dict(self)` (L26-30)
Class `SkillCompiler` (L33-80):
  > Docs: Extracts and stores reusable task patterns.
  - `def __init__(self)` (L36-39)
  - `def analyze_session(self, task_id, domain, tool_sequence)` (L41-57) - Analyze a completed task for reusable patterns.
  - `def suggest_tools(self, domain, context)` (L59-67) - Suggest tools based on learned patterns.
  - `def get_skills(self, domain)` (L69-73)
  - `def get_stats(self)` (L75-80)

## File: `skills_registry.py`
Imports: enum.{Enum}, typing.{List,Dict,Optional}
Class `SkillLevel` (L10-14):
Class `Skill` (L16-30):
  > Docs: Represents a skill with tools and permission level
  - `def __init__(self, name, description, tools, level, pack)` (L18-30)
Class `SkillRegistry` (L120-158):
  > Docs: Registry of all available skills
  - `def __init__(self)` (L123-125)
  - `def load_defaults(self)` (L127-130) - Load core 7 skills + optional packs
  - `def get_skill(self, name)` (L132-134) - Get skill by name
  - `def list_skills(self, pack)` (L136-138) - List skills in a pack
  - `def get_tools_for_skill(self, skill_name)` (L140-143) - Get MCP tool names for a skill
  - `def get_skill_by_tool(self, tool_name)` (L145-150) - Get skill that contains a specific tool
  - `def to_mcp_tools(self, pack)` (L152-158) - Convert skills to MCP tool names

## File: `swarm.py`
Imports: asyncio, logging, dataclasses.{dataclass,field}, datetime.{datetime,timezone}, enum.{Enum}, typing.{Any,Callable,Dict,List,Optional}, uuid.{uuid4}
Class `AgentRole` (L29-35):
  > Docs: Specialized agent roles within a swarm.
Class `SwarmAgent` (L39-54):
  > Docs: A specialized agent within the swarm.
  - `def to_dict(self)` (L47-54)
Class `SubTask` (L58-67):
  > Docs: A subtask assigned to a specific agent.
Class `SwarmResult` (L71-79):
  > Docs: Aggregated result from swarm execution.
Class `AgentSwarm` (L119-332):
  > Docs: Multi-agent coordination with real task decomposition and parallel execution.
  - `def __init__(self, swarm_id, llm_provider, event_bus)` (L130-137)
  - `async def delegate_task(self, task_description, context)` (L139-214) - Decompose and delegate a task to specialized agents.
  - `async def _decompose_task(self, description, context)` (L216-282) - Decompose a task into subtasks.
  - `async def _execute_subtask(self, subtask)` (L284-294) - Execute a single subtask (placeholder for real LLM-driven execution).
  - `def _find_best_agent(self, subtask)` (L296-315) - Find the best idle agent for a subtask.
  - `def get_swarm_status(self)` (L317-319) - Return status of all agents.
  - `def get_history(self)` (L321-332) - Return task execution history.

## File: `task_state_machine.py`
Imports: enum.{Enum}, typing.{Dict,List,Optional,Any}, datetime.{datetime,timezone}, json, os, sqlite3, logging
Class `TaskStatus` (L26-33):
Class `TaskType` (L36-44):
Class `TaskStep` (L47-103):
  > Docs: Individual step in a task with retry support.
  - `def __init__(self, id, description, tools, status, result, error, max_retries)` (L49-69)
  - `def to_dict(self)` (L71-84)
  - `def from_dict(cls, data)` (L87-103)
Class `Task` (L106-206):
  > Docs: Durable task with state persistence.
  - `def __init__(self, id, type, description, steps, status, context, session_id)` (L108-129)
  - `def get_current_step(self)` (L131-134)
  - `def advance_step(self)` (L136-139)
  - `def complete_step(self, result)` (L141-146)
  - `def fail_step(self, error)` (L148-163)
  - `def progress(self)` (L166-171) - Task completion percentage.
  - `def to_dict(self)` (L173-188)
  - `def from_dict(cls, data)` (L191-206)
Class `TaskStateMachine` (L209-458):
  > Docs: Manages task execution with SQLite persistence.
  - `def __init__(self, storage_path, event_bus)` (L220-228)
  - `def _init_db(self)` (L230-250) - Create SQLite tables if not exists.
  - `def create_task(self, type, description, steps, context, session_id)` (L252-267) - Create a new task with SQLite persistence.
  - `def get_task(self, task_id)` (L269-270)
  - `async def execute_task_async(self, task_id, step_executor)` (L272-322) - Execute task step-by-step with async support and timeout.
  - `def execute_task(self, task_id)` (L324-351) - Synchronous task execution (backward compatible).
  - `def pause_task(self, task_id)` (L353-357)
  - `def resume_task(self, task_id)` (L359-363)
  - `def cancel_task(self, task_id)` (L365-369)
  - `def list_tasks(self, status, session_id)` (L371-378)
  - `def _save_to_db(self, task)` (L382-399) - Persist task to SQLite.
  - `def load_tasks(self)` (L401-419) - Load all tasks from SQLite.
  - `def _migrate_from_json(self, json_dir)` (L421-437) - Migrate from legacy JSON file storage to SQLite.
  - `def save_task(self, task)` (L440-441)
  - `def execute_step(self, step)` (L443-445) - Legacy synchronous step executor (placeholder for orchestrator).
  - `async def _emit_event(self, event_type, task, step)` (L447-458) - Emit task lifecycle event.

## File: `tool_executor.py`
Imports: asyncio, logging, dataclasses.{dataclass,field}, datetime.{datetime,timezone}, typing.{Any,Dict,List,Optional}, uuid.{uuid4}, enum.{Enum}
Class `ToolMutability` (L28-33):
  > Docs: How a tool modifies the environment.
Class `ToolCall` (L37-48):
  > Docs: A request to execute a tool.
Class `ToolResult` (L52-61):
  > Docs: Result of a tool execution.
Class `PolicyDecision` (L64-68):
  > Docs: Governance decision for a tool call.
Class `ExecutionContext` (L72-80):
  > Docs: Context for tool execution.
Class `ToolExecutor` (L87-290):
  > Docs: Central pipeline for all tool execution.
  - `def __init__(self, governance, sandbox, event_bus, mcp_client)` (L98-104)
  - `def register_tool(self, tool)` (L106-109) - Register a tool implementation.
  - `def register_tools(self, tools)` (L111-114) - Register multiple tool implementations.
  - `def get_tool(self, name)` (L116-118) - Get a registered tool by name.
  - `def list_tools(self)` (L120-131) - List all registered tools with their schemas.
  - `async def execute(self, tool_call, context)` (L133-228) - Execute a tool call through the full pipeline.
  - `async def execute_batch(self, tool_calls, context)` (L230-234) - Execute multiple independent tool calls concurrently.
  - `async def _check_governance(self, tool_call, context)` (L236-261) - Check governance policy for a tool call.
  - `async def _emit_event(self, event_type, tool_call, result)` (L263-290) - Emit an event through the event bus.

## File: `ui_schema.py`
Imports: yaml, re, os, logging, typing.{Any,Dict,List,Optional,Callable}, dataclasses.{dataclass,field}, pathlib.{Path}, enum.{Enum}
Class `UIParameter` (L28-44):
  > Docs: A single tunable parameter exposed to the UI.
Class `UICategory` (L48-55):
  > Docs: A category of related parameters.
Class `UISchema` (L59-99):
  > Docs: Complete UI schema for dynamic rendering.
  - `def to_dict(self)` (L66-99)
Class `ParameterTypeInferrer` (L102-205):
  > Docs: Infers UI parameter types from Python types and values.
  - `def infer_type(cls, value, field_name)` (L165-185) - Infer UI parameter type from value.
  - `def infer_category(cls, param_id)` (L188-195) - Infer category from parameter ID.
  - `def get_label(cls, param_id)` (L198-200) - Get human-readable label for parameter.
  - `def get_metadata(cls, param_id)` (L203-205) - Get metadata (min, max, step) for parameter.
Class `UISchemaGenerator` (L208-360):
  > Docs: Generates UI schema from runtime configuration and code.
  - `def __init__(self, config_path)` (L225-228)
  - `def load_config(self)` (L230-235) - Load runtime.yaml configuration.
  - `def generate(self)` (L237-255) - Generate complete UI schema from configuration.
  - `def _parse_yaml_config(self, config, prefix)` (L257-268) - Recursively parse YAML config into parameters.
  - `def _add_parameter(self, param_id, value)` (L270-295) - Add a single parameter to the schema.
  - `def _add_hardcoded_parameters(self)` (L297-315) - Add commonly used hardcoded parameters not in config.
  - `def _build_categories(self)` (L317-339) - Build categorized parameter list.
  - `def _get_timestamp(self)` (L341-344) - Get current ISO timestamp.
  - `def get_parameter(self, param_id)` (L346-348) - Get a specific parameter.
  - `def update_parameter_value(self, param_id, value)` (L350-355) - Update a parameter's current value.
  - `def get_parameter_value(self, param_id)` (L357-360) - Get a parameter's current value.
Func `def generate_ui_schema(config_path)` (L363-366) - Convenience function to generate UI schema.

## File: `universal_tools.py`
Imports: abc.{ABC,abstractmethod}, dataclasses.{dataclass}, enum.{Enum}, pathlib.{Path}, typing.{Any,Dict}, typing.{Any,Dict,Optional}, asyncio, logging, os, platform, re, shlex
Class `ToolMutability` (L27-32):
  > Docs: How a tool modifies the environment.
Class `ToolResult` (L36-40):
  > Docs: Standard result from tool execution.
Class `BaseTool` (L43-71):
  > Docs: Abstract base class for all kernel tools.
  - `async def execute(self, arguments, context)` (L61-63) - Execute the tool with the given arguments.
  - `def to_schema(self)` (L65-71) - Export tool definition for MCP/LLM function calling.
Class `ReadFileTool` (L86-148):
  > Docs: Read the contents of a file with optional line range.
  - `async def execute(self, arguments, context)` (L102-148)
Class `WriteFileTool` (L151-195):
  > Docs: Write content to a file, creating directories as needed.
  - `async def execute(self, arguments, context)` (L167-195)
Class `EditFileTool` (L198-245):
  > Docs: Search-and-replace editing within a file.
  - `async def execute(self, arguments, context)` (L214-245)
Class `SearchFilesTool` (L248-318):
  > Docs: Search for text patterns across files using ripgrep-style matching.
  - `async def execute(self, arguments, context)` (L265-311)
  - `def _glob_match(filename, pattern)` (L314-318) - Simple glob matching for file extensions.
Class `ListDirectoryTool` (L321-387):
  > Docs: List contents of a directory.
  - `async def execute(self, arguments, context)` (L337-356)
  - `def _list_dir(self, dir_path, entries, recursive, max_depth, current_depth, base_path)` (L358-387) - Recursively list directory contents.
Func `async def _run_git(args, cwd, timeout)` (L404-425) - Run a git command and return structured output.
Func `def _resolve_cwd(arguments, context)` (L428-433) - Resolve working directory from arguments or context.
Class `GitStatusTool` (L436-458):
  > Docs: Show the working tree status.
  - `async def execute(self, arguments, context)` (L450-458)
Class `GitDiffTool` (L461-496):
  > Docs: Show changes in the working tree.
  - `async def execute(self, arguments, context)` (L478-496)
Class `GitCommitTool` (L499-543):
  > Docs: Commit staged changes with a message.
  - `async def execute(self, arguments, context)` (L520-543)
Class `GitLogTool` (L546-573):
  > Docs: Show commit history.
  - `async def execute(self, arguments, context)` (L562-573)
Class `BashExecuteTool` (L590-686):
  > Docs: Execute shell commands with timeout and output capture.
  - `async def execute(self, arguments, context)` (L608-686)
Class `WebSearchTool` (L701-766):
  > Docs: Search the web using DuckDuckGo Lite (no API key required).
  - `async def execute(self, arguments, context)` (L716-766)
Class `WebFetchTool` (L769-846):
  > Docs: Fetch content from a URL and convert to text.
  - `async def execute(self, arguments, context)` (L784-824)
  - `def _html_to_text(html)` (L827-846) - Basic HTML to text conversion.
Func `def get_all_tools()` (L850-865) - Return instances of all core tools.

## File: `wasm_driver.py`
Imports: asyncio, logging, typing.{Any,Dict}
Class `WasmDriver` (L17-82):
  > Docs: WebAssembly execution driver with subprocess fallback.
  - `def __init__(self)` (L20-23)
  - `def _check_dependencies(self)` (L25-30)
  - `async def execute_in_wasm(self, tool_name, arguments)` (L32-37) - Execute a tool in WASM sandbox (or subprocess fallback).
  - `async def _execute_wasmtime(self, tool_name, arguments)` (L39-52) - Execute via wasmtime (when available).
  - `async def _execute_subprocess_fallback(self, tool_name, arguments)` (L54-76) - Fallback: execute in isolated subprocess.
  - `def get_status(self)` (L78-82)