# kernel Architecture Documentation

*Generated on: 2026-03-28T15:12:48.060154*

---

#### __init__.py *(47 lines)*

> **Imports**: `from runtime import RuntimeConfig`, `from runtime import RuntimeProfile`, `from runtime import ConfigWatcher`, `from event_bus import EventBus`, `from event_bus import AgentEvent`, `from event_bus import EventTypes`, `from tool_executor import ToolExecutor`, `from tool_executor import ToolCall`, `from tool_executor import ToolResult`, `from tool_executor import ExecutionContext`, `from governance import GovernanceEngine`, `from governance import PolicyDecision`, `from governance import ExecutionMode`, `from governance import UserRole`, `from sandbox import ZeroTrustSandbox`, `from sandbox import SandboxResult`, `from task_state_machine import TaskStateMachine`, `from task_state_machine import Task`, `from task_state_machine import TaskStep`, `from task_state_machine import TaskStatus`, `from task_state_machine import TaskType`, `from session_manager import SessionManager`, `from session_manager import SessionContext`, `from project_kernel_runtime.cognition.llm_provider import LLMProvider`, `from project_kernel_runtime.cognition.llm_provider import LLMMessage`, `from project_kernel_runtime.cognition.llm_provider import LLMResponse`, `from rust_core import GACIEngine`, `from rust_core import PerformanceCache`, `from rust_core import ConcurrentExecutor`, `from swarm import AgentSwarm`, `from swarm import SwarmAgent`, `from orchestrator import Orchestrator`, `from orchestrator import get_orchestrator`, `from orchestrator import init_orchestrator`, `from project_kernel_runtime.protocols.mcp_server import MCPServer`, `from project_kernel_runtime.protocols.mcp_server import MCPTool`, `from project_kernel_runtime.protocols.mcp_server import MCPResource`, `from project_kernel_runtime.protocols.mcp_server import MCPSession`, `from observability import NeuralTracer`, `from observability import MetricsCollector`, `from observability import configure_logging`, `from observability import metrics`

> **Constants**: `__all__`=['RuntimeConfig', 'RuntimeProfile', 'ConfigWatcher', 'EventBus', 'AgentEvent', 'EventTypes', 'ToolExecutor', 'ToolCall', 'ToolResult', 'ExecutionContext', 'GovernanceEngine', 'PolicyDecision', 'ExecutionMode', 'UserRole', 'ZeroTrustSandbox', 'SandboxResult', 'TaskStateMachine', 'Task', 'TaskStep', 'TaskStatus', 'TaskType', 'SessionManager', 'SessionContext', 'LLMProvider', 'LLMMessage', 'LLMResponse', 'GACIEngine', 'PerformanceCache', 'ConcurrentExecutor', 'AgentSwarm', 'SwarmAgent', 'Orchestrator', 'get_orchestrator', 'init_orchestrator', 'MCPServer', 'MCPTool', 'MCPResource', 'MCPSession', 'NeuralTracer', 'MetricsCollector', 'configure_logging', 'metrics']

---

#### analytics.py *(94 lines)*

> **Imports**: `import time`, `from typing import Dict`, `from typing import Any`, `from typing import List`, `from typing import Optional`, `from dataclasses import dataclass`, `from dataclasses import field`, `from datetime import datetime`

> **Classes**:
  - **TaskMetric** (lines 13-19)
  - **AnalyticsService** – *Tracks and analyzes system performance metrics.* (lines 22-94)
    - `__init__(self)` (lines 25-27)
    - `start_task_tracking(self, task_id)` – *Initialize tracking for a new task.* (lines 29-31)
    - `record_step_timing(self, task_id, step_id, duration)` – *Record how long a specific step took.* (lines 33-36)
    - `end_task_tracking(self, task_id, success)` – *Finalize tracking for a task.* (lines 38-44)
    - `get_bottlenecks(self)` – *Identify slow steps across all tasks.* (lines 46-65)
    - `get_task_metrics(self)` – *Retrieve metrics for all tasks currently being tracked.* (lines 67-81)
    - `get_system_summary(self)` – *Overall system efficiency summary.* (lines 83-94)

---

#### credits_engine.py *(107 lines)*

> **Imports**: `import logging`, `import os`, `import sqlite3`, `import time`, `from typing import Any`, `from typing import Dict`, `from typing import Optional`

> **Constants**: `logger`=logging.getLogger(__name__), `credits_engine`=CreditsEngine()

> **Classes**:
  - **CreditsEngine** – *Per-tenant usage metering and billing.* (lines 20-103)
    - `__init__(self, db_path)` (lines 23-27)
    - `_init_db(self)` (lines 29-48)
    - `record_usage(self, tenant_id, usage_type, quantity)` – *Record a usage event.* (lines 50-59)
    - `get_usage(self, tenant_id, since)` – *Get usage totals for a tenant.* (lines 61-72)
    - `check_quota(self, tenant_id, usage_type)` – *Check if tenant is within quota.* (lines 74-91)
    - `set_quota(self, tenant_id, max_tool_calls, max_tokens, max_compute_sec)` (lines 93-99)
    - `get_report(self, tenant_id)` (lines 101-103)

---

#### evaluation.py *(82 lines)*

> **Imports**: `import time`, `import json`, `from typing import Dict`, `from typing import Any`, `from typing import List`, `from typing import Optional`, `from datetime import datetime`

> **Classes**:
  - **BenchmarkProfile** – *A set of tasks to evaluate an agent's success rate.* (lines 12-16)
    - `__init__(self, name, tasks)` (lines 14-16)
  - **EvaluationHarness** – *Benchmarks the kernel's agentic performance.* (lines 19-82)
    - `__init__(self, orchestrator)` (lines 22-24)
    - `get_report(self)` – *Calculate summary statistics for the benchmark.* (lines 65-77)
    - `save_to_file(self, path)` – *Persist results for historical comparison.* (lines 79-82)

---

#### event_bus.py *(270 lines)*

> **Imports**: `import asyncio`, `import logging`, `from collections import defaultdict`, `from dataclasses import dataclass`, `from dataclasses import field`, `from datetime import datetime`, `from datetime import timezone`, `from typing import Any`, `from typing import Callable`, `from typing import Coroutine`, `from typing import Dict`, `from typing import List`, `from typing import Optional`, `from uuid import uuid4`

> **Constants**: `logger`=logging.getLogger(__name__), `EventHandler`=Callable[[AgentEvent], Coroutine[Any, Any, None]]

> **Classes**:
  - **AgentEvent** – *Base event published through the event bus.* (lines 27-35)
  - **EventTypes** – *Known event types in the kernel.* (lines 39-111)
  - **EventBus** – *Asynchronous event bus for decoupled inter-subsystem communication.

