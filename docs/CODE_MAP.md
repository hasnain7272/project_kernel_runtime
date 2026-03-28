# Project Code Map

This document provides an exhaustive map of all source code files, including their purpose, methods, and dependencies.

## 📄 `__init__.py`

**Purpose:** Core component belonging to its respective subsystem.

---

## 📄 `agents/growth_swarm/__init__.py`

**Purpose:** Core component belonging to its respective subsystem.

**Dependencies (Imports):**
gtm_swarm_controller.gtm_swarm

---

## 📄 `agents/growth_swarm/gtm_swarm_controller.py`

**Purpose:**
```text
Antigravity Prime: GTM Swarm Controller (Month 25-26)
Architectural Pillar: Autonomous Growth & SaaS Scale-Out.
```

**Dependencies (Imports):**
asyncio, project_kernel_runtime.memory.state_hub.state_hub, typing.Any, typing.Dict, typing.List

**Classes and Methods:**

### `class GtmSwarmController`
| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, orchestrator)` | Internal logic handler. |
| `initialize` | `(self, orchestrator)` | Initializes the GTM Swarm with an orchestrator reference. |
| `start_campaign` | `(self, name, target_niche)` | Triggers a high-velocity growth campaign. |
| `_generate_viral_asset` | `(self, campaign_name, niche, lead)` | Internal logic handler. |
| `_scout_leads` | `(self, campaign_name, niche)` | Internal logic handler. |
| `_perform_outreach` | `(self, campaign_name, lead)` | Autonomous Outreach with Governance. |
| `_monitor_growth_loop` | `(self)` | Background loop to maintain growth velocity. |

---

## 📄 `agents/sre_swarm.py`

**Purpose:**
```text
SRE Swarm v2 — Self-Healing Error Monitor

Real implementation:
- Error pattern classification by type
- Auto-retry with exponential backoff
- Circuit breaker for repeated failures
- Health score tracking
```

**Dependencies (Imports):**
asyncio, collections.defaultdict, logging, time, typing.Any, typing.Dict, typing.List, typing.Optional

**Classes and Methods:**

### `class CircuitBreaker`
> Circuit breaker pattern for fault tolerance.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, failure_threshold, recovery_time)` | Internal logic handler. |
| `record_failure` | `(self)` | Internal logic handler. |
| `record_success` | `(self)` | Internal logic handler. |
| `can_execute` | `(self)` | Internal logic handler. |

### `class SREMonitor`
> Autonomous SRE self-healing monitor.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, orchestrator)` | Internal logic handler. |
| `monitor_and_heal` | `(self, task_id, error_message)` | Classify error and attempt self-healing. |
| `_classify_error` | `(self, error_message)` | Classify error by type. |
| `_heal` | `(self, error_type, task_id, error_msg)` | Attempt self-healing based on error type. |
| `get_health_score` | `(self)` | Calculate system health score (0-1). |
| `get_status` | `(self)` | Internal logic handler. |

---

## 📄 `agents/vision_swarm.py`

**Purpose:**
```text
Vision Swarm v2 — Multimodal Vision Integration

Real implementation:
- Screenshot capture via Playwright (when available)
- LLM-based image analysis (via multimodal models)
- Object detection output parsing
```

**Dependencies (Imports):**
logging, typing.Any, typing.Dict, typing.List, typing.Optional

**Classes and Methods:**

### `class VisionSwarm`
> Multimodal vision capabilities for the agent.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self)` | Internal logic handler. |
| `_check_dependencies` | `(self)` | Internal logic handler. |
| `capture_screenshot` | `(self, url, output_path)` | Capture a screenshot via Playwright. |
| `capture_and_detect` | `(self, viewport_id, description)` | Capture and analyze an image. |
| `analyze_image` | `(self, image_path, query)` | Analyze an image using multimodal LLM. |

---

## 📄 `agents/watchdog.py`

**Purpose:**
```text
Watchdog Agent v2 — Real System Monitoring

Real implementation:
- CPU, memory, disk monitoring via psutil
- Alert thresholds with configurable escalation
- Auto-restart of crashed subsystems
```

**Dependencies (Imports):**
asyncio, logging, time, typing.Any, typing.Dict, typing.List, typing.Optional

**Classes and Methods:**

### `class WatchdogAgent`
> System health watchdog with metric monitoring and auto-restart.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, analytics, orchestrator)` | Internal logic handler. |
| `start_monitoring` | `(self)` | Start periodic health monitoring. |
| `stop_monitoring` | `(self)` | Internal logic handler. |
| `collect_metrics` | `(self)` | Collect system metrics using psutil. |
| `_check_thresholds` | `(self, metrics)` | Check metrics against thresholds and create alerts. |
| `get_status` | `(self)` | Internal logic handler. |

---

## 📄 `cognition/context_cluster.py`

**Purpose:**
```text
Context-Aware Swarm Clusters (Month 15-16).
Dynamically self-organizes the federated mesh into specialized groups based on the active task.
```

**Dependencies (Imports):**
collections.defaultdict, integrations.a2a_protocol.AgentCard, typing.Any, typing.Dict, typing.List

**Classes and Methods:**

### `class ClusterState`
*No explicit methods defined.*

### `class SwarmCluster`
> A dynamic, self-organizing cluster of specialized agents.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, name, focus)` | Internal logic handler. |
| `add_member` | `(self, agent)` | Internal logic handler. |
| `to_dict` | `(self)` | Internal logic handler. |

### `class ClusterManager`
> Manages the lifecycle and distribution of agents into Context Clusters.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self)` | Internal logic handler. |
| `organize_mesh` | `(self, available_peers, active_context)` | Dynamically assign peers to clusters based on the current context. |
| `get_cluster_topology` | `(self)` | Internal logic handler. |

---

## 📄 `cognition/llm_provider.py`

**Purpose:**
```text
LLM Provider v2 — Unified LLM Interface with Streaming, Tool Calling, and Cost Tracking

Upgraded from 29-line summarize-only stub to full LLM provider system:
- Multi-provider support (Ollama, OpenAI, Anthropic) via litellm
- Real streaming with proper async generator
- Tool/function calling support
- Model routing (autocomplete → fast model, architecture → premium)
- Token usage and cost tracking
- Automatic fallback between providers
- Rate limiting

Inspired by: Aider's model selection, Cursor's model router, Claude Code's streaming arch
```

**Dependencies (Imports):**
asyncio, dataclasses.dataclass, dataclasses.field, datetime.datetime, datetime.timezone, logging, os, time, typing.Any, typing.AsyncGenerator, typing.Dict, typing.List, typing.Optional

**Classes and Methods:**

### `class LLMMessage`
> A message in the LLM conversation.

*No explicit methods defined.*

### `class LLMResponse`
> Response from an LLM call.

*No explicit methods defined.*

### `class UsageStats`
> Aggregate usage statistics.

*No explicit methods defined.*

### `class LLMProvider`
> Unified LLM provider with multi-model support, streaming, and tool calling.

Features:
- Multiple provider backends (Ollama, OpenAI, Anthropic via litellm)
- Streaming responses with proper async generators
- Tool/function calling support
- Model router (route tasks to optimal models)
- Cost and token usage tracking
- Automatic provider fallback
- Rate limiting (configurable RPM)

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, config)` | Internal logic handler. |
| `get_model_for_task` | `(self, task_type)` | Route task to optimal model via model router. |
| `complete` | `(self, messages, model, temperature, max_tokens, tools, task_type)` | Send a completion request to the LLM. |
| `stream` | `(self, messages, model, temperature, max_tokens, task_type)` | Stream a completion response token by token. |
| `_call_litellm` | `(self, messages, model, temperature, max_tokens, tools)` | Call LLM via litellm (supports Ollama, OpenAI, Anthropic, etc.). |
| `set_ollama_base_url` | `(self, host, port)` | Update the Ollama API base URL at runtime (from UI provider switch). |
| `_configure_litellm_provider` | `(self, model)` | Set litellm environment for the model's provider. |
| `_detect_provider` | `(self, model)` | Detect which provider a model belongs to. |
| `_messages_to_dicts` | `(messages)` | Convert LLMMessage objects to dict format for litellm. |
| `_track_usage` | `(self, response)` | Track token usage and cost. |
| `get_usage_stats` | `(self)` | Get aggregate usage statistics. |

**Standalone Functions:**

| Function | Arguments | Purpose |
|----------|-----------|---------|
| `_env_provider` | `()` | Internal utility function. |
| `summarize_text` | `(text, strategy, max_chars)` | Legacy provider abstraction — kept for backward compatibility. |

---

## 📄 `cognition/self_attention.py`

**Purpose:**
```text
Self-Attention Loop v2 — Reasoning Validation

Real implementation:
- Compare last N reasoning steps for contradictions
- LLM-driven consistency evaluation (when available)
- Confidence scoring based on step coherence
```

**Dependencies (Imports):**
logging, typing.Any, typing.Dict, typing.List

**Classes and Methods:**

### `class SelfAttentionLoop`
> Validates reasoning consistency across agent steps.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, orchestrator)` | Internal logic handler. |
| `reflect_on_reasoning` | `(self, task_id, recent_steps)` | Analyze recent reasoning steps for contradictions. |
| `_detect_contradictions` | `(self, texts)` | Simple rule-based contradiction detection. |
| `get_confidence_score` | `(self, task_id)` | Get latest confidence score for a task. |

---

## 📄 `fix_relative.py`

**Purpose:** Core component belonging to its respective subsystem.

**Dependencies (Imports):**
glob, os, re

---

## 📄 `integrations/__init__.py`

**Purpose:** Core component belonging to its respective subsystem.

---

## 📄 `integrations/a2a_handshake.py`

**Purpose:**
```text
A2A Handshake Manager: Automated Peer Discovery.
Implements the Google A2A handshake protocol for decentralized swarms.
```

**Dependencies (Imports):**
a2a_protocol.A2AHandler, a2a_protocol.A2AMessage, a2a_protocol.A2AMessageType, a2a_protocol.AgentCard, asyncio, json, typing.Any, typing.Dict, typing.List, typing.Optional

**Classes and Methods:**

### `class A2AHandshakeManager`
> Manages the broadcast and reception of A2A handshakes.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, handler)` | Internal logic handler. |
| `start_broadcasting` | `(self)` | Periodically broadcast the agent card to the local network. |
| `_simulate_network_broadcast` | `(self, message_json)` | Simulates sending a message to the local A2A mesh. |
| `stop` | `(self)` | Internal logic handler. |
| `handle_peer_response` | `(self, response_json)` | Process a response from a peer found via handshake. |

---

## 📄 `integrations/a2a_protocol.py`

**Purpose:**
```text
Google A2A Protocol v0.3 — Full Spec Compliance

Upgraded from 91-line basic handler to full A2A v0.3:
- Agent Card with skills, capabilities, authentication
- Task lifecycle FSM (Submitted→Working→InputRequired→Completed→Failed→Cancelled)
- JSON-RPC transport + SSE streaming
- Message/Part/Artifact model for typed data exchange
- /.well-known/agent.json discovery endpoint
- Push notification webhook support

Ref: Google A2A v0.3 — https://google.github.io/A2A
```

**Dependencies (Imports):**
datetime.datetime, datetime.timezone, enum.Enum, json, logging, typing.Any, typing.Dict, typing.List, typing.Optional, uuid.uuid4

**Classes and Methods:**

### `class A2ATaskState`
> A2A v0.3 task lifecycle states.

*No explicit methods defined.*

### `class AgentSkill`
> Capability advertised by an agent.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, id, name, description, tags, examples)` | Internal logic handler. |
| `to_dict` | `(self)` | Internal logic handler. |

### `class AgentCapabilities`
> What the agent supports.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, streaming, push_notifications, state_transition_history)` | Internal logic handler. |
| `to_dict` | `(self)` | Internal logic handler. |

