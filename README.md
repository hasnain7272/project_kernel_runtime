# Project Kernel Runtime

A marketplace-embeddable AI coding agent kernel inspired by OpenHands, Aider, Claude Code, Cursor, and Windsurf.

## Overview

Project Kernel Runtime is a production-grade AI coding agent kernel with a Coordinator Pattern architecture:

- **Multi-modal deployment**: Web UI, API Server, and MCP server modes
- **Governance enforcement**: Policy-based tool execution controls
- **Task durability**: Persistent task state with SQLite storage
- **MCP protocol support**: Streamable HTTP + WebSocket transports
- **Session management**: Multi-user context with workspace isolation
- **Agentic Loop**: Gather → Plan → Act → Verify with Manager-based multi-agent orchestration

## Architecture

```
project_kernel_runtime/
├── kernel/                    # Core orchestration and execution engine
│   ├── orchestrator.py        # Main coordination engine (Coordinator pattern)
│   ├── manager.py             # Manager-based multi-agent orchestration
│   ├── task_state_machine.py  # Persistent task execution
│   ├── tool_executor.py       # Pipeline tool execution with governance
│   ├── governance.py          # Policy enforcement engine
│   ├── skills_registry.py     # Capability definitions
│   ├── session_manager.py     # User context management
│   ├── workflow_engine.py     # AgentScope-inspired pipelines
│   ├── swarm.py              # Multi-agent swarm coordination
│   ├── planner.py            # Mission planning for agentic loops
│   ├── sandbox.py            # Zero-trust sandbox execution
│   ├── mcp_bridge.py         # MCP server bridge
│   └── ...
├── services/                  # API services layer
│   ├── fastapi_server.py     # HTTP/WebSocket API gateway
│   ├── router_agent.py       # Agent execution endpoints
│   ├── router_mcp.py         # MCP protocol endpoints
│   ├── router_runtime.py     # Runtime configuration endpoints
│   ├── ui_websocket.py       # Real-time UI communication
│   ├── research_api.py       # Research mode endpoints
│   ├── project_registry.py   # Project folder registry
│   └── runtime_control.py    # Control plane for jobs
├── protocols/                 # Protocol implementations
│   ├── mcp_server.py         # MCP 2026 Streamable HTTP + WebSocket server
│   ├── mcp_client.py         # MCP client for external tools
│   ├── mesh_p2p.py           # Peer-to-peer mesh networking (A2A)
│   └── federated_hub.py      # Federated knowledge sharing
├── memory/                    # Memory and state management
│   ├── chroma_store.py       # Vector storage with ChromaDB
│   └── state_hub.py          # Global state management (SSOT)
├── data/                      # Persistent storage
│   ├── tasks.db             # Task persistence
│   ├── sessions.db          # Session persistence
│   ├── heartbeat.db         # Scheduled task persistence
│   ├── credits.db           # Credit tracking
│   └── mcp_registry.json    # MCP server configurations
├── runtime.yaml              # Main configuration file
└── main.py                   # Entry point
```

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Or install from pyproject.toml
pip install -e .
```

## Usage

### Start the Server

```bash
# Start FastAPI server with default settings
python main.py

# Start with custom host/port
python main.py --host 0.0.0.0 --port 8089
```

### API Endpoints

#### Core Endpoints
- `GET /health` - Health check
- `GET /api/ui/bootstrap` - Initial state for frontend IDE
- `GET /status/full` - Full system status
- `GET /api/runtime/surfaces` - Available service surfaces

#### Session Management
- `POST /api/agent/sessions` - Create session
- `GET /api/agent/sessions/{user_id}` - Get session
- `DELETE /api/agent/sessions/{user_id}` - End session

#### Task Management
- `POST /api/agent/tasks` - Create task
- `POST /api/agent/tasks/{task_id}/execute` - Execute task
- `GET /api/agent/tasks/{task_id}` - Get task status
- `POST /api/agent/tasks/{task_id}/stop` - Stop task

#### Agentic Loop
- `POST /api/agent/execute` - Execute agentic loop (SSE stream)

#### MCP Protocol
- `POST /mcp` - MCP Streamable HTTP POST
- `GET /mcp` - MCP Streamable HTTP GET (SSE stream)
- `POST /a2a` - A2A JSON-RPC endpoint

#### Configuration
- `GET /api/runtime/yaml` - Get runtime configuration
- `POST /api/runtime/yaml` - Update runtime configuration
- `GET /api/runtime/project/registry` - Project registry
- `GET /api/runtime/models/status` - LLM provider status

#### Governance & Security
- `GET /api/runtime/governance/config` - Governance configuration
- `PUT /api/runtime/governance/config` - Update governance
- `GET /api/runtime/governance/audit` - Audit log
- `POST /api/runtime/governance/approvals/{id}` - Resolve approval

#### File Operations
- `GET /api/runtime/workspace/tree` - File tree explorer
- `GET /api/runtime/workspace/file` - Read file content

### WebSocket API

Connect to `/ws/ui` for real-time events:

```javascript
const ws = new WebSocket('ws://localhost:8089/ws/ui');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    // Handle: task updates, tool execution, state changes
};
```

## Configuration

The runtime is configured via `runtime.yaml`:

```yaml
version: 2.0.0
mode: production