Features:
- Typed event publish/subscribe
- Wildcard subscriptions (e.g., "task.*" matches all task events)
- Event replay from log for crash recovery
- Async handlers with error isolation
- Event log for auditing and debugging* (lines 121-270)
    - `__init__(self, max_log_size)` (lines 133-138)
    - `subscribe(self, event_type, handler)` – *Subscribe a handler to an event type.

Supports wildcards: "task.*" matches "task.created", "task.started", etc.
Use "*" to subscribe to all events.* (lines 140-148)
    - `unsubscribe(self, event_type, handler)` – *Remove a handler from an event type.* (lines 150-155)
    - `emit(self, event_type, payload, source, session_id, task_id)` – *Convenience method to create and return an event (does not publish).
Call `await bus.publish(event)` to dispatch.* (lines 190-203)
    - `replay(self, from_event_id, event_type, limit)` – *Replay events from the log for crash recovery or debugging.

Args:
    from_event_id: Start replaying from this event ID (exclusive)
    event_type: Filter by event type
    limit: Maximum number of events to return* (lines 213-238)
    - `get_event_log(self, last_n)` – *Get the last N events from the log.* (lines 240-242)
    - `subscriber_count(self)` – *Total number of active subscriptions.* (lines 245-247)
    - `_matches(pattern, event_type)` – *Check if event type matches a subscription pattern.* (lines 250-259)

---

#### export_service.py *(84 lines)*

> **Imports**: `import json`, `import os`, `from datetime import datetime`, `from typing import Dict`, `from typing import Any`, `from typing import List`, `from research import ResearchReport`, `from research import ResearchSession`, `from fpdf import FPDF`

> **Classes**:
  - **ExportService** – *Service to export research reports into MD, JSON, or PDF.* (lines 11-84)
    - `to_markdown(report, session)` – *Convert a report to a Markdown string.* (lines 15-35)
    - `to_json(report)` – *Convert a report to a JSON string.* (lines 38-40)
    - `to_pdf(report, session, output_path)` – *Export to PDF. 
Note: Requires fpdf2. If not installed, this will be a placeholder.* (lines 43-84)

---

#### governance.py *(509 lines)*

> **Imports**: `import asyncio`, `import json`, `import logging`, `import os`, `import sqlite3`, `from datetime import datetime`, `from datetime import timezone`, `from enum import Enum`, `from typing import Dict`, `from typing import List`, `from typing import Optional`, `from typing import Set`, `from uuid import uuid4`, `from urllib.parse import urlparse`

> **Constants**: `logger`=logging.getLogger(__name__)

> **Classes**:
  - **ExecutionMode** (lines 33-37)
  - **PolicyDecision** (lines 40-43)
  - **UserRole** (lines 46-50)
  - **AuditStore** – *SQLite-backed persistent audit trail.* (lines 118-206)
    - `__init__(self, db_path)` (lines 121-124)
    - `_init_db(self)` – *Create audit table if not exists.* (lines 126-150)
    - `log(self, event)` – *Append an audit event to the persistent log.* (lines 152-177)
    - `query(self, user_id, limit, since)` – *Query audit log entries.* (lines 179-206)
  - **GovernanceEngine** – *Production governance engine with real enforcement.

Features:
- RBAC with tool-level permission matrix
- Mode-based policy enforcement (plan/review/research/build)
- SQLite-backed audit trail with real timestamps
- Approval workflows for destructive operations
- Network allowlist enforcement
- .agentrules file support* (lines 213-509)
    - `__init__(self, policy_matrix, config)` (lines 226-247)
    - `check_tool_allowed(self, tool_name, mode, task_id, user_role)` – *Check if a tool is allowed in the given mode and role.

Real enforcement — not a stub. Returns DENY for unauthorized access.* (lines 249-320)
    - `check_permission(self, tool_name, user_role, execution_mode, mutability)` – *Unified permission check (used by ToolExecutor).

Checks:
1. Role has access to this tool
2. Mode allows this mutability level* (lines 322-354)
    - `requires_approval(self, tool_name)` – *Check if a tool requires human approval before execution.* (lines 356-358)
    - `check_network_access(self, url, allowlist)` – *Check if a URL is allowed by the network policy.* (lines 391-412)
    - `project_rules(self)` – *Get loaded project rules.* (lines 443-445)
    - `get_audit_log(self, user_id, limit)` – *Query the audit log.* (lines 477-479)
    - `_classify_tool(self, tool_name)` – *Classify tool by its mutability level.* (lines 483-485)
    - `_log_audit(self, tool_name, mode, decision, user_role, reason, task_id)` – *Log an audit event to SQLite.* (lines 487-509)

---

#### instance_manager.py *(52 lines)*

> **Imports**: `import psutil`, `import subprocess`, `import os`, `from typing import Optional`, `from typing import Dict`, `from typing import Any`, `from project_kernel_runtime.memory.state_hub import state_hub`

> **Constants**: `instance_manager`=InstanceManager()

> **Classes**:
  - **InstanceManager** – *Manages external application instances (Blender, Unity, Browsers) required for MCP tasks.* (lines 7-49)
    - `__init__(self)` (lines 11-16)
    - `is_app_running(self, app_key)` – *Check if a specific app is currently running on the host OS.* (lines 18-28)
    - `launch_app(self, app_key, custom_path)` – *Autonomously launch a registered application.* (lines 30-49)

---

#### mcp_bridge.py *(348 lines)*

> **Imports**: `import asyncio`, `import json`, `import logging`, `import os`, `import subprocess`, `import sys`, `from typing import Any`, `from typing import Dict`, `from typing import List`, `from typing import Optional`, `from project_kernel_runtime.protocols.mcp_client import MCPClient`

> **Constants**: `logger`=logging.getLogger(__name__), `REGISTRY_PATH`=os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'mcp_registry.json')

> **Classes**:
  - **MCPBridge** – *Manages the lifecycle of external MCP server connections.

Supports two transport types:
- stdio: Spawns a subprocess and communicates via stdin/stdout JSON-RPC
- websocket: Connects to a remote MCP server via WebSocket

All discovered tools are exposed to the Orchestrator for LLM tool-calling.* (lines 24-348)
    - `__init__(self)` (lines 35-38)
    - `get_all_external_tools(self)` – *Get all tool schemas from all connected MCP servers for LLM context injection.* (lines 264-281)
    - `get_status(self)` – *Get the current status of all MCP connections.* (lines 283-296)
    - `_read_registry(self)` – *Read the persistent MCP registry from disk.* (lines 326-335)

---

#### multi_tenancy.py *(87 lines)*

> **Imports**: `import logging`, `from typing import Any`, `from typing import Dict`, `from typing import List`, `from typing import Optional`, `from uuid import uuid4`