### `class AgentCard`
> A2A v0.3 Agent Card — identity and capability descriptor.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, id, name, description, url, version, capabilities, skills, default_input_modes, default_output_modes)` | Internal logic handler. |
| `to_dict` | `(self)` | Internal logic handler. |

### `class A2APart`
> Content part in an A2A message.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, type, text, mime_type, data, metadata)` | Internal logic handler. |
| `to_dict` | `(self)` | Internal logic handler. |

### `class A2AMessage`
> A2A v0.3 message with typed parts.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, role, parts, metadata)` | Internal logic handler. |
| `to_dict` | `(self)` | Internal logic handler. |

### `class A2AArtifact`
> An artifact produced by a task.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, id, name, parts, metadata)` | Internal logic handler. |
| `to_dict` | `(self)` | Internal logic handler. |

### `class A2ATask`
> A2A v0.3 task with full lifecycle.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, id, session_id)` | Internal logic handler. |
| `transition` | `(self, new_state)` | Transition task state with history tracking. |
| `to_dict` | `(self)` | Internal logic handler. |

### `class A2AHandler`
> Google A2A v0.3 protocol handler.

Supports:
- Agent Card discovery (.well-known/agent.json)
- Task lifecycle (send, get, cancel)
- Message streaming via SSE
- Peer registry

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, owner_card)` | Internal logic handler. |
| `get_agent_card` | `(self)` | Return agent card for /.well-known/agent.json. |
| `handle_jsonrpc` | `(self, method, params)` | Route A2A JSON-RPC methods. |
| `_handle_task_send` | `(self, params)` | Create or update a task (tasks/send). |
| `_handle_task_get` | `(self, params)` | Get task status (tasks/get). |
| `_handle_task_cancel` | `(self, params)` | Cancel a task (tasks/cancel). |
| `_handle_task_send_subscribe` | `(self, params)` | Send task and subscribe to updates (tasks/sendSubscribe). |
| `register_peer` | `(self, card)` | Internal logic handler. |
| `handle_incoming` | `(self, raw_message)` | Legacy incoming message handler (backward compat). |
| `list_peers` | `(self)` | Internal logic handler. |
| `create_handshake` | `(self)` | Generate handshake message. |

### `class GA2AMeshV2`
> Merged from a2a_protocol_v2 — mesh networking for A2A.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, owner_card)` | Internal logic handler. |
| `broadcast_presence` | `(self)` | Internal logic handler. |
| `handle_message` | `(self, raw)` | Internal logic handler. |

---

## 📄 `integrations/a2a_protocol_v2.py`

**Purpose:**
```text
G-A2A Protocol V2 — Bridge Module (redirects to a2a_protocol.py)

This module preserves backward compatibility by re-exporting from
the unified a2a_protocol.py which now includes the GA2AMeshV2 class.
```

**Dependencies (Imports):**
a2a_protocol.A2AArtifact, a2a_protocol.A2AHandler, a2a_protocol.A2AMessage, a2a_protocol.A2APart, a2a_protocol.A2ATask, a2a_protocol.A2ATaskState, a2a_protocol.AgentCard, a2a_protocol.GA2AMeshV2

---

## 📄 `integrations/browser_mcp.py`

**Purpose:**
```text
Antigravity Prime: Chrome MCO Hub (Browser MCP)
A first-class hub for web orchestration and browser-native missions.
```

**Dependencies (Imports):**
asyncio, httpx, mcp.server.fastmcp.FastMCP, typing.Any, typing.Dict

**Standalone Functions:**

| Function | Arguments | Purpose |
|----------|-----------|---------|
| `browser_navigate` | `(url)` | Navigates the sovereign browser instance to a specific URL. |
| `browser_extract` | `(selector)` | Extracts data from the current page using a CSS selector. |
| `browser_dispatch` | `(directive)` | Dispatches a complex web-mission (e.g., 'Search for 3D benchmarks'). |
| `browser_screenshot` | `()` | Captures a high-resolution buffer of the current browser viewport. |

---

## 📄 `integrations/universal_mcp.py`

**Purpose:** Core component belonging to its respective subsystem.

**Dependencies (Imports):**
asyncio, httpx, os, project_kernel_runtime.memory.state_hub.state_hub, typing.Any, typing.Dict, typing.List, typing.Optional, yaml

**Classes and Methods:**

### `class UniversalMCP`
| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, registry_path)` | Internal logic handler. |
| `_load_registry` | `(self)` | Load discovered MCPs from persistent storage. |
| `_save_registry` | `(self)` | Save discovered MCPs to persistent storage. |
| `_rebuild_tool_map` | `(self)` | Rebuild tool_map from discovered_servers. |
| `add_server` | `(self, url)` | Adds and probes a new MCP server via SSE. |
| `initiate_mcp_discovery` | `(self)` | Background task to discover local and configured MCP servers. |
| `execute_mcp_tool` | `(self, tool_name, arguments)` | Routes execution to the target MCP server via SSE. |
| `reprobe_server` | `(self, url)` | Manually re-probe an existing server to update status and tools. |
| `check_health` | `(self)` | Background health check for all registered servers. |

---

## 📄 `kernel/__init__.py`

**Purpose:** Core component belonging to its respective subsystem.

**Dependencies (Imports):**
event_bus.AgentEvent, event_bus.EventBus, event_bus.EventTypes, governance.ExecutionMode, governance.GovernanceEngine, governance.PolicyDecision, governance.UserRole, observability.MetricsCollector, observability.NeuralTracer, observability.configure_logging, observability.metrics, orchestrator.Orchestrator, orchestrator.get_orchestrator, orchestrator.init_orchestrator, project_kernel_runtime.cognition.llm_provider.LLMMessage, project_kernel_runtime.cognition.llm_provider.LLMProvider, project_kernel_runtime.cognition.llm_provider.LLMResponse, project_kernel_runtime.protocols.mcp_server.MCPResource, project_kernel_runtime.protocols.mcp_server.MCPServer, project_kernel_runtime.protocols.mcp_server.MCPSession, project_kernel_runtime.protocols.mcp_server.MCPTool, runtime.ConfigWatcher, runtime.RuntimeConfig, runtime.RuntimeProfile, rust_core.ConcurrentExecutor, rust_core.GACIEngine, rust_core.PerformanceCache, sandbox.SandboxResult, sandbox.ZeroTrustSandbox, session_manager.SessionContext, session_manager.SessionManager, swarm.AgentSwarm, swarm.SwarmAgent, task_state_machine.Task, task_state_machine.TaskStateMachine, task_state_machine.TaskStatus, task_state_machine.TaskStep, task_state_machine.TaskType, tool_executor.ExecutionContext, tool_executor.ToolCall, tool_executor.ToolExecutor, tool_executor.ToolResult

---

## 📄 `kernel/analytics.py`

**Purpose:**
```text
Analytics Service: Performance tracking and bottleneck identification.
Part of Phase 9-10 (Enterprise Features).
```

**Dependencies (Imports):**
dataclasses.dataclass, dataclasses.field, datetime.datetime, time, typing.Any, typing.Dict, typing.List, typing.Optional

**Classes and Methods:**

### `class TaskMetric`
*No explicit methods defined.*

### `class AnalyticsService`
> Tracks and analyzes system performance metrics.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self)` | Internal logic handler. |
| `start_task_tracking` | `(self, task_id)` | Initialize tracking for a new task. |
| `record_step_timing` | `(self, task_id, step_id, duration)` | Record how long a specific step took. |
| `end_task_tracking` | `(self, task_id, success)` | Finalize tracking for a task. |
| `get_bottlenecks` | `(self)` | Identify slow steps across all tasks. |
| `get_task_metrics` | `(self)` | Retrieve metrics for all tasks currently being tracked. |
| `get_system_summary` | `(self)` | Overall system efficiency summary. |

---

## 📄 `kernel/credits_engine.py`

**Purpose:**
```text
Credits Engine v2 — SQLite-backed Usage Metering

Real usage tracking:
- Per-tenant token & tool metering
- SQLite persistence
- Quota enforcement
- Usage reports
```

**Dependencies (Imports):**
logging, os, sqlite3, time, typing.Any, typing.Dict, typing.Optional

**Classes and Methods:**

### `class CreditsEngine`
> Per-tenant usage metering and billing.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, db_path)` | Internal logic handler. |
| `_init_db` | `(self)` | Internal logic handler. |
| `record_usage` | `(self, tenant_id, usage_type, quantity)` | Record a usage event. |
| `get_usage` | `(self, tenant_id, since)` | Get usage totals for a tenant. |
| `check_quota` | `(self, tenant_id, usage_type)` | Check if tenant is within quota. |
| `set_quota` | `(self, tenant_id, max_tool_calls, max_tokens, max_compute_sec)` | Internal logic handler. |
| `get_report` | `(self, tenant_id)` | Internal logic handler. |

---

## 📄 `kernel/evaluation.py`

**Purpose:**
```text
Evaluation Harness: Performance benchmarking for the kernel.
Inspired by EvoClaw, SWE-bench, and OpenHands Evaluation.
```

**Dependencies (Imports):**
datetime.datetime, json, time, typing.Any, typing.Dict, typing.List, typing.Optional

**Classes and Methods:**

### `class BenchmarkProfile`
> A set of tasks to evaluate an agent's success rate.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, name, tasks)` | Internal logic handler. |

### `class EvaluationHarness`
> Benchmarks the kernel's agentic performance.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, orchestrator)` | Internal logic handler. |
| `run_benchmark` | `(self, profile)` | Run all tasks in the profile and record success metrics. |
| `get_report` | `(self)` | Calculate summary statistics for the benchmark. |
| `save_to_file` | `(self, path)` | Persist results for historical comparison. |

---

## 📄 `kernel/event_bus.py`

**Purpose:**
```text
Event Bus — Central Event Publish/Subscribe System

Provides decoupled communication between all kernel subsystems.
All agent actions, tool executions, task state changes, and governance
decisions are published as typed events through the bus.

Inspired by: OpenHands EventStream, Cursor's flow-based architecture
```

**Dependencies (Imports):**
asyncio, collections.defaultdict, dataclasses.dataclass, dataclasses.field, datetime.datetime, datetime.timezone, logging, typing.Any, typing.Callable, typing.Coroutine, typing.Dict, typing.List, typing.Optional, uuid.uuid4

**Classes and Methods:**

### `class AgentEvent`
> Base event published through the event bus.

*No explicit methods defined.*

### `class EventTypes`
> Known event types in the kernel.

*No explicit methods defined.*

### `class EventBus`
> Asynchronous event bus for decoupled inter-subsystem communication.

Features:
- Typed event publish/subscribe
- Wildcard subscriptions (e.g., "task.*" matches all task events)
- Event replay from log for crash recovery
- Async handlers with error isolation
- Event log for auditing and debugging

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, max_log_size)` | Internal logic handler. |
| `subscribe` | `(self, event_type, handler)` | Subscribe a handler to an event type. |
| `unsubscribe` | `(self, event_type, handler)` | Remove a handler from an event type. |
| `publish` | `(self, event)` | Publish an event to all matching subscribers. |
| `publish_and_wait` | `(self, event)` | Publish and wait for all handlers to complete. |
| `emit` | `(self, event_type, payload, source, session_id, task_id)` | Convenience method to create and return an event (does not publish). |
| `emit_and_publish` | `(self, event_type, payload, source, session_id, task_id)` | Create, publish, and return an event in one call. |
| `replay` | `(self, from_event_id, event_type, limit)` | Replay events from the log for crash recovery or debugging. |
| `get_event_log` | `(self, last_n)` | Get the last N events from the log. |
| `subscriber_count` | `(self)` | Total number of active subscriptions. |
| `_matches` | `(pattern, event_type)` | Check if event type matches a subscription pattern. |
| `_safe_call` | `(handler, event)` | Call a handler with error isolation. |

---

## 📄 `kernel/export_service.py`

**Purpose:**
```text
Export Service for Research Reports.
```

**Dependencies (Imports):**
datetime.datetime, json, os, research.ResearchReport, research.ResearchSession, typing.Any, typing.Dict, typing.List

**Classes and Methods:**

### `class ExportService`
> Service to export research reports into MD, JSON, or PDF.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `to_markdown` | `(report, session)` | Convert a report to a Markdown string. |
| `to_json` | `(report)` | Convert a report to a JSON string. |
| `to_pdf` | `(report, session, output_path)` | Export to PDF. |

---

## 📄 `kernel/governance.py`

**Purpose:**
```text
Governance Engine v2 — Real RBAC, Tool Permissions, and Audit Logging

