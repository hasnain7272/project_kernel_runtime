# Project Kernel Runtime

A marketplace-embeddable AI coding agent kernel inspired by OpenHands, Aider, Claude Code, Cursor, and Windsurf.

## Overview

Project Kernel Runtime is a production-grade AI coding agent kernel that provides:

- **Multi-modal deployment**: CLI, Web UI, and MCP server modes
- **Governance enforcement**: Policy-based tool execution controls
- **Task durability**: Persistent task state with recovery
- **MCP protocol support**: Extensible tool and resource system
- **Session management**: User context and workspace state

## Architecture

```
project_kernel_runtime/
├── core/                    # Core SDK components
│   ├── runtime.py          # Configuration management
│   ├── governance.py       # Policy enforcement
│   ├── skills_registry.py  # Capability definitions
│   ├── task_state_machine.py # Durable task execution
│   ├── session_manager.py  # User context management
│   ├── orchestrator.py     # Main coordination engine
│   ├── mcp_client.py       # MCP protocol client
│   └── mcp_server.py      # MCP protocol server
├── services/               # API services
│   └── fastapi_server.py  # HTTP/WebSocket API
├── ui/                     # User interfaces
│   └── cli_app.py         # Textual-based CLI
└── main.py                # Entry point
```

## Installation

```bash
# Install dependencies
pip install -e .

# Or install from pyproject.toml
pip install .
```

## Usage

### CLI Mode (Aider-style)

```bash
# Start CLI interface
project-kernel cli --user-id myuser --workspace /path/to/project
```

### Web Server Mode (OpenHands-style)

```bash
# Start web server
project-kernel web --host 0.0.0.0 --port 8000
```

### MCP Server Mode

```bash
# Start MCP server for tool integration
project-kernel mcp --host localhost --mcp-port 3000
```

### API Server Mode

```bash
# Start FastAPI server
project-kernel server --host 0.0.0.0 --port 8000
```

## Configuration

The runtime is configured via `runtime.yaml`:

```yaml
mode: development
governance:
  enabled: true
  audit_log: true
mcp:
  enabled: true
  server_url: ws://localhost:3000
skills:
  core: true
  blender: false
  coding: true
```

## Core Concepts

### Skills
Skills define what the agent can do, organized by domain:
- **Core**: File operations, terminal, git, LSP, error recovery, browser automation
- **Blender**: Geometry nodes, animation, materials
- **Coding**: Testing, debugging, refactoring

### Tasks
Durable tasks with state persistence:
- **Types**: code_generation, code_review, debugging, refactoring, testing, deployment
- **States**: pending, running, paused, completed, failed, cancelled
- **Steps**: Individual operations with tool requirements

### Governance
Policy enforcement at the tool execution layer:
- **Modes**: plan, review, research, build
- **Decisions**: allow, deny, require_approval
- **Audit logging**: All tool executions are logged

### Sessions
User context management:
- **Workspace state**: Current project and files
- **Task history**: Recent tasks and commands
- **Activity tracking**: File access and command history

## API Reference

### REST API Endpoints

- `GET /health` - Health check
- `POST /sessions` - Create session
- `GET /sessions/{user_id}` - Get session info
- `POST /tasks` - Create task
- `POST /tasks/{task_id}/execute` - Execute task
- `GET /tasks/{task_id}` - Get task status
- `GET /tasks` - List user tasks
- `POST /tools/call` - Call tool
- `GET /skills` - Get available skills

### WebSocket API

Real-time communication for task updates and tool execution.

## Development

### Testing

```bash
# Run tests
python test_kernel.py
```

### Adding New Skills

1. Define skill in `skills_registry.py`
2. Implement tools in MCP server or direct execution
3. Update governance policies if needed

### Adding New UI Modes

1. Create new UI module in `ui/`
2. Update `main.py` to support new mode
3. Implement orchestrator integration

## Inspiration & References

- **OpenHands**: Modular SDK architecture, REST API design
- **Aider**: Terminal UI, git integration, AST parsing
- **Claude Code**: MCP protocol, tool extensibility
- **Cursor**: Autonomy controls, governance patterns
- **Windsurf**: MCP tools, agent coordination

## License

MIT License