> **Constants**: `logger`=logging.getLogger(__name__), `tenancy_manager`=TenancyManager()

> **Classes**:
  - **Tenant** – *A tenant (organization/user) in the system.* (lines 17-32)
    - `__init__(self, tenant_id, name, api_key, plan, max_agents)` (lines 19-26)
    - `to_dict(self)` (lines 28-32)
  - **TenancyManager** – *Manages multi-tenant isolation.* (lines 35-83)
    - `__init__(self)` (lines 38-45)
    - `register_tenant(self, tenant_id, name, plan)` (lines 47-53)
    - `get_tenant(self, tenant_id)` (lines 55-56)
    - `identify_by_api_key(self, api_key)` – *Identify tenant from API key.* (lines 58-60)
    - `set_current_tenant(self, tenant_id)` (lines 62-63)
    - `get_current_tenant(self)` (lines 65-66)
    - `list_tenants(self)` (lines 68-69)
    - `check_resource_quota(self, tenant_id, resource)` – *Check if tenant can use a resource.* (lines 71-83)

---

#### observability.py *(189 lines)*

> **Imports**: `import json`, `import logging`, `import os`, `import time`, `import uuid`, `from contextvars import ContextVar`, `from typing import Any`, `from typing import Dict`, `from typing import List`, `from typing import Optional`, `import structlog`, `import structlog`, `from datetime import datetime`, `from datetime import timezone`

> **Constants**: `logger`=logging.getLogger(__name__), `metrics`=MetricsCollector()

> **Classes**:
  - **DecisionNode** – *A single step in an agent's reasoning path.* (lines 73-82)
    - `__init__(self, step_id, logic, parent_id)` (lines 75-82)
  - **NeuralTracer** – *Traces reasoning and decision-making causality.* (lines 85-134)
    - `__init__(self, session_id)` (lines 88-91)
    - `start_decision(self, logic, parent_id)` (lines 93-104)
    - `end_decision(self, node_id, result_summary, metadata)` (lines 106-111)
    - `get_full_trace(self)` (lines 113-124)
    - `save_trace(self, path)` (lines 126-134)
  - **MetricsCollector** – *Simple metrics collection for Prometheus-compatible export.* (lines 141-185)
    - `__init__(self)` (lines 144-147)
    - `inc(self, name, value, labels)` (lines 149-151)
    - `set(self, name, value, labels)` (lines 153-155)
    - `observe(self, name, value, labels)` (lines 157-164)
    - `export_prometheus(self)` – *Export metrics in Prometheus text format.* (lines 166-178)
    - `_key(name, labels)` (lines 181-185)

> **Functions**:
  - `configure_logging(log_level, json_output)` – *Configure structured logging for the runtime.* (lines 29-57)
  - `get_logger(name)` – *Get a structlog logger instance.* (lines 60-66)

---

#### orchestrator.py *(821 lines)*

> **Imports**: `import asyncio`, `import logging`, `from functools import cached_property`, `from typing import Dict`, `from typing import List`, `from typing import Optional`, `from typing import Any`, `from datetime import datetime`, `from datetime import timezone`, `from runtime import RuntimeConfig`, `from event_bus import EventBus`, `from governance import GovernanceEngine`, `from tool_executor import ToolExecutor`, `from universal_tools import get_all_tools`, `from sandbox import ZeroTrustSandbox`, `from task_state_machine import TaskStateMachine`, `from session_manager import SessionManager`, `from project_kernel_runtime.cognition.llm_provider import LLMProvider`, `from skills_registry import SkillRegistry`, `from swarm import AgentSwarm`, `from rust_core import GACIEngine`, `from analytics import AnalyticsService`, `from project_kernel_runtime.protocols.mcp_client import MCPClient`, `from planner import MissionPlanner`, `from observability import NeuralTracer`, `from project_kernel_runtime.agents.watchdog import WatchdogAgent`, `from project_kernel_runtime.agents.sre_swarm import SREMonitor`, `from project_kernel_runtime.protocols.mesh_p2p import GlobalMeshP2P`, `from project_kernel_runtime.protocols.federated_hub import FederatedHub`, `from project_kernel_runtime.cognition.self_attention import SelfAttentionLoop`, `from skill_compiler import SkillCompiler`, `from mcp_bridge import MCPBridge`, `from predictive import PredictiveEngine`, `from credits_engine import credits_engine`, `from multi_tenancy import tenancy_manager`, `from export_service import ExportService`, `from export_service import ExportService`, `from project_kernel_runtime.cognition.llm_provider import LLMMessage`, `from task_state_machine import TaskType`, `from task_state_machine import TaskStep`, `from universal_tools import get_all_tools`, `from task_state_machine import TaskStep`, `from tool_executor import ToolCall`, `from tool_executor import ExecutionContext`, `from research import ResearchSession`, `from research import Source`, `import urllib.request`, `from research import ResearchReport`, `from project_kernel_runtime.cognition.llm_provider import summarize_text`, `from export_service import ExportService`, `from project_kernel_runtime.protocols.mcp_server import MCPTool`, `from project_kernel_runtime.agents.growth_swarm.gtm_swarm_controller import gtm_swarm`, `import json`, `from tool_executor import ToolCall`, `from tool_executor import ExecutionContext`

> **Constants**: `logger`=logging.getLogger(__name__)

> **Classes**:
  - **Orchestrator** – *Main coordination engine — Coordinator pattern.

Subsystems are lazily initialized via @cached_property.
All communication goes through EventBus.
All tool execution goes through ToolExecutor pipeline.* (lines 25-799)
    - `__init__(self, config_path)` (lines 34-46)
    - `event_bus(self)` (lines 53-57)
    - `governance(self)` (lines 60-64)
    - `tool_executor(self)` (lines 67-78)
    - `sandbox(self)` (lines 81-86)
    - `tasks(self)` (lines 89-93)
    - `sessions(self)` (lines 96-100)
    - `llm(self)` (lines 103-109)
    - `skills(self)` (lines 112-116)
    - `swarm(self)` (lines 119-123)
    - `performance_core(self)` (lines 126-130)
    - `analytics(self)` (lines 133-137)
    - `mcp_client(self)` (lines 140-146)
    - `planner(self)` (lines 149-153)
    - `observability(self)` (lines 156-160)
    - `watchdog(self)` (lines 163-167)
    - `sre(self)` (lines 170-174)
    - `mesh_p2p(self)` (lines 177-181)
    - `federated(self)` (lines 184-188)
    - `self_attention(self)` (lines 191-195)
    - `skill_compiler(self)` (lines 198-202)
    - `mcp_bridge(self)` (lines 205-209)
    - `predictive(self)` (lines 212-216)
    - `credits(self)` (lines 219-221)
    - `tenancy(self)` (lines 224-226)
    - `export_service(self)` (lines 229-231)
    - `export_service(self)` (lines 234-236)
    - `_build_system_prompt(self)` – *Build system prompt with project context.* (lines 453-460)
    - `_get_tool_schemas(self)` – *Get tool schemas for LLM function calling, including external MCP tools.* (lines 462-487)
    - `register_mcp_tools(self, mcp_server)` – *Register orchestrator tools with MCP server.* (lines 768-789)