Upgraded from stub to production:
- Role-Based Access Control (RBAC) with real enforcement
- Tool-level permission matrix (not blanket returns)
- SQLite-backed audit trail with real timestamps
- Approval workflows for destructive operations
- Network allowlist enforcement
- .agentrules file loading (Cursor .cursorrules equivalent)

Inspired by: Cursor governance & editing rules, Claude Code sandbox boundaries,
OpenHands governance controls, NemoClaw policy engine
```

**Dependencies (Imports):**
asyncio, datetime.datetime, datetime.timezone, enum.Enum, json, logging, os, sqlite3, typing.Dict, typing.List, typing.Optional, typing.Set, uuid.uuid4

**Classes and Methods:**

### `class ExecutionMode`
*No explicit methods defined.*

### `class PolicyDecision`
*No explicit methods defined.*

### `class UserRole`
*No explicit methods defined.*

### `class AuditStore`
> SQLite-backed persistent audit trail.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, db_path)` | Internal logic handler. |
| `_init_db` | `(self)` | Create audit table if not exists. |
| `log` | `(self, event)` | Append an audit event to the persistent log. |
| `query` | `(self, user_id, limit, since)` | Query audit log entries. |

### `class GovernanceEngine`
> Production governance engine with real enforcement.

Features:
- RBAC with tool-level permission matrix
- Mode-based policy enforcement (plan/review/research/build)
- SQLite-backed audit trail with real timestamps
- Approval workflows for destructive operations
- Network allowlist enforcement
- .agentrules file support

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, policy_matrix, config)` | Internal logic handler. |
| `check_tool_allowed` | `(self, tool_name, mode, task_id, user_role)` | Check if a tool is allowed in the given mode and role. |
| `check_permission` | `(self, tool_name, user_role, execution_mode, mutability)` | Unified permission check (used by ToolExecutor). |
| `requires_approval` | `(self, tool_name)` | Check if a tool requires human approval before execution. |
| `request_approval` | `(self, tool_call_id, tool_name, arguments, user_id)` | Queue a tool call for human approval. |
| `resolve_approval` | `(self, approval_id, approved, reviewer_id)` | Resolve a pending approval request. |
| `check_network_access` | `(self, url, allowlist)` | Check if a URL is allowed by the network policy. |
| `load_project_rules` | `(self, workspace_path)` | Load .agentrules file from workspace (Cursor's .cursorrules equivalent). |
| `project_rules` | `(self)` | Get loaded project rules. |
| `check_skill_permission` | `(self, user_id, skill_name, level)` | Check skill permission with real role-based logic. |
| `audit_log` | `(self, user_id, action, details)` | Log an audit event with a real timestamp. |
| `load_policies` | `(self)` | Load governance policies from config. |
| `get_audit_log` | `(self, user_id, limit)` | Query the audit log. |
| `_classify_tool` | `(self, tool_name)` | Classify tool by its mutability level. |
| `_log_audit` | `(self, tool_name, mode, decision, user_role, reason, task_id)` | Log an audit event to SQLite. |

---

## 📄 `kernel/instance_manager.py`

**Purpose:** Core component belonging to its respective subsystem.

**Dependencies (Imports):**
os, project_kernel_runtime.memory.state_hub.state_hub, psutil, subprocess, typing.Any, typing.Dict, typing.Optional

**Classes and Methods:**

### `class InstanceManager`
> Manages external application instances (Blender, Unity, Browsers) required for MCP tasks.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self)` | Internal logic handler. |
| `is_app_running` | `(self, app_key)` | Check if a specific app is currently running on the host OS. |
| `launch_app` | `(self, app_key, custom_path)` | Autonomously launch a registered application. |

---

## 📄 `kernel/mcp_bridge.py`

**Purpose:**
```text
MCP Bridge — Dynamic MCP Server Lifecycle Manager

Spawns stdio subprocess-based MCP servers and manages websocket MCP clients.
On boot, reads data/mcp_registry.json to auto-connect permanent MCPs.
Exposes discovered tools to the Orchestrator's LLM context.

Inspired by: OpenHands MCP integration, Claude Code tool discovery
```

**Dependencies (Imports):**
asyncio, json, logging, os, subprocess, sys, typing.Any, typing.Dict, typing.List, typing.Optional

**Classes and Methods:**

### `class MCPBridge`
> Manages the lifecycle of external MCP server connections.

Supports two transport types:
- stdio: Spawns a subprocess and communicates via stdin/stdout JSON-RPC
- websocket: Connects to a remote MCP server via WebSocket

All discovered tools are exposed to the Orchestrator for LLM tool-calling.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self)` | Internal logic handler. |
| `boot_permanent_servers` | `(self)` | On startup, read the registry and connect all permanent MCPs. |
| `connect` | `(self, name, config)` | Connect to an MCP server (stdio or websocket). |
| `_connect_stdio` | `(self, name, config)` | Spawn an MCP server as a subprocess, communicate via stdin/stdout. |
| `_connect_websocket` | `(self, name, config)` | Connect to an MCP server via WebSocket. |
| `_discover_tools_stdio` | `(self, name, process)` | Send JSON-RPC initialize + tools/list to discover available tools. |
| `call_tool` | `(self, server_name, tool_name, arguments)` | Call a tool on a connected MCP server. |
| `_call_tool_stdio` | `(self, process, tool_name, arguments)` | Execute a tool call via stdio JSON-RPC. |
| `get_all_external_tools` | `(self)` | Get all tool schemas from all connected MCP servers for LLM context injection. |
| `get_status` | `(self)` | Get the current status of all MCP connections. |
| `disconnect` | `(self, name)` | Disconnect and clean up an MCP server. |
| `shutdown` | `(self)` | Disconnect all servers. |
| `_read_registry` | `(self)` | Read the persistent MCP registry from disk. |
| `add_server` | `(self, url)` | Legacy compatibility: add a server by URL. |
| `reprobe_server` | `(self, url)` | Re-probe a server to refresh its tool list. |

---

## 📄 `kernel/multi_tenancy.py`

**Purpose:**
```text
Multi-Tenancy v2 — Real Tenant Isolation

Real multi-tenant support:
- Per-tenant task queues, session stores, credit balances
- Tenant identification from API key
- Resource quotas per tenant
```

**Dependencies (Imports):**
logging, typing.Any, typing.Dict, typing.List, typing.Optional, uuid.uuid4

**Classes and Methods:**

### `class Tenant`
> A tenant (organization/user) in the system.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, tenant_id, name, api_key, plan, max_agents)` | Internal logic handler. |
| `to_dict` | `(self)` | Internal logic handler. |

### `class TenancyManager`
> Manages multi-tenant isolation.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self)` | Internal logic handler. |
| `register_tenant` | `(self, tenant_id, name, plan)` | Internal logic handler. |
| `get_tenant` | `(self, tenant_id)` | Internal logic handler. |
| `identify_by_api_key` | `(self, api_key)` | Identify tenant from API key. |
| `set_current_tenant` | `(self, tenant_id)` | Internal logic handler. |
| `get_current_tenant` | `(self)` | Internal logic handler. |
| `list_tenants` | `(self)` | Internal logic handler. |
| `check_resource_quota` | `(self, tenant_id, resource)` | Check if tenant can use a resource. |

---

## 📄 `kernel/observability.py`

**Purpose:**
```text
Observability v2 — Structured Logging + Decision Tracing

Upgraded from 80-line tracer to full observability stack:
- structlog configuration (json + console output)
- Decision tree tracing (preserved from v1)
- Prometheus-compatible metrics export
- Request ID tracking via context vars
```

**Dependencies (Imports):**
contextvars.ContextVar, json, logging, os, time, typing.Any, typing.Dict, typing.List, typing.Optional, uuid

**Classes and Methods:**

### `class DecisionNode`
> A single step in an agent's reasoning path.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, step_id, logic, parent_id)` | Internal logic handler. |

### `class NeuralTracer`
> Traces reasoning and decision-making causality.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, session_id)` | Internal logic handler. |
| `start_decision` | `(self, logic, parent_id)` | Internal logic handler. |
| `end_decision` | `(self, node_id, result_summary, metadata)` | Internal logic handler. |
| `get_full_trace` | `(self)` | Internal logic handler. |
| `save_trace` | `(self, path)` | Internal logic handler. |

### `class MetricsCollector`
> Simple metrics collection for Prometheus-compatible export.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self)` | Internal logic handler. |
| `inc` | `(self, name, value, labels)` | Internal logic handler. |
| `set` | `(self, name, value, labels)` | Internal logic handler. |
| `observe` | `(self, name, value, labels)` | Internal logic handler. |
| `export_prometheus` | `(self)` | Export metrics in Prometheus text format. |
| `_key` | `(name, labels)` | Internal logic handler. |

**Standalone Functions:**

| Function | Arguments | Purpose |
|----------|-----------|---------|
| `configure_logging` | `(log_level, json_output)` | Configure structured logging for the runtime. |
| `get_logger` | `(name)` | Get a structlog logger instance. |

---

## 📄 `kernel/orchestrator.py`

**Purpose:**
```text
Orchestrator v2 — Coordinator Pattern with Agentic Loop

Refactored from 665-line God Object to Coordinator pattern:
- Lazy initialization via @cached_property (subsystems init on first use)
- Event bus architecture (all subsystems publish/subscribe to EventBus)
- Agentic loop (Gather → Plan → Act → Verify)
- Plugin-based feature pack loading
- All tool execution via ToolExecutor pipeline
- Research orchestration extracted to dedicated methods

Inspired by: OpenHands event-driven runtime, Cursor subagent orchestration,
Claude Code agentic loop, Aider architect/editor dual model
```

**Dependencies (Imports):**
asyncio, datetime.datetime, datetime.timezone, functools.cached_property, logging, typing.Any, typing.Dict, typing.List, typing.Optional

**Classes and Methods:**

### `class Orchestrator`
> Main coordination engine — Coordinator pattern.