# Governance

governance:
  enabled: true
  default_role: developer
  require_approval_for:
    - git_commit
    - bash_execute
  policy_matrix:
    plan:
      read_only: true
      write: false
      execute: true
    build:
      read_only: true
      write: true
      execute: true

# MCP Protocol

mcp:
  enabled: true
  transport: streamable_http
  host: 0.0.0.0
  port: 8090

# LLM Providers

llm:
  active_model: ollama/llama3.1:8b
  providers:
    - name: ollama
      base_url: http://127.0.0.1:11500
      enabled: true
    - name: anthropic
      api_key_env: ANTHROPIC_API_KEY
      enabled: false

# Sandbox

sandbox:
  backend: subprocess
  docker_image: python:3.11-slim
  memory_limit_mb: 512

# Features

features:
  gtm_swarm: true
  mesh_p2p: true
  sre_swarm: true
  predictive: true
  skill_compiler: true
```

## Core Concepts

### Agentic Loop

The core execution model: Gather → Plan → Act → Verify

- **Manager**: Analyzes tasks and decomposes into sub-tasks
- **Orchestrator**: Dispatches to specialized agents via ToolExecutor
- **Event Bus**: All subsystems communicate via publish/subscribe

### Skills

Skills define capabilities, organized by domain:
- **Core**: File operations, terminal, git, web, LSP
- **Coding**: Testing, debugging, refactoring

Skills are loaded from `kernel/skills_registry.py`.

### Tasks

Durable tasks with state persistence:
- **Types**: code_generation, code_review, debugging, refactoring, testing, deployment, custom
- **States**: pending, running, paused, completed, failed, cancelled
- **Steps**: Individual operations with tool requirements

Tasks are stored in `data/tasks.db`.

### Governance

Policy enforcement at the tool execution layer:
- **Modes**: plan, review, research, build
- **Decisions**: allow, deny, require_approval
- **Audit logging**: All tool executions logged to SQLite

### Sessions

User context management:
- **Workspace isolation**: Per-session working directories
- **Task history**: Linked to session
- **Activity tracking**: File access and command history

Sessions are stored in `data/sessions.db`.

### MCP Protocol

Full MCP 2026 spec implementation:
- **Streamable HTTP**: POST for requests, GET for SSE streams
- **WebSocket**: Legacy transport for backward compatibility
- **Session management**: Mcp-Session-Id headers
- **Resumability**: Last-Event-ID for reconnection
- **Protocol versions**: 2024-11-05 and 2025-03-26

### Tool Execution Pipeline

All tools execute through `ToolExecutor`:
1. **Validation**: Input schema validation
2. **Governance**: Policy enforcement
3. **Sandbox**: Isolated execution
4. **Audit**: Log execution
5. **Event**: Publish result to EventBus

## Development

### Running Tests

```bash
# Run smoke tests
python verify_runtime_smoke.py

# Run specific test
python test_file_ops.py
```

### Project Structure Notes

- **Coordinator Pattern**: Orchestrator uses lazy initialization via `@cached_property`
- **Event-Driven**: All communication through EventBus
- **Zero-Trust**: Sandboxed tool execution
- **Multi-Agent**: Manager-based task decomposition

## License

MIT License