> **Functions**:
  - `get_orchestrator()` (lines 809-813)

---

#### parameter_registry.py *(371 lines)*

> **Imports**: `import asyncio`, `import logging`, `import os`, `import yaml`, `import json`, `from typing import Any`, `from typing import Callable`, `from typing import Dict`, `from typing import List`, `from typing import Optional`, `from typing import Set`, `from dataclasses import dataclass`, `from dataclasses import field`, `from datetime import datetime`, `from datetime import timezone`, `from uuid import uuid4`, `from ui_schema import UISchemaGenerator`, `from ui_schema import UIParameter`, `from ui_schema import generate_ui_schema`, `from ui_schema import UIParameter`, `from ui_schema import ParameterTypeInferrer`

> **Constants**: `logger`=logging.getLogger(__name__), `ParamChangeCallback`=Callable[[str, Any, Any], None], `ParamValidator`=Callable[[str, Any], bool]

> **Classes**:
  - **ParameterChange** – *Record of a parameter change.* (lines 34-40)
  - **ParameterValidator** – *Validates parameter values.* (lines 43-78)
    - `register(cls, param_id, validator)` (lines 49-50)
    - `validate(cls, param_id, value)` (lines 53-67)
    - `get_validation_error(cls, param_id, value)` – *Get validation error message if invalid.* (lines 70-78)
  - **ParameterRegistry** – *Centralized registry for all system parameters.

Features:
- Get/set with validation
- Change callbacks
- Hot-reload support
- Persistence to YAML/JSON
- Event emission* (lines 81-345)
    - `__init__(self, config_path)` (lines 93-108)
    - `_register_default_validators(self)` – *Register default parameter validators.* (lines 110-121)
    - `_load_config(self)` – *Load configuration from YAML file.* (lines 123-132)
    - `_load_schema(self)` – *Load parameter schema.* (lines 134-137)
    - `get(self, param_id, default)` – *Get parameter value.* (lines 139-151)
    - `set(self, param_id, value, source)` – *Set parameter value with validation.

Returns:
    (success: bool, error_message: Optional[str])* (lines 153-182)
    - `_add_parameter(self, param_id, value)` – *Add a new parameter dynamically.* (lines 184-197)
    - `_record_change(self, param_id, old_value, new_value, source)` – *Record parameter change in history.* (lines 199-210)
    - `_notify_callbacks(self, param_id, old_value, new_value)` – *Notify all registered callbacks.* (lines 212-225)
    - `subscribe(self, param_id, callback)` – *Subscribe to parameter changes.* (lines 227-231)
    - `unsubscribe(self, param_id, callback)` – *Unsubscribe from parameter changes.* (lines 233-238)
    - `subscribe_global(self, callback)` – *Subscribe to all parameter changes.* (lines 240-242)
    - `unsubscribe_global(self, callback)` – *Unsubscribe from all parameter changes.* (lines 244-247)
    - `get_schema(self)` – *Get UI schema for dynamic rendering.* (lines 249-256)
    - `get_all_params(self)` – *Get all parameters as flat dictionary.* (lines 258-260)
    - `get_change_history(self, limit)` – *Get parameter change history.* (lines 262-274)
    - `search_params(self, query)` – *Search parameters by label or ID.* (lines 276-291)
    - `get_by_category(self, category)` – *Get all parameters in a category.* (lines 293-299)
    - `get_categories(self)` – *Get all categories with parameter counts.* (lines 301-310)
    - `_save_config_nolock(self)` – *Save config without locking.* (lines 322-339)
    - `reload(self)` – *Reload configuration from file.* (lines 341-345)

> **Functions**:
  - `get_registry(config_path)` – *Get global parameter registry instance.* (lines 351-356)
  - `get_param(param_id, default)` – *Convenience function to get parameter.* (lines 359-361)
  - `set_param(param_id, value, source)` – *Convenience function to set parameter.* (lines 364-366)

---

#### planner.py *(78 lines)*

> **Imports**: `import os`, `from datetime import datetime`, `from typing import List`, `from typing import Dict`, `from typing import Any`, `import asyncio`

> **Classes**:
  - **MissionPlanner** – *Handles high-level architectural planning before execution.
Inspired by OpenHands PLAN.md and Cursor's reasoning loop.* (lines 10-72)
    - `__init__(self, workspace_path)` (lines 15-17)
    - `_build_plan_template(self, task_id, description, mesh_context)` (lines 33-72)

---

#### predictive.py *(69 lines)*

> **Imports**: `import logging`, `from collections import Counter`, `from collections import defaultdict`, `from typing import Any`, `from typing import Dict`, `from typing import List`

> **Constants**: `logger`=logging.getLogger(__name__)

> **Classes**:
  - **PredictiveEngine** – *Predicts next useful actions based on task history.* (lines 17-69)
    - `__init__(self)` (lines 20-24)
    - `record_action(self, tool_name, context, file_ext)` – *Record a tool action for pattern learning.* (lines 26-38)
    - `predict_next_tool(self, current_tool, file_ext)` – *Predict next useful tools.* (lines 40-62)
    - `get_stats(self)` (lines 64-69)

---

#### research.py *(45 lines)*

> **Imports**: `from pydantic import BaseModel`, `from pydantic import Field`, `from typing import List`, `from typing import Dict`, `from typing import Optional`, `from typing import Any`, `from datetime import datetime`, `import asyncio`, `import requests`

> **Classes**:
  - **Source** (lines 8-15)
  - **ResearchReport** (lines 18-25)
  - **ResearchSession** (lines 28-38)

> **Functions**:
  - `simple_summarize(text, max_chars)` – *Basic text summarizer fallback.* (lines 42-45)

---

#### runtime.py *(444 lines)*

> **Imports**: `from pydantic import BaseModel`, `from pydantic import Field`, `from typing import List`, `from typing import Dict`, `from typing import Optional`, `from typing import Literal`, `from typing import Any`, `from typing import Set`, `from enum import Enum`, `import yaml`, `import os`, `import logging`, `from pathlib import Path`, `from datetime import datetime`, `from watchfiles import awatch`

> **Constants**: `logger`=logging.getLogger(__name__)