Subsystems are lazily initialized via @cached_property.
All communication goes through EventBus.
All tool execution goes through ToolExecutor pipeline.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, config_path)` | Internal logic handler. |
| `event_bus` | `(self)` | Internal logic handler. |
| `governance` | `(self)` | Internal logic handler. |
| `tool_executor` | `(self)` | Internal logic handler. |
| `sandbox` | `(self)` | Internal logic handler. |
| `tasks` | `(self)` | Internal logic handler. |
| `sessions` | `(self)` | Internal logic handler. |
| `llm` | `(self)` | Internal logic handler. |
| `skills` | `(self)` | Internal logic handler. |
| `swarm` | `(self)` | Internal logic handler. |
| `performance_core` | `(self)` | Internal logic handler. |
| `analytics` | `(self)` | Internal logic handler. |
| `mcp_client` | `(self)` | Internal logic handler. |
| `planner` | `(self)` | Internal logic handler. |
| `observability` | `(self)` | Internal logic handler. |
| `watchdog` | `(self)` | Internal logic handler. |
| `sre` | `(self)` | Internal logic handler. |
| `mesh_p2p` | `(self)` | Internal logic handler. |
| `federated` | `(self)` | Internal logic handler. |
| `self_attention` | `(self)` | Internal logic handler. |
| `skill_compiler` | `(self)` | Internal logic handler. |
| `mcp_bridge` | `(self)` | Internal logic handler. |
| `predictive` | `(self)` | Internal logic handler. |
| `credits` | `(self)` | Internal logic handler. |
| `tenancy` | `(self)` | Internal logic handler. |
| `export_service` | `(self)` | Internal logic handler. |
| `export_service` | `(self)` | Internal logic handler. |
| `initialize` | `(self)` | Initialize the orchestrator — only starts what's needed. |
| `shutdown` | `(self)` | Graceful shutdown. |
| `_load_feature_packs` | `(self)` | Dynamically load feature packs based on config. |
| `execute_agentic_loop` | `(self, task_description, user_id, session_id, max_iterations)` | Core agentic loop — Gather → Plan → Act → Verify. |
| `_build_system_prompt` | `(self)` | Build system prompt with project context. |
| `_get_tool_schemas` | `(self)` | Get tool schemas for LLM function calling, including external MCP tools. |
| `start_session` | `(self, user_id, workspace_path, mode)` | Internal logic handler. |
| `end_session` | `(self, user_id)` | Internal logic handler. |
| `create_task` | `(self, user_id, task_type, description, steps, context)` | Internal logic handler. |
| `execute_task` | `(self, user_id, task_id)` | Internal logic handler. |
| `_execute_task_async` | `(self, user_id, task)` | Execute task with full pipeline integration. |
| `cancel_task` | `(self, user_id, task_id)` | Internal logic handler. |
| `get_task_status` | `(self, user_id, task_id)` | Internal logic handler. |
| `list_user_tasks` | `(self, user_id, status)` | Internal logic handler. |
| `call_tool` | `(self, user_id, tool_name, arguments, session_id)` | Execute tool through the ToolExecutor pipeline. |
| `start_research_session` | `(self, user_id, query, params)` | Internal logic handler. |
| `list_research_sessions` | `(self, user_id)` | Internal logic handler. |
| `add_research_source` | `(self, user_id, session_id, source_uri, source_type)` | Internal logic handler. |
| `summarize_session` | `(self, user_id, session_id, strategy)` | Internal logic handler. |
| `get_research_progress` | `(self, user_id, session_id)` | Internal logic handler. |
| `get_research_session` | `(self, user_id, session_id)` | Internal logic handler. |
| `list_research_reports` | `(self, user_id)` | Internal logic handler. |
| `export_research_report` | `(self, user_id, session_id, report_id, format)` | Internal logic handler. |
| `get_system_status` | `(self)` | Internal logic handler. |
| `get_available_skills` | `(self, user_id)` | Internal logic handler. |
| `register_mcp_tools` | `(self, mcp_server)` | Register orchestrator tools with MCP server. |
| `trigger_gtm_campaign` | `(self, name, niche)` | Internal logic handler. |

**Standalone Functions:**

| Function | Arguments | Purpose |
|----------|-----------|---------|
| `get_orchestrator` | `()` | Internal utility function. |
| `init_orchestrator` | `()` | Internal utility function. |

---

## 📄 `kernel/planner.py`

**Purpose:**
```text
Antigravity Prime: Mission Planner (Month 19-20 Feature)
Generates structured PLAN.md files for deterministic multi-agent execution.
```

**Dependencies (Imports):**
datetime.datetime, os, typing.Any, typing.Dict, typing.List

**Classes and Methods:**

### `class MissionPlanner`
> Handles high-level architectural planning before execution.
Inspired by OpenHands PLAN.md and Cursor's reasoning loop.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, workspace_path)` | Internal logic handler. |
| `generate_mission_plan` | `(self, task_id, description, mesh_context)` | Analyzes the task and writes a PLAN.md to the workspace. |
| `_build_plan_template` | `(self, task_id, description, mesh_context)` | Internal logic handler. |

---

## 📄 `kernel/predictive.py`

**Purpose:**
```text
Predictive Engine v2 — Task & Tool Prediction

Real implementation:
- Use task history + context to predict next useful actions
- Suggest tools based on file context
- Frequency-based ranking
```

**Dependencies (Imports):**
collections.Counter, collections.defaultdict, logging, typing.Any, typing.Dict, typing.List

**Classes and Methods:**

### `class PredictiveEngine`
> Predicts next useful actions based on task history.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self)` | Internal logic handler. |
| `record_action` | `(self, tool_name, context, file_ext)` | Record a tool action for pattern learning. |
| `predict_next_tool` | `(self, current_tool, file_ext)` | Predict next useful tools. |
| `get_stats` | `(self)` | Internal logic handler. |

---

## 📄 `kernel/research.py`

**Purpose:** Core component belonging to its respective subsystem.

**Dependencies (Imports):**
asyncio, datetime.datetime, pydantic.BaseModel, pydantic.Field, requests, typing.Any, typing.Dict, typing.List, typing.Optional

**Classes and Methods:**

### `class Source`
*No explicit methods defined.*

### `class ResearchReport`
*No explicit methods defined.*

### `class ResearchSession`
*No explicit methods defined.*

**Standalone Functions:**

| Function | Arguments | Purpose |
|----------|-----------|---------|
| `simple_summarize` | `(text, max_chars)` | Basic text summarizer fallback. |

---

## 📄 `kernel/runtime.py`

**Purpose:**
```text
Project Kernel Runtime Configuration v2.0

Production-grade configuration system with:
- Pydantic v2 nested models for type-safe, validated config
- Environment variable overlay (YAML → env vars → CLI args)
- Hot-reload support via file watching
- Multi-environment profiles (development, staging, production)
- Schema version migration

Inspired by: Cursor's layered config, Claude Code's CLAUDE.md, OpenHands RuntimeProfile
```

**Dependencies (Imports):**
datetime.datetime, enum.Enum, logging, os, pathlib.Path, pydantic.BaseModel, pydantic.Field, typing.Any, typing.Dict, typing.List, typing.Literal, typing.Optional, typing.Set, yaml

**Classes and Methods:**

### `class GovernancePolicyMode`
> Permission set for a specific execution mode.

*No explicit methods defined.*

### `class GovernanceConfig`
> Governance and security policy configuration.

*No explicit methods defined.*

### `class MCPConfig`
> MCP (Model Context Protocol) server/client configuration.

*No explicit methods defined.*

### `class SandboxConfig`
> Sandbox and execution isolation configuration.

*No explicit methods defined.*

### `class LLMProviderConfig`
> Configuration for a single LLM provider.

*No explicit methods defined.*

### `class LLMConfig`
> LLM provider system configuration.

*No explicit methods defined.*

### `class VectorDBConfig`
> Vector database / agent memory configuration.

*No explicit methods defined.*

### `class A2AConfig`
> Google A2A (Agent-to-Agent) protocol configuration.

*No explicit methods defined.*

### `class ObservabilityConfig`
> Observability, logging, and monitoring configuration.

*No explicit methods defined.*

### `class SkillsConfig`
> Skills registry configuration.

*No explicit methods defined.*

### `class FeaturesConfig`
> Feature flags for optional subsystems.

*No explicit methods defined.*

### `class ServerConfig`
> HTTP server configuration.

*No explicit methods defined.*

### `class RuntimeConfig`
> Root configuration model for the Antigravity Project Kernel Runtime.

Supports layered loading: YAML file → environment variables → CLI args.
All subsections are validated Pydantic models with sensible defaults.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `from_yaml` | `(cls, path)` | Load configuration from YAML file with fallback to defaults. |
| `from_env` | `(cls)` | Load from environment variables overlaid on YAML config. |
| `_migrate_v1_to_v2` | `(cls, data)` | Migrate v1 YAML config to v2 schema. |
| `_parse_env_value` | `(value)` | Parse environment variable values into appropriate Python types. |
| `save_yaml` | `(self, path)` | Save current config to YAML file. |
| `ensure_data_dirs` | `(self)` | Create required data directories. |

### `class RuntimeProfile`
> Backward-compatible alias for RuntimeConfig.

Existing code that imports RuntimeProfile will continue to work.
New code should use RuntimeConfig directly.

*No explicit methods defined.*

### `class ConfigWatcher`
> Watches runtime.yaml for changes and triggers reload callback.

Usage:
    watcher = ConfigWatcher("runtime.yaml", on_config_change)
    await watcher.start()

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, config_path, callback)` | Internal logic handler. |
| `start` | `(self)` | Start watching for config changes. |
| `stop` | `(self)` | Stop watching. |

---

## 📄 `kernel/rust_core.py`

**Purpose:**
```text
Performance Core — High-Performance Python Execution Substrate

Renamed from rust_core.py — honest about what this is: optimized Python
with real caching, concurrent execution, and process pool support.

Replaces the mock 72-line file that used asyncio.sleep() pretending to be Rust.

Features:
- Real TTL+LRU memory cache for agent context
- Concurrent task executor with semaphore-bounded parallelism
- ProcessPoolExecutor for CPU-bound operations (AST parsing, embeddings)
- Performance metrics tracking
```

**Dependencies (Imports):**
asyncio, concurrent.futures.ProcessPoolExecutor, functools.lru_cache, logging, time, typing.Any, typing.Callable, typing.Dict, typing.List, typing.Optional

**Classes and Methods:**

### `class PerformanceCache`
> Real high-performance cache with TTL expiry and LRU eviction.

Replaces the mock RustMemoryCache that did nothing useful.
Uses a dict-based approach with timestamp tracking for TTL.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, max_size, ttl)` | Internal logic handler. |
| `store_context` | `(self, key, data)` | Store data in cache with TTL. |
| `retrieve_context` | `(self, key)` | Retrieve data from cache, return empty string if expired or missing. |
| `delete` | `(self, key)` | Remove entry from cache. |
| `clear` | `(self)` | Clear all entries. Returns count cleared. |
| `_evict_oldest` | `(self)` | Remove the least recently accessed entry. |
| `stats` | `(self)` | Cache statistics. |

### `class ConcurrentExecutor`
> Bounded concurrent task executor using asyncio.Semaphore.

Replaces the mock RustToolExecutor that used asyncio.sleep(0.05).
Handles real concurrent I/O operations with backpressure.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, max_workers)` | Internal logic handler. |
| `execute` | `(self, coroutine)` | Execute a single coroutine with bounded concurrency. |
| `execute_batch` | `(self, coroutines)` | Execute multiple coroutines concurrently with bounded parallelism. |
| `run_in_process` | `(self, func)` | Run a CPU-bound function in a ProcessPoolExecutor. |
| `shutdown` | `(self)` | Shutdown the process pool. |
| `stats` | `(self)` | Executor statistics. |

### `class GACIEngine`
> General Artificial Coding Intelligence Orchestrator.

High-performance Python implementation combining:
- Real TTL cache for context management
- Bounded concurrent execution for tool parallelism
- Process pool for CPU-bound operations

Note: The original aspirational description was "Rust Hyper-Core Substrate."
This is honest Python — fast, real, and production-ready.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, max_cache_size, max_workers)` | Internal logic handler. |
| `process_gaci_task` | `(self, task_id, instructions)` | Process a task with context caching and bounded execution. |
| `stats` | `(self)` | Combined performance statistics. |
| `shutdown` | `(self)` | Clean shutdown. |

---

## 📄 `kernel/sandbox.py`

**Purpose:**
```text
Sandbox Manager v2 — Real Execution Isolation

Multi-backend sandbox with actual subprocess isolation, Docker support,
and E2B integration. Replaces the 50-line mock with real functionality.

Backends:
- subprocess: Works immediately, uses asyncio.create_subprocess_exec with resource limits
- docker: Production isolation using Docker containers
- e2b: Cloud-scale Firecracker MicroVMs via E2B SDK
- none: Direct execution (for trusted environments)

Inspired by: OpenHands Docker sandbox, E2B Firecracker MicroVMs,
Claude Code OS-level sandbox (bubblewrap/seatbelt)
```

**Dependencies (Imports):**
asyncio, dataclasses.dataclass, dataclasses.field, datetime.datetime, datetime.timezone, logging, os, platform, shlex, tempfile, typing.Any, typing.Dict, typing.List, typing.Optional, uuid.uuid4

**Classes and Methods:**

### `class SandboxResult`
> Result from sandbox execution.

*No explicit methods defined.*

### `class SandboxInstance`
> Tracks an active sandbox.

*No explicit methods defined.*

### `class SubprocessSandbox`
> Subprocess-based sandbox using asyncio.

Works on any OS without Docker. Provides basic isolation via:
- Separate subprocess (not in-process)
- Timeout enforcement
- Working directory restriction
- Environment variable isolation
- Output capture and truncation

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `execute` | `(self, command, working_dir, timeout, env, memory_limit_mb)` | Execute a command in a sandboxed subprocess. |

### `class DockerSandbox`
> Docker container-based sandbox for production isolation.

Features:
- Full container isolation
- Read-only filesystem with tmpfs scratch
- Network mode: none (default), allowlist, or full
- CPU and memory limits
- Auto cleanup

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, image)` | Internal logic handler. |
| `is_available` | `(self)` | Check if Docker is installed and running. |
| `execute` | `(self, command, working_dir, timeout, env, memory_limit_mb, cpu_limit, network_mode)` | Execute a command inside a Docker container. |

### `class E2BSandbox`
> E2B (Execute to Build) cloud sandbox using Firecracker MicroVMs.

Requires E2B API key. Each execution runs in an isolated MicroVM
with ~150ms cold start.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `execute` | `(self, command, working_dir, timeout)` | Execute a command in an E2B cloud sandbox. |

### `class ZeroTrustSandbox`
> Unified sandbox manager with pluggable backends.

Upgraded from 50-line mock to real multi-backend isolation.
Backward-compatible class name for existing code.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, config)` | Internal logic handler. |
| `_create_backend` | `(self, name)` | Create the sandbox backend. |
| `provision_sandbox` | `(self, task_id)` | Provision an isolated execution environment. |
| `execute` | `(self, command, sandbox_id, timeout, env)` | Execute a command in the sandbox. |
| `execute_tool` | `(self, tool, arguments, context)` | Execute a tool within the sandbox environment. |
| `request_network_access` | `(self, sandbox_id, endpoint)` | Check if a sandbox is allowed to access a network endpoint. |
| `teardown_sandbox` | `(self, sandbox_id)` | Remove and clean up a sandbox. |
| `calculate_security_score` | `(self)` | Calculate real-time security score based on isolation posture. |

---

## 📄 `kernel/session_manager.py`

**Purpose:**
```text
Session Manager v2 — SQLite-backed Session & Context Management

Upgraded from JSON-file storage to SQLite with:
- ACID transactions for crash safety
- Conversation memory tracking
- Project-level configuration loading (.agentrules)
- Session timeout and auto-cleanup
- Event bus integration

Inspired by: Cursor sessions/context, OpenHands workspaces
```

**Dependencies (Imports):**
datetime.datetime, datetime.timezone, json, logging, os, sqlite3, typing.Any, typing.Dict, typing.List, typing.Optional, uuid

**Classes and Methods:**

### `class SessionContext`
> User session with workspace state.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, session_id, user_id, workspace_path, mode, context)` | Internal logic handler. |
| `update_activity` | `(self)` | Internal logic handler. |
| `add_task` | `(self, task_id)` | Internal logic handler. |
| `add_file` | `(self, file_path)` | Internal logic handler. |
| `add_command` | `(self, command)` | Internal logic handler. |
| `add_message` | `(self, role, content)` | Add a conversation message to session memory. |
| `get_recent_files` | `(self, limit)` | Internal logic handler. |
| `get_recent_tasks` | `(self, limit)` | Internal logic handler. |
| `get_conversation_context` | `(self, last_n)` | Get recent conversation for LLM context building. |
| `to_dict` | `(self)` | Internal logic handler. |
| `from_dict` | `(cls, data)` | Internal logic handler. |

### `class SessionManager`
> Manages user sessions with SQLite persistence.

Upgraded from JSON files to SQLite for:
- ACID transactions
- Fast queries
- Concurrent access support

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, storage_path, event_bus)` | Internal logic handler. |
| `_init_db` | `(self)` | Create SQLite tables. |
| `create_session` | `(self, user_id, workspace_path, mode, context)` | Internal logic handler. |
| `get_session` | `(self, session_id)` | Internal logic handler. |
| `get_active_session` | `(self, user_id)` | Internal logic handler. |
| `update_session_activity` | `(self, session_id)` | Internal logic handler. |
| `add_task_to_session` | `(self, session_id, task_id)` | Internal logic handler. |
| `add_file_to_session` | `(self, session_id, file_path)` | Internal logic handler. |
| `add_command_to_session` | `(self, session_id, command)` | Internal logic handler. |
| `add_message_to_session` | `(self, session_id, role, content)` | Add conversation message for context tracking. |
| `end_session` | `(self, session_id)` | Internal logic handler. |
| `list_user_sessions` | `(self, user_id)` | Internal logic handler. |
| `cleanup_old_sessions` | `(self, days)` | Internal logic handler. |
| `_save_to_db` | `(self, session)` | Internal logic handler. |
| `load_sessions` | `(self)` | Internal logic handler. |
| `_delete_from_db` | `(self, session_id)` | Internal logic handler. |
| `_migrate_from_json` | `(self, json_dir)` | Migrate legacy JSON file sessions to SQLite. |
| `save_session` | `(self, session)` | Internal logic handler. |
| `delete_session_file` | `(self, session_id)` | Internal logic handler. |

---

## 📄 `kernel/skill_compiler.py`

**Purpose:**
```text
Skill Compiler v2 — Task Pattern Learning

Real implementation:
- Analyze completed tasks to extract reusable tool sequences
- Store patterns for future task suggestions
- Auto-suggest learned patterns
```

**Dependencies (Imports):**
collections.Counter, logging, typing.Any, typing.Dict, typing.List

**Classes and Methods:**

### `class LearnedSkill`
> A reusable pattern extracted from task history.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, name, tool_sequence, domain, success_count)` | Internal logic handler. |
| `to_dict` | `(self)` | Internal logic handler. |

### `class SkillCompiler`
> Extracts and stores reusable task patterns.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self)` | Internal logic handler. |
| `analyze_session` | `(self, task_id, domain, tool_sequence)` | Analyze a completed task for reusable patterns. |
| `suggest_tools` | `(self, domain, context)` | Suggest tools based on learned patterns. |
| `get_skills` | `(self, domain)` | Internal logic handler. |
| `get_stats` | `(self)` | Internal logic handler. |

---

## 📄 `kernel/skills_registry.py`

**Purpose:**
```text
Skills Registry: Core Capabilities

Inspired by OpenHands skills + Aider capabilities
```

**Dependencies (Imports):**
enum.Enum, typing.Dict, typing.List, typing.Optional

**Classes and Methods:**

### `class SkillLevel`
*No explicit methods defined.*

### `class Skill`
> Represents a skill with tools and permission level

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, name, description, tools, level, pack)` | Internal logic handler. |

### `class SkillRegistry`
> Registry of all available skills

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self)` | Internal logic handler. |
| `load_defaults` | `(self)` | Load core 7 skills + optional packs |
| `get_skill` | `(self, name)` | Get skill by name |
| `list_skills` | `(self, pack)` | List skills in a pack |
| `get_tools_for_skill` | `(self, skill_name)` | Get MCP tool names for a skill |
| `get_skill_by_tool` | `(self, tool_name)` | Get skill that contains a specific tool |
| `to_mcp_tools` | `(self, pack)` | Convert skills to MCP tool names |

---

## 📄 `kernel/swarm.py`

**Purpose:**
```text
Agent Swarm v2 — Real Multi-Agent Orchestration

Upgraded from 75-line string-matching mock to real multi-agent system:
- Typed specialized agent roles (Architect, Coder, Reviewer, Tester, Researcher)
- LLM-driven task decomposition (not string matching)
- Parallel subtask execution with asyncio.gather
- Inter-agent communication via EventBus
- Result aggregation and conflict resolution

Inspired by: Claude Code agent teams, Cursor subagents, OpenHands parallel agents
```

**Dependencies (Imports):**
asyncio, dataclasses.dataclass, dataclasses.field, datetime.datetime, datetime.timezone, enum.Enum, logging, typing.Any, typing.Callable, typing.Dict, typing.List, typing.Optional, uuid.uuid4

**Classes and Methods:**

### `class AgentRole`
> Specialized agent roles within a swarm.

*No explicit methods defined.*

### `class SwarmAgent`
> A specialized agent within the swarm.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `to_dict` | `(self)` | Internal logic handler. |

### `class SubTask`
> A subtask assigned to a specific agent.

*No explicit methods defined.*

### `class SwarmResult`
> Aggregated result from swarm execution.

*No explicit methods defined.*

### `class AgentSwarm`
> Multi-agent coordination with real task decomposition and parallel execution.

Upgraded from hardcoded agents + string matching to:
- Typed specialized agents per role
- Task decomposition (rule-based now, LLM-injectable)
- Parallel execution of independent subtasks
- Result aggregation

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, swarm_id, llm_provider, event_bus)` | Internal logic handler. |
| `delegate_task` | `(self, task_description, context)` | Decompose and delegate a task to specialized agents. |
| `_decompose_task` | `(self, description, context)` | Decompose a task into subtasks. |
| `_execute_subtask` | `(self, subtask)` | Execute a single subtask (placeholder for real LLM-driven execution). |
| `_find_best_agent` | `(self, subtask)` | Find the best idle agent for a subtask. |
| `get_swarm_status` | `(self)` | Return status of all agents. |
| `get_history` | `(self)` | Return task execution history. |

---

## 📄 `kernel/task_state_machine.py`

**Purpose:**
```text
Task State Machine v2 — SQLite-backed Durable Task Execution

Upgraded from JSON-file persistence to SQLite with:
- Real SQLite backend (crash-safe ACID transactions)
- Async step execution with timeout
- Retry logic with configurable max attempts
- Task dependency support
- Event bus integration for lifecycle notifications
- Full backward compatibility with existing Task/TaskStep classes

Inspired by: OpenHands task orchestration, Cursor autonomy controls
```

**Dependencies (Imports):**
datetime.datetime, datetime.timezone, enum.Enum, json, logging, os, sqlite3, typing.Any, typing.Dict, typing.List, typing.Optional

**Classes and Methods:**

### `class TaskStatus`
*No explicit methods defined.*

### `class TaskType`
*No explicit methods defined.*

### `class TaskStep`
> Individual step in a task with retry support.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, id, description, tools, status, result, error, max_retries)` | Internal logic handler. |
| `to_dict` | `(self)` | Internal logic handler. |
| `from_dict` | `(cls, data)` | Internal logic handler. |

### `class Task`
> Durable task with state persistence.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, id, type, description, steps, status, context, session_id)` | Internal logic handler. |
| `get_current_step` | `(self)` | Internal logic handler. |
| `advance_step` | `(self)` | Internal logic handler. |
| `complete_step` | `(self, result)` | Internal logic handler. |
| `fail_step` | `(self, error)` | Internal logic handler. |
| `progress` | `(self)` | Task completion percentage. |
| `to_dict` | `(self)` | Internal logic handler. |
| `from_dict` | `(cls, data)` | Internal logic handler. |

### `class TaskStateMachine`
> Manages task execution with SQLite persistence.

Upgraded from JSON file storage to SQLite for:
- ACID transactions (crash-safe)
- Fast queries by status, session, type
- No file-per-task overhead
- Concurrent access support

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, storage_path, event_bus)` | Internal logic handler. |
| `_init_db` | `(self)` | Create SQLite tables if not exists. |
| `create_task` | `(self, type, description, steps, context, session_id)` | Create a new task with SQLite persistence. |
| `get_task` | `(self, task_id)` | Internal logic handler. |
| `execute_task_async` | `(self, task_id, step_executor)` | Execute task step-by-step with async support and timeout. |
| `execute_task` | `(self, task_id)` | Synchronous task execution (backward compatible). |
| `pause_task` | `(self, task_id)` | Internal logic handler. |
| `resume_task` | `(self, task_id)` | Internal logic handler. |
| `cancel_task` | `(self, task_id)` | Internal logic handler. |
| `list_tasks` | `(self, status, session_id)` | Internal logic handler. |
| `_save_to_db` | `(self, task)` | Persist task to SQLite. |
| `load_tasks` | `(self)` | Load all tasks from SQLite. |
| `_migrate_from_json` | `(self, json_dir)` | Migrate from legacy JSON file storage to SQLite. |
| `save_task` | `(self, task)` | Internal logic handler. |
| `execute_step` | `(self, step)` | Legacy synchronous step executor (placeholder for orchestrator). |
| `_emit_event` | `(self, event_type, task, step)` | Emit task lifecycle event. |

---

## 📄 `kernel/tool_executor.py`

**Purpose:**
```text
Tool Executor — Central Tool Execution Pipeline