> **Classes**:
  - **GovernancePolicyMode** – *Permission set for a specific execution mode.* (lines 30-35)
  - **GovernanceConfig** – *Governance and security policy configuration.* (lines 38-63)
  - **MCPConfig** – *MCP (Model Context Protocol) server/client configuration.* (lines 66-80)
  - **SandboxConfig** – *Sandbox and execution isolation configuration.* (lines 83-94)
  - **LLMProviderConfig** – *Configuration for a single LLM provider.* (lines 97-106)
  - **LLMConfig** – *LLM provider system configuration.* (lines 109-139)
  - **VectorDBConfig** – *Vector database / agent memory configuration.* (lines 142-151)
  - **A2AConfig** – *Google A2A (Agent-to-Agent) protocol configuration.* (lines 154-162)
  - **ObservabilityConfig** – *Observability, logging, and monitoring configuration.* (lines 165-173)
  - **SkillsConfig** – *Skills registry configuration.* (lines 176-188)
  - **FeaturesConfig** – *Feature flags for optional subsystems.* (lines 191-203)
  - **ServerConfig** – *HTTP server configuration.* (lines 206-214)
  - **RuntimeConfig** – *Root configuration model for the Antigravity Project Kernel Runtime.

Supports layered loading: YAML file → environment variables → CLI args.
All subsections are validated Pydantic models with sensible defaults.* (lines 221-386)
    - `from_yaml(cls, path)` – *Load configuration from YAML file with fallback to defaults.* (lines 254-280)
    - `from_env(cls)` – *Load from environment variables overlaid on YAML config.

Environment variables follow the pattern:
    PKR_<SECTION>_<KEY>=value

Examples:
    PKR_MODE=production
    PKR_SERVER_PORT=9000
    PKR_SANDBOX_BACKEND=docker
    PKR_LLM_ACTIVE_MODEL=claude-sonnet-4-20250514
    PKR_OBSERVABILITY_LOG_LEVEL=DEBUG* (lines 283-316)
    - `_migrate_v1_to_v2(cls, data)` – *Migrate v1 YAML config to v2 schema.* (lines 319-345)
    - `_parse_env_value(value)` – *Parse environment variable values into appropriate Python types.* (lines 348-369)
    - `save_yaml(self, path)` – *Save current config to YAML file.* (lines 371-375)
    - `ensure_data_dirs(self)` – *Create required data directories.* (lines 377-386)
  - **RuntimeProfile** – *Backward-compatible alias for RuntimeConfig.

Existing code that imports RuntimeProfile will continue to work.
New code should use RuntimeConfig directly.* (lines 393-400)
  - **ConfigWatcher** – *Watches runtime.yaml for changes and triggers reload callback.

Usage:
    watcher = ConfigWatcher("runtime.yaml", on_config_change)
    await watcher.start()* (lines 407-444)
    - `__init__(self, config_path, callback)` (lines 416-419)
    - `stop(self)` – *Stop watching.* (lines 442-444)

---

#### rust_core.py *(232 lines)*

> **Imports**: `import asyncio`, `import logging`, `import time`, `from concurrent.futures import ProcessPoolExecutor`, `from typing import Any`, `from typing import Callable`, `from typing import Dict`, `from typing import List`, `from typing import Optional`, `from functools import lru_cache`

> **Constants**: `logger`=logging.getLogger(__name__), `RustMemoryCache`=PerformanceCache, `RustToolExecutor`=ConcurrentExecutor

> **Classes**:
  - **PerformanceCache** – *Real high-performance cache with TTL expiry and LRU eviction.

Replaces the mock RustMemoryCache that did nothing useful.
Uses a dict-based approach with timestamp tracking for TTL.* (lines 30-110)
    - `__init__(self, max_size, ttl)` (lines 38-45)
    - `_evict_oldest(self)` – *Remove the least recently accessed entry.* (lines 92-97)
    - `stats(self)` – *Cache statistics.* (lines 100-110)
  - **ConcurrentExecutor** – *Bounded concurrent task executor using asyncio.Semaphore.

Replaces the mock RustToolExecutor that used asyncio.sleep(0.05).
Handles real concurrent I/O operations with backpressure.* (lines 117-179)
    - `__init__(self, max_workers)` (lines 125-132)
    - `shutdown(self)` – *Shutdown the process pool.* (lines 165-169)
    - `stats(self)` – *Executor statistics.* (lines 172-179)
  - **GACIEngine** – *General Artificial Coding Intelligence Orchestrator.

High-performance Python implementation combining:
- Real TTL cache for context management
- Bounded concurrent execution for tool parallelism
- Process pool for CPU-bound operations

Note: The original aspirational description was "Rust Hyper-Core Substrate."
This is honest Python — fast, real, and production-ready.* (lines 186-223)
    - `__init__(self, max_cache_size, max_workers)` (lines 199-202)
    - `stats(self)` – *Combined performance statistics.* (lines 214-219)
    - `shutdown(self)` – *Clean shutdown.* (lines 221-223)

---

#### sandbox.py *(464 lines)*

> **Imports**: `import asyncio`, `import logging`, `import os`, `import platform`, `import shlex`, `import tempfile`, `from dataclasses import dataclass`, `from dataclasses import field`, `from datetime import datetime`, `from datetime import timezone`, `from typing import Any`, `from typing import Dict`, `from typing import List`, `from typing import Optional`, `from uuid import uuid4`, `import time`, `import time`, `import time`, `from e2b_code_interpreter import Sandbox`, `import shutil`, `from urllib.parse import urlparse`

> **Constants**: `logger`=logging.getLogger(__name__)

> **Classes**:
  - **SandboxResult** – *Result from sandbox execution.* (lines 36-43)
  - **SandboxInstance** – *Tracks an active sandbox.* (lines 47-56)
  - **SubprocessSandbox** – *Subprocess-based sandbox using asyncio.

Works on any OS without Docker. Provides basic isolation via:
- Separate subprocess (not in-process)
- Timeout enforcement
- Working directory restriction
- Environment variable isolation
- Output capture and truncation* (lines 63-145)
  - **DockerSandbox** – *Docker container-based sandbox for production isolation.

Features:
- Full container isolation
- Read-only filesystem with tmpfs scratch
- Network mode: none (default), allowlist, or full
- CPU and memory limits
- Auto cleanup* (lines 148-248)
    - `__init__(self, image)` (lines 160-162)
  - **E2BSandbox** – *E2B (Execute to Build) cloud sandbox using Firecracker MicroVMs.

Requires E2B API key. Each execution runs in an isolated MicroVM
with ~150ms cold start.* (lines 251-289)
  - **ZeroTrustSandbox** – *Unified sandbox manager with pluggable backends.