All tool calls flow through this pipeline:
  1. Governance check (is the tool allowed?)
  2. Sandbox routing (does it need isolation?)
  3. Execution (builtin, MCP, or sandboxed)
  4. Audit logging (record what happened)

Inspired by: Claude Code's tool architecture, OpenHands ActionExecutor
```

**Dependencies (Imports):**
asyncio, dataclasses.dataclass, dataclasses.field, datetime.datetime, datetime.timezone, enum.Enum, logging, typing.Any, typing.Dict, typing.List, typing.Optional, uuid.uuid4

**Classes and Methods:**

### `class ToolMutability`
> How a tool modifies the environment.

*No explicit methods defined.*

### `class ToolCall`
> A request to execute a tool.

*No explicit methods defined.*

### `class ToolResult`
> Result of a tool execution.

*No explicit methods defined.*

### `class PolicyDecision`
> Governance decision for a tool call.

*No explicit methods defined.*

### `class ExecutionContext`
> Context for tool execution.

*No explicit methods defined.*

### `class ToolExecutor`
> Central pipeline for all tool execution.

Every tool call goes through:
1. Governance gate — check if the tool is allowed
2. Sandbox routing — run in sandbox if required
3. Execution — call the actual tool
4. Audit + Event — log and publish result

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, governance, sandbox, event_bus, mcp_client)` | Internal logic handler. |
| `register_tool` | `(self, tool)` | Register a tool implementation. |
| `register_tools` | `(self, tools)` | Register multiple tool implementations. |
| `get_tool` | `(self, name)` | Get a registered tool by name. |
| `list_tools` | `(self)` | List all registered tools with their schemas. |
| `execute` | `(self, tool_call, context)` | Execute a tool call through the full pipeline. |
| `execute_batch` | `(self, tool_calls, context)` | Execute multiple independent tool calls concurrently. |
| `_check_governance` | `(self, tool_call, context)` | Check governance policy for a tool call. |
| `_emit_event` | `(self, event_type, tool_call, result)` | Emit an event through the event bus. |

---

## 📄 `kernel/universal_tools.py`

**Purpose:**
```text
Universal Tools Module - Consolidated tools for Agentic OS
```

**Dependencies (Imports):**
abc.ABC, abc.abstractmethod, asyncio, dataclasses.dataclass, enum.Enum, logging, os, pathlib.Path, platform, re, shlex, typing.Any, typing.Dict, typing.Optional

**Classes and Methods:**

### `class ToolMutability`
> How a tool modifies the environment.

*No explicit methods defined.*

### `class ToolResult`
> Standard result from tool execution.

*No explicit methods defined.*

### `class BaseTool`
> Abstract base class for all kernel tools.

Subclasses must define:
- name: unique identifier (e.g., "read_file")
- description: what the tool does
- input_schema: JSON Schema for arguments
- execute(): the actual implementation

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `execute` | `(self, arguments, context)` | Execute the tool with the given arguments. |
| `to_schema` | `(self)` | Export tool definition for MCP/LLM function calling. |

### `class ReadFileTool`
> Read the contents of a file with optional line range.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `execute` | `(self, arguments, context)` | Internal logic handler. |

### `class WriteFileTool`
> Write content to a file, creating directories as needed.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `execute` | `(self, arguments, context)` | Internal logic handler. |

### `class EditFileTool`
> Search-and-replace editing within a file.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `execute` | `(self, arguments, context)` | Internal logic handler. |

### `class SearchFilesTool`
> Search for text patterns across files using ripgrep-style matching.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `execute` | `(self, arguments, context)` | Internal logic handler. |
| `_glob_match` | `(filename, pattern)` | Simple glob matching for file extensions. |

### `class ListDirectoryTool`
> List contents of a directory.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `execute` | `(self, arguments, context)` | Internal logic handler. |
| `_list_dir` | `(self, dir_path, entries, recursive, max_depth, current_depth, base_path)` | Recursively list directory contents. |

### `class GitStatusTool`
> Show the working tree status.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `execute` | `(self, arguments, context)` | Internal logic handler. |

### `class GitDiffTool`
> Show changes in the working tree.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `execute` | `(self, arguments, context)` | Internal logic handler. |

### `class GitCommitTool`
> Commit staged changes with a message.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `execute` | `(self, arguments, context)` | Internal logic handler. |

### `class GitLogTool`
> Show commit history.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `execute` | `(self, arguments, context)` | Internal logic handler. |

### `class BashExecuteTool`
> Execute shell commands with timeout and output capture.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `execute` | `(self, arguments, context)` | Internal logic handler. |

### `class WebSearchTool`
> Search the web using DuckDuckGo Lite (no API key required).

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `execute` | `(self, arguments, context)` | Internal logic handler. |

### `class WebFetchTool`
> Fetch content from a URL and convert to text.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `execute` | `(self, arguments, context)` | Internal logic handler. |
| `_html_to_text` | `(html)` | Basic HTML to text conversion. |

**Standalone Functions:**

| Function | Arguments | Purpose |
|----------|-----------|---------|
| `_run_git` | `(args, cwd, timeout)` | Run a git command and return structured output. |
| `_resolve_cwd` | `(arguments, context)` | Resolve working directory from arguments or context. |
| `get_all_tools` | `()` | Return instances of all core tools. |

---

## 📄 `kernel/wasm_driver.py`

**Purpose:**
```text
WASM Driver v2 — WebAssembly Execution (with Fallback)

Honest implementation:
- wasmtime-py integration when available
- Falls back to subprocess sandbox for isolation
- Documented as optional capability
```

**Dependencies (Imports):**
asyncio, logging, typing.Any, typing.Dict

**Classes and Methods:**

### `class WasmDriver`
> WebAssembly execution driver with subprocess fallback.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self)` | Internal logic handler. |
| `_check_dependencies` | `(self)` | Internal logic handler. |
| `execute_in_wasm` | `(self, tool_name, arguments)` | Execute a tool in WASM sandbox (or subprocess fallback). |
| `_execute_wasmtime` | `(self, tool_name, arguments)` | Execute via wasmtime (when available). |
| `_execute_subprocess_fallback` | `(self, tool_name, arguments)` | Fallback: execute in isolated subprocess. |
| `get_status` | `(self)` | Internal logic handler. |

---

## 📄 `main.py`

**Purpose:**
```text
Project Kernel Runtime: Antigravity Agentic OS
Master Entry Point (Horizon 2028 Architecture)
```

**Dependencies (Imports):**
argparse, pathlib.Path, project_kernel_runtime.services.fastapi_server.run_server, sys

**Standalone Functions:**

| Function | Arguments | Purpose |
|----------|-----------|---------|
| `main` | `()` | Single Unified Pipeline Bootstrapper |

---

## 📄 `memory/chroma_store.py`

**Purpose:**
```text
Vector DB v2 — ChromaDB-backed Semantic Memory + Codebase RAG

Upgraded from abstract base to real implementation:
- ChromaDB persistent backend (no external server needed)
- Agent memory layer (remember/recall/forget)
- Codebase RAG pipeline (index workspace, query by meaning)
- Sentence-transformer embeddings (via ChromaDB default)
- Collection management for multi-tenant isolation

Inspired by: Cursor RAG indexing, Windsurf Codemaps, Claude Code project memory
```

**Dependencies (Imports):**
datetime.datetime, datetime.timezone, logging, os, typing.Any, typing.Dict, typing.List, typing.Optional, uuid.uuid4

**Classes and Methods:**

### `class MemoryResult`
> A result from memory recall.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, id, content, metadata, distance)` | Internal logic handler. |
| `to_dict` | `(self)` | Internal logic handler. |

### `class CodeSnippet`
> A code snippet from codebase RAG.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, file_path, content, start_line, end_line, language, score)` | Internal logic handler. |
| `to_dict` | `(self)` | Internal logic handler. |

### `class ChromaVectorStore`
> ChromaDB-backed vector store for semantic search.

Uses ChromaDB's built-in embedding functions.
Falls back to in-memory store if ChromaDB not installed.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, persist_dir)` | Internal logic handler. |
| `_init_store` | `(self)` | Initialize ChromaDB or fall back to in-memory. |
| `store` | `(self, text, metadata, id)` | Store text with optional metadata. |
| `search` | `(self, query, top_k, where)` | Search for similar documents. |
| `delete` | `(self, id)` | Delete a document. |
| `count` | `(self)` | Internal logic handler. |

### `class AgentMemory`
> Long-term agent memory using vector similarity search.

Provides remember/recall/forget operations over the vector store.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, vector_store)` | Internal logic handler. |
| `remember` | `(self, content, context, task_id, category)` | Store a memory. |
| `recall` | `(self, query, limit, category)` | Recall memories similar to query. |
| `forget` | `(self, memory_id)` | Remove a memory. |

### `class CodebaseRAG`
> Codebase semantic indexing and retrieval.

Indexes source files by chunks and enables semantic search.
Inspired by: Cursor's codebase indexing, Windsurf Codemaps

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, vector_store, persist_dir)` | Internal logic handler. |
| `store` | `(self)` | Internal logic handler. |
| `index_workspace` | `(self, workspace_path, max_files)` | Index a workspace for semantic search. |
| `query` | `(self, question, top_k)` | Query indexed codebase by semantic meaning. |
| `_chunk_code` | `(self, content, file_path, chunk_size)` | Chunk code into segments for indexing. |

---

## 📄 `memory/state_hub.py`

**Purpose:**
```text
Antigravity Prime: Centralized Global State Hub (Month 25-26)
Architectural Pillar: Single Source of Truth (SSOT).
```

**Dependencies (Imports):**
time, typing.Any, typing.Dict, typing.List

**Classes and Methods:**

### `class GlobalStateHub`
> The Single Source of Truth (SSOT) for the entire Antigravity Kernel.
Every agent step, sandbox state, and mesh heartbeat is tracked here.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self)` | Internal logic handler. |
| `update_task_state` | `(self, task_id, status, result)` | Internal logic handler. |
| `record_thought` | `(self, agent_id, agent_type, thought)` | Streams a 'Reasoning Frame' for total observability. |
| `get_snapshot` | `(self)` | Provides a complete system state for UI/API synchronization. |
| `inject_thought_delta` | `(self, agent_id, new_logic)` | Hot Reloads 'Self-Attention' logic for a running agent. |

---

## 📄 `observability/__init__.py`

**Purpose:**
```text
Observability and monitoring infrastructure for Project Kernel Runtime.
```

**Dependencies (Imports):**
logging.get_logger, logging.setup_logging, metrics.get_counter, metrics.get_histogram, metrics.setup_metrics, tracing.get_tracer, tracing.setup_tracing

---

## 📄 `observability/health.py`

**Purpose:**
```text
Health check endpoints for Project Kernel Runtime.
```

**Dependencies (Imports):**
asyncio, fastapi.FastAPI, fastapi.HTTPException, fastapi.responses.JSONResponse, fastapi.status, logging.get_logger, logging.log_api_request, metrics.get_meter, time, tracing.get_tracer, typing.Any, typing.Dict, typing.Optional

**Classes and Methods:**

### `class HealthChecker`
> Health checker for monitoring service health.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self)` | Internal logic handler. |
| `_register_default_checks` | `(self)` | Register default health checks. |
| `register_check` | `(self, name, check_func)` | Register a health check function. |
| `run_checks` | `(self)` | Run all registered health checks. |
| `_check_database` | `(self)` | Check database connectivity. |
| `_check_redis` | `(self)` | Check Redis connectivity. |
| `_check_llm_provider` | `(self)` | Check LLM provider connectivity. |
| `_check_mcp_server` | `(self)` | Check MCP server connectivity. |
| `_check_storage` | `(self)` | Check storage connectivity. |