Upgraded from 50-line mock to real multi-backend isolation.
Backward-compatible class name for existing code.* (lines 296-464)
    - `__init__(self, config)` (lines 304-328)
    - `_create_backend(self, name)` – *Create the sandbox backend.* (lines 330-342)
    - `provision_sandbox(self, task_id)` – *Provision an isolated execution environment.* (lines 344-362)
    - `request_network_access(self, sandbox_id, endpoint)` – *Check if a sandbox is allowed to access a network endpoint.* (lines 401-420)
    - `teardown_sandbox(self, sandbox_id)` – *Remove and clean up a sandbox.* (lines 422-433)
    - `calculate_security_score(self)` – *Calculate real-time security score based on isolation posture.* (lines 435-464)

---

#### session_manager.py *(328 lines)*

> **Imports**: `from typing import Dict`, `from typing import List`, `from typing import Optional`, `from typing import Any`, `from datetime import datetime`, `from datetime import timezone`, `import json`, `import os`, `import sqlite3`, `import uuid`, `import logging`

> **Constants**: `logger`=logging.getLogger(__name__)

> **Classes**:
  - **SessionContext** – *User session with workspace state.* (lines 25-123)
    - `__init__(self, session_id, user_id, workspace_path, mode, context)` (lines 27-46)
    - `update_activity(self)` (lines 48-49)
    - `add_task(self, task_id)` (lines 51-54)
    - `add_file(self, file_path)` (lines 56-61)
    - `add_command(self, command)` (lines 63-66)
    - `add_message(self, role, content)` – *Add a conversation message to session memory.* (lines 68-77)
    - `get_recent_files(self, limit)` (lines 79-80)
    - `get_recent_tasks(self, limit)` (lines 82-83)
    - `get_conversation_context(self, last_n)` – *Get recent conversation for LLM context building.* (lines 85-87)
    - `to_dict(self)` (lines 89-103)
    - `from_dict(cls, data)` (lines 106-123)
  - **SessionManager** – *Manages user sessions with SQLite persistence.

Upgraded from JSON files to SQLite for:
- ACID transactions
- Fast queries
- Concurrent access support* (lines 126-328)
    - `__init__(self, storage_path, event_bus)` (lines 136-145)
    - `_init_db(self)` – *Create SQLite tables.* (lines 147-163)
    - `create_session(self, user_id, workspace_path, mode, context)` (lines 165-191)
    - `get_session(self, session_id)` (lines 193-194)
    - `get_active_session(self, user_id)` (lines 196-200)
    - `update_session_activity(self, session_id)` (lines 202-206)
    - `add_task_to_session(self, session_id, task_id)` (lines 208-212)
    - `add_file_to_session(self, session_id, file_path)` (lines 214-218)
    - `add_command_to_session(self, session_id, command)` (lines 220-224)
    - `add_message_to_session(self, session_id, role, content)` – *Add conversation message for context tracking.* (lines 226-231)
    - `end_session(self, session_id)` (lines 233-241)
    - `list_user_sessions(self, user_id)` (lines 243-244)
    - `cleanup_old_sessions(self, days)` (lines 246-259)
    - `_save_to_db(self, session)` (lines 263-277)
    - `load_sessions(self)` (lines 279-293)
    - `_delete_from_db(self, session_id)` (lines 295-300)
    - `_migrate_from_json(self, json_dir)` – *Migrate legacy JSON file sessions to SQLite.* (lines 302-321)
    - `save_session(self, session)` (lines 324-325)
    - `delete_session_file(self, session_id)` (lines 327-328)

---

#### skill_compiler.py *(80 lines)*

> **Imports**: `import logging`, `from collections import Counter`, `from typing import Any`, `from typing import Dict`, `from typing import List`

> **Constants**: `logger`=logging.getLogger(__name__)

> **Classes**:
  - **LearnedSkill** – *A reusable pattern extracted from task history.* (lines 17-30)
    - `__init__(self, name, tool_sequence, domain, success_count)` (lines 19-24)
    - `to_dict(self)` (lines 26-30)
  - **SkillCompiler** – *Extracts and stores reusable task patterns.* (lines 33-80)
    - `__init__(self)` (lines 36-39)
    - `analyze_session(self, task_id, domain, tool_sequence)` – *Analyze a completed task for reusable patterns.* (lines 41-57)
    - `suggest_tools(self, domain, context)` – *Suggest tools based on learned patterns.* (lines 59-67)
    - `get_skills(self, domain)` (lines 69-73)
    - `get_stats(self)` (lines 75-80)

---

#### skills_registry.py *(158 lines)*

> **Imports**: `from enum import Enum`, `from typing import List`, `from typing import Dict`, `from typing import Optional`

> **Constants**: `CORE_SKILLS`=[Skill(name='file_operations', description='Read/write files with AST parsing', tools=['read_file', 'write_file', 'search_files', 'list_directory'], level=SkillLevel.WRITE, pack='core'), Skill(name='terminal_execution', description='Execute shell commands with error capture', tools=['shell_exec', 'run_test', 'run_lint'], level=SkillLevel.EXECUTE, pack='core'), Skill(name='git_operations', description='Git commit, branch, diff', tools=['git_commit', 'git_branch', 'git_diff'], level=SkillLevel.WRITE, pack='core'), Skill(name='lsp_integration', description='Symbol search via Language Server', tools=['goto_definition', 'find_references', 'rename_symbol'], level=SkillLevel.READ_ONLY, pack='core'), Skill(name='error_recovery', description='Automatic linting & syntax fixing', tools=['run_linter', 'auto_fix_syntax'], level=SkillLevel.EXECUTE, pack='core'), Skill(name='browser_automation', description='Screenshot, navigation, visual bug fixes', tools=['screenshot', 'navigate_url', 'click_element'], level=SkillLevel.AUTONOMOUS, pack='core'), Skill(name='custom_tools', description='Extensible via MCP resources', tools=['register_tool', 'invoke_custom_tool'], level=SkillLevel.AUTONOMOUS, pack='core')], `BLENDER_PACK_SKILLS`=[Skill(name='blender_geometry', description='Geometry nodes, modifiers', tools=['geometry_nodes_script', 'apply_modifier'], level=SkillLevel.EXECUTE, pack='blender'), Skill(name='blender_animation', description='Keyframes, armature, cloth sim', tools=['keyframe_add', 'bake_simulation'], level=SkillLevel.EXECUTE, pack='blender')], `CODING_PACK_SKILLS`=[Skill(name='testing', description='Unit tests, integration tests', tools=['run_pytest', 'run_jest', 'coverage'], level=SkillLevel.EXECUTE, pack='coding'), Skill(name='debugging', description='Breakpoints, memory profiling', tools=['set_breakpoint', 'profile_memory'], level=SkillLevel.EXECUTE, pack='coding')]