**Standalone Functions:**

| Function | Arguments | Purpose |
|----------|-----------|---------|
| `get_health_checker` | `()` | Get the global health checker instance. |
| `setup_health_check_routes` | `(app)` | Setup health check routes for FastAPI application. |
| `register_custom_health_check` | `(name, check_func)` | Register a custom health check function. |
| `setup_circuit_breaker` | `()` | Setup circuit breaker for external service calls. |
| `setup_rate_limiting` | `()` | Setup rate limiting for API endpoints. |

---

## 📄 `observability/logging.py`

**Purpose:**
```text
Structured logging implementation for Project Kernel Runtime.
```

**Dependencies (Imports):**
datetime.datetime, json, logging, logging.handlers, os, pathlib.Path, sys, typing.Any, typing.Dict, typing.Optional, typing.Union

**Classes and Methods:**

### `class JSONFormatter`
> JSON formatter for structured logging.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `format` | `(self, record)` | Format log record as JSON. |
| `_json_serializer` | `(self, obj)` | JSON serializer for non-serializable objects. |

### `class StructuredLogger`
> Structured logger with JSON formatting and context support.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, name, level)` | Internal logic handler. |
| `_setup_handlers` | `(self)` | Setup logging handlers. |
| `info` | `(self, message)` | Log info message with extra context. |
| `warning` | `(self, message)` | Log warning message with extra context. |
| `error` | `(self, message)` | Log error message with extra context. |
| `debug` | `(self, message)` | Log debug message with extra context. |
| `critical` | `(self, message)` | Log critical message with extra context. |
| `exception` | `(self, message)` | Log exception message with extra context. |

**Standalone Functions:**

| Function | Arguments | Purpose |
|----------|-----------|---------|
| `setup_logging` | `(level, log_dir, json_format)` | Setup structured logging for the application. |
| `get_logger` | `(name)` | Get a logger instance for the specified name. |
| `_configure_loggers` | `()` | Configure specific loggers for different components. |
| `log_api_request` | `(method, path, status_code, duration_ms, user_id, trace_id)` | Log API request with structured data. |
| `log_task_execution` | `(task_id, task_type, status, duration_ms, user_id, trace_id)` | Log task execution with structured data. |
| `log_mcp_interaction` | `(method, tool_name, status, duration_ms, user_id, trace_id)` | Log MCP interaction with structured data. |
| `log_llm_call` | `(provider, model, prompt_tokens, completion_tokens, duration_ms, user_id, trace_id)` | Log LLM provider call with structured data. |
| `log_error` | `(error_type, error_message, context, user_id, trace_id)` | Log error with structured data. |

---

## 📄 `observability/metrics.py`

**Purpose:**
```text
OpenTelemetry metrics implementation for Project Kernel Runtime.
```

**Dependencies (Imports):**
logging, opentelemetry.exporter.otlp.proto.http.metrics_exporter.OTLPMetricExporter, opentelemetry.metrics, opentelemetry.metrics.Counter, opentelemetry.metrics.Histogram, opentelemetry.metrics.UpDownCounter, opentelemetry.sdk.metrics.MeterProvider, opentelemetry.sdk.metrics.export.ConsoleMetricExporter, opentelemetry.sdk.metrics.export.PeriodicExportingMetricReader, time, typing.Optional

**Standalone Functions:**

| Function | Arguments | Purpose |
|----------|-----------|---------|
| `setup_metrics` | `(service_name, endpoint, console_export)` | Setup OpenTelemetry metrics with configurable exporters. |
| `get_meter` | `()` | Get the global meter instance. |
| `get_counter` | `(name, description)` | Get or create a counter metric. |
| `get_histogram` | `(name, description)` | Get or create a histogram metric. |
| `get_up_down_counter` | `(name, description)` | Get or create an up-down counter metric. |
| `get_request_counter` | `()` | Counter for HTTP requests. |
| `get_request_duration_histogram` | `()` | Histogram for HTTP request duration. |
| `get_task_counter` | `()` | Counter for tasks executed. |
| `get_task_duration_histogram` | `()` | Histogram for task execution duration. |
| `get_error_counter` | `()` | Counter for errors encountered. |
| `get_active_sessions_counter` | `()` | Counter for active user sessions. |
| `get_mcp_calls_counter` | `()` | Counter for MCP calls. |
| `get_llm_calls_counter` | `()` | Counter for LLM provider calls. |
| `track_execution_time` | `(metric_name, description)` | Decorator to track execution time of a function. |
| `track_api_request` | `(func)` | Decorator to track API request metrics. |
| `track_task_execution` | `(func)` | Decorator to track task execution metrics. |

---

## 📄 `observability/middleware.py`

**Purpose:**
```text
Middleware for observability integration in Project Kernel Runtime.
```

**Dependencies (Imports):**
fastapi.Request, fastapi.Response, fastapi.middleware.base.BaseHTTPMiddleware, logging.get_logger, logging.log_api_request, metrics.get_request_counter, metrics.get_request_duration_histogram, opentelemetry.propagate.extract, opentelemetry.trace, time, tracing.get_tracer, typing.Callable, typing.Optional

**Classes and Methods:**

### `class ObservabilityMiddleware`
> Middleware to add observability to HTTP requests.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `dispatch` | `(self, request, call_next)` | Process request with observability tracking. |

### `class MetricsMiddleware`
> Middleware to collect metrics for HTTP requests.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `dispatch` | `(self, request, call_next)` | Process request with metrics collection. |

### `class LoggingMiddleware`
> Middleware to add logging to HTTP requests.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `dispatch` | `(self, request, call_next)` | Process request with logging. |

### `class SecurityMiddleware`
> Middleware to add security logging to HTTP requests.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `dispatch` | `(self, request, call_next)` | Process request with security logging. |

**Standalone Functions:**

| Function | Arguments | Purpose |
|----------|-----------|---------|
| `setup_middleware` | `(app)` | Setup all middleware for the FastAPI application. |

---

## 📄 `observability/setup.py`

**Purpose:**
```text
Setup script for observability components.
```

**Dependencies (Imports):**
setuptools.find_packages, setuptools.setup

---

## 📄 `observability/tracing.py`

**Purpose:**
```text
OpenTelemetry tracing implementation for Project Kernel Runtime.
```

**Dependencies (Imports):**
asyncio, logging, opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter, opentelemetry.sdk.resources.Resource, opentelemetry.sdk.trace.TracerProvider, opentelemetry.sdk.trace.export.BatchSpanProcessor, opentelemetry.sdk.trace.export.ConsoleSpanExporter, opentelemetry.trace, opentelemetry.trace.SpanKind, opentelemetry.trace.status.Status, opentelemetry.trace.status.StatusCode, typing.Optional

**Standalone Functions:**

| Function | Arguments | Purpose |
|----------|-----------|---------|
| `setup_tracing` | `(service_name, endpoint, console_export)` | Setup OpenTelemetry tracing with configurable exporters. |
| `get_tracer` | `()` | Get the global tracer instance. |
| `trace_orchestrator_call` | `(func)` | Decorator to trace orchestrator method calls. |
| `trace_api_call` | `(func)` | Decorator to trace API endpoint calls. |
| `trace_mcp_interaction` | `(func)` | Decorator to trace MCP client/server interactions. |
| `trace_async_operation` | `(operation_name, async_func)` | Trace an async operation with proper context propagation. |

---

## 📄 `protocols/federated_hub.py`

**Purpose:**
```text
Federated Hub v2 — Knowledge Sharing Between Instances

Real federated learning patterns:
- Task success/failure pattern storage in vector DB
- Anonymized metric aggregation
- Privacy-preserving pattern sharing
```

**Dependencies (Imports):**
logging, time, typing.Any, typing.Dict, typing.List

**Classes and Methods:**

### `class FederatedHub`
> Federated knowledge sharing hub between agent instances.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self)` | Internal logic handler. |
| `start_gossip` | `(self)` | Start gossip protocol for peer metric exchange. |
| `stop_gossip` | `(self)` | Internal logic handler. |
| `share_pattern` | `(self, pattern_type, data, anonymize)` | Share a task pattern with the federation. |
| `query_patterns` | `(self, pattern_type, limit)` | Query shared patterns. |
| `sync_metrics` | `(self, peer_id, metrics)` | Receive metrics from a peer for aggregation. |
| `get_aggregated_metrics` | `(self)` | Get aggregated metrics across peers. |
| `_anonymize` | `(data)` | Remove PII from shared data. |

---

## 📄 `protocols/mcp_client.py`

**Purpose:**
```text
MCP Client: Model Context Protocol Implementation

Inspired by Anthropic MCP + OpenHands tool integration
```

**Dependencies (Imports):**
asyncio, dataclasses.dataclass, json, typing.Any, typing.Callable, typing.Dict, typing.List, typing.Optional, websockets, websockets.exceptions.ConnectionClosedError

**Classes and Methods:**

### `class MCPTool`
> MCP Tool definition

*No explicit methods defined.*

### `class MCPResource`
> MCP Resource definition

*No explicit methods defined.*

### `class MCPPrompt`
> MCP Prompt definition

*No explicit methods defined.*

### `class MCPClient`
> Client for MCP server communication

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, server_url)` | Internal logic handler. |
| `connect` | `(self)` | Connect to MCP server |
| `disconnect` | `(self)` | Disconnect from MCP server |
| `_initialize` | `(self)` | Initialize MCP connection |
| `_list_tools` | `(self)` | List available tools |
| `_list_resources` | `(self)` | List available resources |
| `_list_prompts` | `(self)` | List available prompts |
| `call_tool` | `(self, tool_name, arguments)` | Call an MCP tool |
| `read_resource` | `(self, uri)` | Read an MCP resource |
| `get_prompt` | `(self, prompt_name, arguments)` | Get an MCP prompt |
| `_next_id` | `(self)` | Get next message ID |
| `_send_request` | `(self, request)` | Send JSON-RPC request and wait for response |
| `_message_handler` | `(self)` | Handle incoming messages from MCP server |
| `_handle_notification` | `(self, notification)` | Handle MCP notifications |

---

## 📄 `protocols/mcp_server.py`

**Purpose:**
```text
MCP Server v2 — MCP 2026 Streamable HTTP + Legacy WebSocket

Upgraded from WebSocket-only to dual transport:
- Streamable HTTP transport (POST for requests, GET for SSE streams)
- Session management with Mcp-Session-Id headers
- Resumability via Last-Event-ID
- Protocol version negotiation (2024-11-05 and 2025-03-26)
- Auto-registration of tools from ToolExecutor
- Legacy WebSocket transport preserved for backward compatibility