> **Classes**:
  - **SkillLevel** (lines 10-14)
  - **Skill** – *Represents a skill with tools and permission level* (lines 16-30)
    - `__init__(self, name, description, tools, level, pack)` (lines 18-30)
  - **SkillRegistry** – *Registry of all available skills* (lines 120-158)
    - `__init__(self)` (lines 123-125)
    - `load_defaults(self)` – *Load core 7 skills + optional packs* (lines 127-130)
    - `get_skill(self, name)` – *Get skill by name* (lines 132-134)
    - `list_skills(self, pack)` – *List skills in a pack* (lines 136-138)
    - `get_tools_for_skill(self, skill_name)` – *Get MCP tool names for a skill* (lines 140-143)
    - `get_skill_by_tool(self, tool_name)` – *Get skill that contains a specific tool* (lines 145-150)
    - `to_mcp_tools(self, pack)` – *Convert skills to MCP tool names* (lines 152-158)

---

#### swarm.py *(332 lines)*

> **Imports**: `import asyncio`, `import logging`, `from dataclasses import dataclass`, `from dataclasses import field`, `from datetime import datetime`, `from datetime import timezone`, `from enum import Enum`, `from typing import Any`, `from typing import Callable`, `from typing import Dict`, `from typing import List`, `from typing import Optional`, `from uuid import uuid4`, `import time`

> **Constants**: `logger`=logging.getLogger(__name__), `DEFAULT_AGENTS`=[SwarmAgent(name='Architect', role=AgentRole.ARCHITECT, capabilities=['read_file', 'search_files', 'list_directory', 'web_search']), SwarmAgent(name='Coder', role=AgentRole.CODER, capabilities=['read_file', 'write_file', 'edit_file', 'bash_execute', 'search_files']), SwarmAgent(name='Reviewer', role=AgentRole.REVIEWER, capabilities=['read_file', 'search_files', 'git_diff', 'git_status']), SwarmAgent(name='Tester', role=AgentRole.TESTER, capabilities=['read_file', 'write_file', 'bash_execute', 'search_files']), SwarmAgent(name='Researcher', role=AgentRole.RESEARCHER, capabilities=['web_search', 'web_fetch', 'read_file'])]

> **Classes**:
  - **AgentRole** – *Specialized agent roles within a swarm.* (lines 29-35)
  - **SwarmAgent** – *A specialized agent within the swarm.* (lines 39-54)
    - `to_dict(self)` (lines 47-54)
  - **SubTask** – *A subtask assigned to a specific agent.* (lines 58-67)
  - **SwarmResult** – *Aggregated result from swarm execution.* (lines 71-79)
  - **AgentSwarm** – *Multi-agent coordination with real task decomposition and parallel execution.

Upgraded from hardcoded agents + string matching to:
- Typed specialized agents per role
- Task decomposition (rule-based now, LLM-injectable)
- Parallel execution of independent subtasks
- Result aggregation* (lines 119-332)
    - `__init__(self, swarm_id, llm_provider, event_bus)` (lines 130-137)
    - `_find_best_agent(self, subtask)` – *Find the best idle agent for a subtask.* (lines 296-315)
    - `get_swarm_status(self)` – *Return status of all agents.* (lines 317-319)
    - `get_history(self)` – *Return task execution history.* (lines 321-332)

---

#### task_state_machine.py *(458 lines)*

> **Imports**: `from enum import Enum`, `from typing import Dict`, `from typing import List`, `from typing import Optional`, `from typing import Any`, `from datetime import datetime`, `from datetime import timezone`, `import json`, `import os`, `import sqlite3`, `import logging`, `from uuid import uuid4`, `import time`

> **Constants**: `logger`=logging.getLogger(__name__)

> **Classes**:
  - **TaskStatus** (lines 26-33)
  - **TaskType** (lines 36-44)
  - **TaskStep** – *Individual step in a task with retry support.* (lines 47-103)
    - `__init__(self, id, description, tools, status, result, error, max_retries)` (lines 49-69)
    - `to_dict(self)` (lines 71-84)
    - `from_dict(cls, data)` (lines 87-103)
  - **Task** – *Durable task with state persistence.* (lines 106-206)
    - `__init__(self, id, type, description, steps, status, context, session_id)` (lines 108-129)
    - `get_current_step(self)` (lines 131-134)
    - `advance_step(self)` (lines 136-139)
    - `complete_step(self, result)` (lines 141-146)
    - `fail_step(self, error)` (lines 148-163)
    - `progress(self)` – *Task completion percentage.* (lines 166-171)
    - `to_dict(self)` (lines 173-188)
    - `from_dict(cls, data)` (lines 191-206)
  - **TaskStateMachine** – *Manages task execution with SQLite persistence.

Upgraded from JSON file storage to SQLite for:
- ACID transactions (crash-safe)
- Fast queries by status, session, type
- No file-per-task overhead
- Concurrent access support* (lines 209-458)
    - `__init__(self, storage_path, event_bus)` (lines 220-228)
    - `_init_db(self)` – *Create SQLite tables if not exists.* (lines 230-250)
    - `create_task(self, type, description, steps, context, session_id)` – *Create a new task with SQLite persistence.* (lines 252-267)
    - `get_task(self, task_id)` (lines 269-270)
    - `execute_task(self, task_id)` – *Synchronous task execution (backward compatible).* (lines 324-351)
    - `pause_task(self, task_id)` (lines 353-357)
    - `resume_task(self, task_id)` (lines 359-363)
    - `cancel_task(self, task_id)` (lines 365-369)
    - `list_tasks(self, status, session_id)` (lines 371-378)
    - `_save_to_db(self, task)` – *Persist task to SQLite.* (lines 382-399)
    - `load_tasks(self)` – *Load all tasks from SQLite.* (lines 401-419)
    - `_migrate_from_json(self, json_dir)` – *Migrate from legacy JSON file storage to SQLite.* (lines 421-437)
    - `save_task(self, task)` (lines 440-441)
    - `execute_step(self, step)` – *Legacy synchronous step executor (placeholder for orchestrator).* (lines 443-445)

---

#### tool_executor.py *(290 lines)*

> **Imports**: `import asyncio`, `import logging`, `from dataclasses import dataclass`, `from dataclasses import field`, `from datetime import datetime`, `from datetime import timezone`, `from typing import Any`, `from typing import Dict`, `from typing import List`, `from typing import Optional`, `from uuid import uuid4`, `from enum import Enum`, `import time`, `from event_bus import AgentEvent`

> **Constants**: `logger`=logging.getLogger(__name__)

> **Classes**:
  - **ToolMutability** – *How a tool modifies the environment.* (lines 28-33)
  - **ToolCall** – *A request to execute a tool.* (lines 37-48)
  - **ToolResult** – *Result of a tool execution.* (lines 52-61)
  - **PolicyDecision** – *Governance decision for a tool call.* (lines 64-68)
  - **ExecutionContext** – *Context for tool execution.* (lines 72-80)
  - **ToolExecutor** – *Central pipeline for all tool execution.