Ref: MCP spec March 2026 — https://spec.modelcontextprotocol.io
```

**Dependencies (Imports):**
asyncio, dataclasses.dataclass, dataclasses.field, datetime.datetime, datetime.timezone, json, logging, typing.Any, typing.Callable, typing.Dict, typing.List, typing.Optional, uuid

**Classes and Methods:**

### `class MCPTool`
> MCP Tool definition.

*No explicit methods defined.*

### `class MCPResource`
> MCP Resource definition.

*No explicit methods defined.*

### `class MCPPrompt`
> MCP Prompt definition.

*No explicit methods defined.*

### `class MCPSession`
> MCP session for Streamable HTTP.

*No explicit methods defined.*

### `class MCPServer`
> MCP Server with dual transport: Streamable HTTP + WebSocket.

MCP 2026 Spec features:
- POST: JSON-RPC request → direct JSON or SSE stream response
- GET: SSE stream for server-initiated notifications
- Mcp-Session-Id header for session management
- Last-Event-ID for resumability
- Protocol version negotiation

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, host, port)` | Internal logic handler. |
| `_setup_handlers` | `(self)` | Setup JSON-RPC method handlers. |
| `register_tool` | `(self, tool)` | Register a tool with the server. |
| `register_resource` | `(self, resource)` | Internal logic handler. |
| `register_prompt` | `(self, prompt)` | Internal logic handler. |
| `register_tools_from_executor` | `(self, tool_executor)` | Auto-register tools from the ToolExecutor's tool registry. |
| `handle_streamable_http_post` | `(self, body, headers)` | Handle POST requests (Streamable HTTP transport). |
| `handle_streamable_http_get` | `(self, headers)` | Handle GET requests — return SSE stream. |
| `_process_jsonrpc` | `(self, data, session)` | Process a single JSON-RPC request. |
| `_handle_initialize` | `(self, params, session)` | Handle initialize — protocol negotiation. |
| `_handle_initialized` | `(self, params, session)` | Client confirms initialization — notification, no response. |
| `_handle_tools_list` | `(self, params, session)` | Internal logic handler. |
| `_handle_tools_call` | `(self, params, session)` | Internal logic handler. |
| `_handle_resources_list` | `(self, params, session)` | Internal logic handler. |
| `_handle_resources_read` | `(self, params, session)` | Internal logic handler. |
| `_handle_prompts_list` | `(self, params, session)` | Internal logic handler. |
| `_handle_prompts_get` | `(self, params, session)` | Internal logic handler. |
| `_handle_ping` | `(self, params, session)` | Internal logic handler. |
| `_handle_sampling` | `(self, params, session)` | Handle sampling/createMessage — delegate to LLM provider. |
| `_notify_tools_changed` | `(self)` | Notify all clients that tools list changed. |
| `emit_sse_event` | `(self, event_type, data, session_id)` | Emit an SSE event to subscribers. |
| `start_websocket` | `(self)` | Start WebSocket server (legacy transport). |
| `_handle_ws_connection` | `(self, websocket, path)` | Handle a WebSocket connection. |
| `_error_response` | `(msg_id, code, message)` | Internal logic handler. |

---

## 📄 `protocols/mesh_p2p.py`

**Purpose:**
```text
Mesh P2P v2 — Peer Discovery with Heartbeat Tracking

Upgraded from 20-line print statement to real peer registry:
- Peer registration with health status and last-seen timestamps
- Heartbeat tracking with configurable timeout
- Peer discovery and cleanup
```

**Dependencies (Imports):**
logging, time, typing.Any, typing.Dict, typing.List, typing.Optional, uuid.uuid4

**Classes and Methods:**

### `class PeerInfo`
> Information about a peer in the mesh.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, peer_id, address, port, capabilities, metadata)` | Internal logic handler. |
| `to_dict` | `(self)` | Internal logic handler. |

### `class GlobalMeshP2P`
> Peer-to-peer mesh network for agent discovery and coordination.

| Method | Arguments | Purpose |
|--------|-----------|---------|
| `__init__` | `(self, heartbeat_timeout)` | Internal logic handler. |
| `register_self` | `(self, address, port, capabilities)` | Register this node in the mesh. |
| `register_peer` | `(self, peer_id, address, port, capabilities)` | Internal logic handler. |
| `heartbeat` | `(self, peer_id)` | Record heartbeat from peer. |
| `health_check` | `(self)` | Check health of all peers, mark stale ones. |
| `discover_peers` | `(self, capability)` | Find peers, optionally filtered by capability. |
| `remove_stale_peers` | `(self)` | Remove peers that haven't sent heartbeats. |
| `federated_sync` | `(self, metrics)` | Sync metrics with mesh (called by orchestrator). |
| `get_mesh_status` | `(self)` | Internal logic handler. |

---

## 📄 `restructure_2028.py`

**Purpose:** Core component belonging to its respective subsystem.

**Dependencies (Imports):**
glob, os, shutil

---

## 📄 `services/__init__.py`

**Purpose:** Core component belonging to its respective subsystem.

---

## 📄 `services/fastapi_server.py`

**Purpose:**
```text
FastAPI Server: HTTP/WebSocket API

Inspired by OpenHands REST API + Cursor web interface
```

**Dependencies (Imports):**
asyncio, contextlib.asynccontextmanager, datetime.datetime, fastapi.Depends, fastapi.FastAPI, fastapi.HTTPException, fastapi.WebSocket, fastapi.middleware.cors.CORSMiddleware, fastapi.responses.JSONResponse, fastapi.responses.RedirectResponse, fastapi.staticfiles.StaticFiles, json, os, project_kernel_runtime.kernel.task_state_machine.TaskStatus, project_kernel_runtime.memory.state_hub.state_hub, project_kernel_runtime.services.research_api.router, project_kernel_runtime.services.router_agent.router, project_kernel_runtime.services.router_mcp.router, sys, typing.Any, typing.Dict, typing.List, typing.Optional, uvicorn

**Standalone Functions:**

| Function | Arguments | Purpose |
|----------|-----------|---------|
| `lifespan` | `(app)` | Lifecycle event handler for the FastAPI app. |
| `root_redirect` | `()` | Internal utility function. |
| `health_check` | `()` | Health check endpoint |
| `websocket_endpoint` | `(websocket, user_id)` | WebSocket endpoint for real-time communication |
| `handle_websocket_message` | `(user_id, message)` | Handle WebSocket message |
| `prometheus_metrics` | `()` | Prometheus-compatible metrics endpoint. |
| `full_system_status` | `()` | Comprehensive system status including all subsystems. |
| `global_exception_handler` | `(request, exc)` | Global exception handler |
| `run_server` | `(host, port)` | Run the FastAPI server |

---

## 📄 `services/research_api.py`

**Purpose:** Core component belonging to its respective subsystem.

**Dependencies (Imports):**
fastapi.APIRouter, fastapi.HTTPException, project_kernel_runtime.kernel.orchestrator.Orchestrator, typing.Any, typing.Dict

**Standalone Functions:**

| Function | Arguments | Purpose |
|----------|-----------|---------|
| `start_research` | `(body)` | Internal utility function. |
| `list_sessions` | `(user_id)` | Internal utility function. |
| `add_source` | `(session_id, body)` | Internal utility function. |
| `list_reports` | `(session_id, user_id)` | Internal utility function. |
| `summarize` | `(session_id, body)` | Internal utility function. |
| `get_session` | `(session_id, user_id)` | Internal utility function. |
| `get_progress` | `(session_id, user_id)` | Internal utility function. |
| `get_sources` | `(session_id, user_id)` | Internal utility function. |
| `end_session` | `(session_id, body)` | Internal utility function. |
| `export_report` | `(session_id, report_id, user_id, format)` | Internal utility function. |

---

## 📄 `services/router_agent.py`

**Purpose:** Core component belonging to its respective subsystem.

**Dependencies (Imports):**
asyncio, datetime.datetime, fastapi.APIRouter, fastapi.Depends, fastapi.HTTPException, fastapi.responses.StreamingResponse, json, project_kernel_runtime.memory.state_hub.state_hub, typing.Any, typing.Dict, typing.Optional

**Standalone Functions:**

| Function | Arguments | Purpose |
|----------|-----------|---------|
| `patch_system_provider` | `(request)` | Hot-swap the system inference provider (Ollama, OpenAI, Anthropic) with custom host/port settings. |
| `create_session` | `(request)` | Internal utility function. |
| `end_session` | `(user_id)` | Internal utility function. |
| `get_session` | `(user_id)` | Internal utility function. |
| `create_task` | `(request)` | Internal utility function. |
| `execute_task` | `(task_id, request)` | Internal utility function. |
| `stop_task` | `(task_id, request)` | Internal utility function. |
| `get_task_status` | `(task_id, user_id)` | Internal utility function. |
| `get_task_trace` | `(task_id)` | Internal utility function. |
| `list_tasks` | `(user_id, status)` | Internal utility function. |
| `inject_memory` | `(request)` | Internal utility function. |
| `search_memory` | `(request)` | Internal utility function. |
| `tweak_governance` | `(request)` | Internal utility function. |
| `get_governance` | `()` | Internal utility function. |
| `call_tool` | `(request)` | Internal utility function. |
| `get_available_skills` | `(user_id)` | Internal utility function. |
| `get_intelligence_status` | `(user_id)` | Internal utility function. |
| `get_thought_stream` | `()` | Internal utility function. |
| `hot_reload_logic` | `(data)` | Internal utility function. |
| `trigger_gtm_campaign` | `(data)` | Internal utility function. |
| `reprobe_mcp` | `(data)` | Internal utility function. |
| `launch_app` | `(data)` | Internal utility function. |
| `dispatch_scratchpad` | `(data)` | Internal utility function. |
| `get_mcp_discovery` | `()` | Internal utility function. |
| `get_vision_config` | `()` | Internal utility function. |
| `update_vision_config` | `(data)` | Internal utility function. |
| `get_credits_balance` | `(tenant_id)` | Internal utility function. |
| `get_intelligence_status` | `(user_id)` | Internal utility function. |
| `get_thought_stream` | `()` | Internal utility function. |
| `hot_reload_logic` | `(data)` | Internal utility function. |
| `trigger_gtm_campaign` | `(data)` | Internal utility function. |
| `reprobe_mcp` | `(data)` | Internal utility function. |
| `launch_app` | `(data)` | Internal utility function. |
| `dispatch_scratchpad` | `(data)` | Internal utility function. |
| `get_mcp_discovery` | `()` | Internal utility function. |
| `get_vision_config` | `()` | Internal utility function. |
| `update_vision_config` | `(data)` | Internal utility function. |
| `get_credits_balance` | `(tenant_id)` | Internal utility function. |
| `list_mcps` | `()` | List all mounted MCP servers (both memory and permanent registry). |
| `mount_new_mcp` | `(data)` | Mount a new MCP protocol and optionally save to persistence. |
| `execute_agent_stream` | `(description, user_id, max_iterations)` | SSE endpoint that streams every step of the agentic loop to the UI in real-time. |
| `get_mcp_discovery` | `()` | Internal utility function. |
| `get_vision_config` | `()` | Internal utility function. |
| `update_vision_config` | `(data)` | Internal utility function. |
| `get_credits_balance` | `(tenant_id)` | Internal utility function. |
| `a2a_agent_card` | `()` | Internal utility function. |
| `execute_agentic_loop` | `(request)` | Internal utility function. |
| `fork_reality` | `(request)` | Internal utility function. |
| `sre_auto_heal` | `(request)` | Internal utility function. |

---

## 📄 `services/router_mcp.py`

**Purpose:** Core component belonging to its respective subsystem.

**Dependencies (Imports):**
fastapi.APIRouter, fastapi.HTTPException, fastapi.Request, json, typing.Any, typing.Dict

**Standalone Functions:**

| Function | Arguments | Purpose |
|----------|-----------|---------|
| `mcp_streamable_http_post` | `(request)` | Internal utility function. |
| `mcp_streamable_http_get` | `()` | Internal utility function. |
| `a2a_jsonrpc` | `(request)` | Internal utility function. |

---

## 📄 `ui/__init__.py`

**Purpose:** Core component belonging to its respective subsystem.

---

## 📄 `verify_upgrade.py`

**Purpose:**
```text
Verify Upgrade v2 — Complete System Verification

Tests all upgraded components:
1. Core infrastructure (config, event bus, governance, sandbox)
2. Intelligence (LLM, swarm, task machine, session)
3. Orchestrator (coordinator pattern, agentic loop)
4. Protocols (MCP server, A2A v0.3)
5. Vector DB (ChromaDB, agent memory, codebase RAG)
6. Subsystems (SRE, watchdog, mesh, federated, etc.)
7. Observability (structlog, metrics, tracing)
```

**Dependencies (Imports):**
asyncio, os, sys

**Standalone Functions:**

| Function | Arguments | Purpose |
|----------|-----------|---------|
| `test_section` | `(name)` | Internal utility function. |
| `verify_all` | `()` | Run comprehensive verification of all upgraded modules. |

---