Every tool call goes through:
1. Governance gate — check if the tool is allowed
2. Sandbox routing — run in sandbox if required
3. Execution — call the actual tool
4. Audit + Event — log and publish result* (lines 87-290)
    - `__init__(self, governance, sandbox, event_bus, mcp_client)` (lines 98-104)
    - `register_tool(self, tool)` – *Register a tool implementation.* (lines 106-109)
    - `register_tools(self, tools)` – *Register multiple tool implementations.* (lines 111-114)
    - `get_tool(self, name)` – *Get a registered tool by name.* (lines 116-118)
    - `list_tools(self)` – *List all registered tools with their schemas.* (lines 120-131)

---

#### ui_schema.py *(373 lines)*

> **Imports**: `import yaml`, `import re`, `import os`, `import logging`, `from typing import Any`, `from typing import Dict`, `from typing import List`, `from typing import Optional`, `from typing import Callable`, `from dataclasses import dataclass`, `from dataclasses import field`, `from pathlib import Path`, `from pydantic import BaseModel`, `from pydantic import Field`, `from enum import Enum`, `import json`, `from datetime import datetime`, `from datetime import timezone`

> **Constants**: `logger`=logging.getLogger(__name__)

> **Classes**:
  - **UIParameter** – *A single tunable parameter exposed to the UI.* (lines 29-45)
  - **UICategory** – *A category of related parameters.* (lines 49-56)
  - **UISchema** – *Complete UI schema for dynamic rendering.* (lines 60-100)
    - `to_dict(self)` (lines 67-100)
  - **ParameterTypeInferrer** – *Infers UI parameter types from Python types and values.* (lines 103-206)
    - `infer_type(cls, value, field_name)` – *Infer UI parameter type from value.* (lines 166-186)
    - `infer_category(cls, param_id)` – *Infer category from parameter ID.* (lines 189-196)
    - `get_label(cls, param_id)` – *Get human-readable label for parameter.* (lines 199-201)
    - `get_metadata(cls, param_id)` – *Get metadata (min, max, step) for parameter.* (lines 204-206)
  - **UISchemaGenerator** – *Generates UI schema from runtime configuration and code.* (lines 209-361)
    - `__init__(self, config_path)` (lines 226-229)
    - `load_config(self)` – *Load runtime.yaml configuration.* (lines 231-236)
    - `generate(self)` – *Generate complete UI schema from configuration.* (lines 238-256)
    - `_parse_yaml_config(self, config, prefix)` – *Recursively parse YAML config into parameters.* (lines 258-269)
    - `_add_parameter(self, param_id, value)` – *Add a single parameter to the schema.* (lines 271-296)
    - `_add_hardcoded_parameters(self)` – *Add commonly used hardcoded parameters not in config.* (lines 298-316)
    - `_build_categories(self)` – *Build categorized parameter list.* (lines 318-340)
    - `_get_timestamp(self)` – *Get current ISO timestamp.* (lines 342-345)
    - `get_parameter(self, param_id)` – *Get a specific parameter.* (lines 347-349)
    - `update_parameter_value(self, param_id, value)` – *Update a parameter's current value.* (lines 351-356)
    - `get_parameter_value(self, param_id)` – *Get a parameter's current value.* (lines 358-361)

> **Functions**:
  - `generate_ui_schema(config_path)` – *Convenience function to generate UI schema.* (lines 364-367)

---

#### universal_tools.py *(865 lines)*

> **Imports**: `from abc import ABC`, `from abc import abstractmethod`, `from dataclasses import dataclass`, `from enum import Enum`, `from pathlib import Path`, `from typing import Any`, `from typing import Dict`, `from typing import Any`, `from typing import Dict`, `from typing import Optional`, `import asyncio`, `import logging`, `import os`, `import platform`, `import re`, `import shlex`, `import httpx`, `import httpx`

> **Constants**: `logger`=logging.getLogger(__name__), `logger`=logging.getLogger(__name__), `logger`=logging.getLogger(__name__), `logger`=logging.getLogger(__name__)

> **Classes**:
  - **ToolMutability** – *How a tool modifies the environment.* (lines 27-32)
  - **ToolResult** – *Standard result from tool execution.* (lines 36-40)
  - **BaseTool** – *Abstract base class for all kernel tools.

Subclasses must define:
- name: unique identifier (e.g., "read_file")
- description: what the tool does
- input_schema: JSON Schema for arguments
- execute(): the actual implementation* (lines 43-71)
    - `to_schema(self)` – *Export tool definition for MCP/LLM function calling.* (lines 65-71)
  - **ReadFileTool** – *Read the contents of a file with optional line range.* (lines 86-148)
  - **WriteFileTool** – *Write content to a file, creating directories as needed.* (lines 151-195)
  - **EditFileTool** – *Search-and-replace editing within a file.* (lines 198-245)
  - **SearchFilesTool** – *Search for text patterns across files using ripgrep-style matching.* (lines 248-318)
    - `_glob_match(filename, pattern)` – *Simple glob matching for file extensions.* (lines 314-318)
  - **ListDirectoryTool** – *List contents of a directory.* (lines 321-387)
    - `_list_dir(self, dir_path, entries, recursive, max_depth, current_depth, base_path)` – *Recursively list directory contents.* (lines 358-387)
  - **GitStatusTool** – *Show the working tree status.* (lines 436-458)
  - **GitDiffTool** – *Show changes in the working tree.* (lines 461-496)
  - **GitCommitTool** – *Commit staged changes with a message.* (lines 499-543)
  - **GitLogTool** – *Show commit history.* (lines 546-573)
  - **BashExecuteTool** – *Execute shell commands with timeout and output capture.* (lines 590-686)
  - **WebSearchTool** – *Search the web using DuckDuckGo Lite (no API key required).* (lines 701-766)
  - **WebFetchTool** – *Fetch content from a URL and convert to text.* (lines 769-846)
    - `_html_to_text(html)` – *Basic HTML to text conversion.* (lines 827-846)

> **Functions**:
  - `_resolve_cwd(arguments, context)` – *Resolve working directory from arguments or context.* (lines 428-433)
  - `get_all_tools()` – *Return instances of all core tools.* (lines 850-865)

---

#### wasm_driver.py *(82 lines)*

> **Imports**: `import asyncio`, `import logging`, `from typing import Any`, `from typing import Dict`, `import wasmtime`, `import wasmtime`

> **Constants**: `logger`=logging.getLogger(__name__)

> **Classes**:
  - **WasmDriver** – *WebAssembly execution driver with subprocess fallback.* (lines 17-82)
    - `__init__(self)` (lines 20-23)
    - `_check_dependencies(self)` (lines 25-30)
    - `get_status(self)` (lines 78-82)

---

