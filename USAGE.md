# Project Kernel Runtime: Complete Usage Guide

Complete guide for using Project Kernel Runtime - a production-grade AI coding agent kernel with Coordinator Pattern architecture.

---

## 🚀 Quick Start

### 1. Start the Server

```bash
# Default: runs on http://localhost:8089
python main.py

# Custom port
python main.py --port 9000

# Bind to all interfaces
python main.py --host 0.0.0.0 --port 8089
```

### 2. Verify Installation

```bash
# Health check
curl http://localhost:8089/health

# Get bootstrap data for UI
curl http://localhost:8089/api/ui/bootstrap
```

### 3. Access the Web UI

Open your browser to: `http://localhost:8089/ui/`

---

## 🤖 Agentic Loop Execution

The core execution model: **Gather → Plan → Act → Verify**

### Execute an Agentic Task

```bash
curl -X POST http://localhost:8089/api/agent/execute \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Create a Python script that sorts files by extension",
    "user_id": "myuser",
    "session_id": "sess_abc123",
    "max_iterations": 10
  }'
```

Response (SSE stream):
```
event: step_start
data: {"step": 1, "action": "analyze", "description": "Understanding task requirements"}

event: tool_call
data: {"tool": "file_write", "path": "./workspace/my-project/sort_files.py"}

event: step_complete
data: {"step": 1, "success": true}

event: task_complete
data: {"task_id": "task_xyz789", "status": "completed"}
```

---

## 📋 Task Management

### Create a Task

```bash
curl -X POST http://localhost:8089/api/agent/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "myuser",
    "type": "code_generation",
    "description": "Generate a REST API client",
    "steps": [
      {"description": "Analyze requirements", "tools": ["web_search"]},
      {"description": "Generate code", "tools": ["code_generation"]},
      {"description": "Validate", "tools": ["test_runner"]}
    ]
  }'
```

### Execute a Task

```bash
curl -X POST http://localhost:8089/api/agent/tasks/task_123/execute
```

### Get Task Status

```bash
curl http://localhost:8089/api/agent/tasks/task_123
```

### Stop a Task

```bash
curl -X POST http://localhost:8089/api/agent/tasks/task_123/stop
```

### List Tasks

```bash
curl "http://localhost:8089/api/agent/tasks?user_id=myuser&status=running"
```

---

## 🔐 Session Management

### Create a Session

```bash
curl -X POST http://localhost:8089/api/agent/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "myuser",
    "workspace_path": "./workspace/my-project",
    "mode": "cli"
  }'
```

### Get Session Info

```bash
curl http://localhost:8089/api/agent/sessions/myuser
```

### End Session

```bash
curl -X DELETE http://localhost:8089/api/agent/sessions/myuser
```

---

## 🔧 Tool Execution

### Call a Tool Directly

```bash
curl -X POST http://localhost:8089/api/agent/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "file_write",
    "arguments": {
      "path": "./workspace/test.txt",
      "content": "Hello World"
    },
    "user_id": "myuser",
    "session_id": "sess_abc123"
  }'
```

### Get Available Skills

```bash
curl "http://localhost:8089/api/agent/skills?user_id=myuser"
```

---

## 🔄 Workflow Engine

### Run a Workflow Pipeline

```bash
curl -X POST http://localhost:8089/api/workflows/run \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess_abc123",
    "name": "Refactor Pipeline",
    "pipeline": "sequential",
    "steps": [
      {"name": "analyze", "tool": "code_analyzer", "inputs": {"target": "main.py"}},
      {"name": "refactor", "tool": "code_refactor", "inputs": {"suggestions": "{{analyze.output}}"}},
      {"name": "test", "tool": "test_runner", "inputs": {}}
    ],
    "input": {"workspace": "./workspace/my-project"}
  }'
```

**Pipeline Types:**
- `sequential`: Execute steps one after another
- `fanout`: Execute steps in parallel

---

## 🔍 Research Mode

### Start Research Session

```bash
curl -X POST http://localhost:8089/research/start \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "myuser",
    "query": "Latest Python web frameworks 2025"
  }'
```

### Add Source

```bash
curl -X POST http://localhost:8089/research/sessions/research_1/sources \
  -H "Content-Type: application/json" \
  -d '{
    "uri": "https://example.com/article",
    "type": "web"
  }'
```

### Generate Summary

```bash
curl -X POST http://localhost:8089/research/sessions/research_1/summarize \
  -H "Content-Type: application/json" \
  -d '{"strategy": "comprehensive"}'
```

### Get Research Progress

```bash
curl http://localhost:8089/research/sessions/research_1/progress
```

### List Research Sessions

```bash
curl "http://localhost:8089/research/sessions?user_id=myuser"
```

### Export Report

```bash
curl "http://localhost:8089/research/sessions/research_1/reports/report_1/export?format=markdown"
```

---

## 🔌 MCP Protocol

### List MCP Servers

```bash
curl http://localhost:8089/api/runtime/mcp/registry
```

### Register New MCP Server

```bash
curl -X POST http://localhost:8089/api/runtime/mcp/registry \
  -H "Content-Type: application/json" \
  -d '{
    "name": "filesystem-server",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem"],
    "auto_start": true
  }'
```

### Start MCP Server

```bash
curl -X POST http://localhost:8089/api/runtime/mcp/servers/filesystem-server/start
```

### Stop MCP Server

```bash
curl -X POST http://localhost:8089/api/runtime/mcp/servers/filesystem-server/stop
```

### Toggle MCP Server

```bash
curl -X POST http://localhost:8089/api/runtime/mcp/servers/filesystem-server/toggle \
  -H "Content-Type: application/json" \
  -d '{"disabled": true}'
```

### Call MCP Tool

```bash
curl -X POST http://localhost:8089/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "read_file",
      "arguments": {"path": "/workspace/file.txt"}
    },
    "id": 1
  }'
```

---

## 🛡️ Governance & Security

### Get Governance Configuration

```bash
curl http://localhost:8089/api/runtime/governance/config
```

### Update Governance

```bash
curl -X PUT http://localhost:8089/api/runtime/governance/config \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "default_role": "developer",
    "require_approval_for": ["git_commit", "bash_execute", "file_delete"]
  }'
```

### Get Audit Log

```bash
curl "http://localhost:8089/api/runtime/governance/audit?limit=100"
```

### Get Pending Approvals

```bash
curl http://localhost:8089/api/runtime/governance/approvals
```

### Resolve Approval

```bash
curl -X POST http://localhost:8089/api/runtime/governance/approvals/approval_123 \
  -H "Content-Type: application/json" \
  -d '{"approved": true, "reviewer_id": "admin"}'
```

### Update Session Governance

```bash
curl -X PUT http://localhost:8089/api/runtime/sessions/sess_abc123/governance \
  -H "Content-Type: application/json" \
  -d '{
    "risk_mode": "review",
    "require_approval_for": ["file_delete", "network_request"]
  }'
```

---

## ⚙️ Configuration Management

### Get Runtime Configuration

```bash
curl http://localhost:8089/api/runtime/yaml
```

### Update Runtime Configuration

```bash
curl -X POST http://localhost:8089/api/runtime/yaml \
  -H "Content-Type: application/json" \
  -d '{
    "yaml": "llm:\\n  active_model: ollama/qwen2.5-coder:14b-instruct"
  }'
```

### Get System Configuration

```bash
curl http://localhost:8089/api/runtime/runtime/config
```

### Patch System Configuration

```bash
curl -X PATCH http://localhost:8089/api/runtime/runtime/config \
  -H "Content-Type: application/json" \
  -d '{
    "features": {
      "gtm_swarm": true,
      "sre_swarm": true
    }
  }'
```

---

## 🤖 LLM Providers

### Get Model Status

```bash
curl http://localhost:8089/api/runtime/models/status
```

### Update Model Configuration

```bash
curl -X PUT http://localhost:8089/api/runtime/models/status \
  -H "Content-Type: application/json" \
  -d '{
    "active_model": "ollama/qwen2.5-coder:14b-instruct",
    "ollama_host": "127.0.0.1",
    "ollama_port": "11500"
  }'
```

### Get Available Models

```bash
curl http://localhost:8089/api/runtime/models/available
```

### Get Provider Live Status

```bash
curl http://localhost:8089/api/runtime/providers/live
```

### Configure NVIDIA NIM

```bash
curl -X POST http://localhost:8089/api/runtime/nvidia-nim \
  -H "Content-Type: application/json" \
  -d '{
    "base_url": "https://integrate.api.nvidia.com/v1",
    "api_key": "your-api-key"
  }'
```

---

## 📁 File Operations

### Get File Tree

```bash
curl "http://localhost:8089/api/runtime/workspace/tree?path=./workspace&depth=2"
```

Response:
```json
{
  "tree": {
    "name": "workspace",
    "path": "./workspace",
    "type": "directory",
    "children": [
      {
        "name": "main.py",
        "path": "./workspace/main.py",
        "type": "file",
        "size": 1024,
        "ext": ".py"
      }
    ]
  },
  "root": "./workspace",
  "exists": true
}
```

### Read File

```bash
curl "http://localhost:8089/api/runtime/workspace/file?path=./workspace/main.py"
```

---

## 📊 Project Registry

### Get Project Registry

```bash
curl http://localhost:8089/api/runtime/project/registry
```

### List Project Folders

```bash
curl http://localhost:8089/api/runtime/project/folders
```

### Add Project Folder

```bash
curl -X POST http://localhost:8089/api/runtime/project/folders \
  -H "Content-Type: application/json" \
  -d '{"path": "./my-projects/project1"}'
```

### Remove Project Folder

```bash
curl -X DELETE "http://localhost:8089/api/runtime/project/folders?path=./my-projects/project1"
```

---

## 🌐 A2A Mesh Networking

### Get Mesh Topology

```bash
curl http://localhost:8089/api/runtime/a2a/topology
```

### Delegate Task to Peer

```bash
curl -X POST http://localhost:8089/api/runtime/a2a/delegate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Analyze this codebase",
    "target_peer": "peer_abc123",
    "session_id": "sess_abc123",
    "workspace_path": "./workspace/project"
  }'
```

---

## 🎯 Jobs & Background Tasks

### List Jobs

```bash
curl "http://localhost:8089/api/runtime/jobs?limit=50"
```

### Create Job

```bash
curl -X POST http://localhost:8089/api/runtime/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "kind": "code_analysis",
    "payload": {
      "target_path": "./workspace/project",
      "analysis_type": "complexity"
    }
  }'
```

### Get Job

```bash
curl http://localhost:8089/api/runtime/jobs/job_123
```

### Cancel Job

```bash
curl -X POST http://localhost:8089/api/runtime/jobs/job_123/cancel
```

---

## 📈 Auto-Tune

### Get Auto-Tune Suggestions

```bash
curl -X POST http://localhost:8089/api/runtime/auto-tune \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Apply Auto-Tune Suggestion

```bash
curl -X POST http://localhost:8089/api/runtime/auto-tune/apply \
  -H "Content-Type: application/json" \
  -d '{
    "param": "llm.active_model",
    "value": "ollama/qwen2.5-coder:14b-instruct"
  }'
```

---

## 💓 Heartbeat Tasks

### List Heartbeat Tasks

```bash
curl http://localhost:8089/api/runtime/heartbeat
```

### Create Heartbeat Task

```bash
curl -X POST http://localhost:8089/api/runtime/heartbeat \
  -H "Content-Type: application/json" \
  -d '{
    "label": "Daily Sync",
    "cron": "0 9 * * *",
    "task": "Sync repository with upstream",
    "user_id": "myuser"
  }'
```

### Toggle Heartbeat Task

```bash
curl -X POST http://localhost:8089/api/runtime/heartbeat/task_123/toggle \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

### Delete Heartbeat Task

```bash
curl -X DELETE http://localhost:8089/api/runtime/heartbeat/task_123
```

---

## 🎓 Skills Registry

### Get Skills Registry

```bash
curl http://localhost:8089/api/runtime/skills/registry
```

### Toggle Skill

```bash
curl -X POST http://localhost:8089/api/runtime/skills/data_analysis/toggle \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "pack": "core"
  }'
```

---

## 💰 Credits

### Get Credits Balance

```bash
curl http://localhost:8089/api/runtime/credits/balance
```

---

## 🐝 Swarm Status

### Get Swarm Status

```bash
curl http://localhost:8089/api/runtime/swarm/status
```

---

## 🌊 WebSocket Real-Time Updates

Connect to `/ws/ui` for live updates:

```javascript
const ws = new WebSocket('ws://localhost:8089/ws/ui');

ws.onopen = () => {
    console.log('Connected to Project Kernel Runtime');
    
    // Subscribe to events
    ws.send(JSON.stringify({
        type: 'subscribe',
        channels: ['tasks', 'sessions', 'tools']
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case 'task.created':
            console.log('Task created:', data.task_id);
            break;
        case 'task.progress':
            console.log(`Task ${data.task_id}: ${data.progress}%`);
            break;
        case 'tool.execution':
            console.log(`Tool ${data.tool} executed:`, data.success);
            break;
        case 'governance.approval_required':
            console.log('Approval required for:', data.tool);
            break;
    }
};

ws.onclose = () => {
    console.log('Disconnected');
};
```

---

## 🐍 Python SDK

```python
from project_kernel_runtime import Orchestrator, init_orchestrator
import asyncio

async def main():
    # Initialize orchestrator
    orchestrator = await init_orchestrator()
    
    # Create session
    session = await orchestrator.start_session(
        user_id="myuser",
        workspace_path="./workspace/project"
    )
    
    # Execute agentic loop
    result = await orchestrator.execute_agentic_loop(
        task_description="Create a Python script",
        user_id="myuser",
        session_id=session.session_id,
        max_iterations=10
    )
    
    print(f"Task completed: {result['task_id']}")
    print(f"Response: {result['response']}")
    
    # Call tool directly
    result = await orchestrator.call_tool(
        user_id="myuser",
        tool_name="file_write",
        arguments={"path": "test.txt", "content": "Hello"},
        session_id=session.session_id
    )
    
    # End session
    await orchestrator.end_session("myuser")

asyncio.run(main())
```

---

## 🛠️ Troubleshooting

### Server Won't Start

```bash
# Check if port is in use
lsof -i :8089

# Try different port
python main.py --port 9000
```

### MCP Connection Issues

```bash
# Check MCP status
curl http://localhost:8089/api/runtime/mcp/registry

# Reprobe MCP servers
curl -X POST http://localhost:8089/api/agent/mcp/reprobe
```

### LLM Provider Issues

```bash
# Check provider status
curl http://localhost:8089/api/runtime/models/status

# Check Ollama connection
curl http://127.0.0.1:11500/api/tags
```

### Session Not Found

```bash
# List active sessions
curl http://localhost:8089/api/agent/sessions/myuser
```

---

## ⚙️ Configuration Examples

### Development Mode

```yaml
mode: development
governance:
  enabled: false
sandbox:
  backend: subprocess
llm:
  active_model: ollama/llama3.1:8b
```

### Production Mode

```yaml
mode: production
governance:
  enabled: true
  require_approval_for: [git_commit, bash_execute, file_delete]
sandbox:
  backend: docker
  docker_image: python:3.11-slim
  memory_limit_mb: 512
llm:
  active_model: anthropic/claude-3-5-sonnet-20241022
  providers:
    - name: anthropic
      api_key_env: ANTHROPIC_API_KEY
      enabled: true
features:
  gtm_swarm: true
  sre_swarm: true
  mesh_p2p: true
```

### Multi-Provider Setup

```yaml
llm:
  active_model: ollama/llama3.1:8b
  providers:
    - name: ollama
      base_url: http://127.0.0.1:11500
      enabled: true
      priority: 0
    - name: anthropic
      api_key_env: ANTHROPIC_API_KEY
      default_model: claude-3-5-sonnet-20241022
      enabled: true
      priority: 1
  model_router:
    autocomplete: ollama/llama3.1:8b
    code_generation: anthropic/claude-3-5-sonnet-20241022
    architecture: anthropic/claude-3-5-sonnet-20241022
```

---

## 📚 Architecture Overview

### Coordinator Pattern
- **Orchestrator**: Main coordination engine with lazy subsystem initialization
- **Event Bus**: All subsystems communicate via publish/subscribe
- **ToolExecutor**: Central pipeline for all tool execution

### Agentic Loop
- **Manager**: Analyzes tasks and decomposes into sub-tasks
- **Planner**: Mission planning for complex operations
- **Swarm**: Multi-agent coordination for parallel execution

### Data Flow
1. User request → FastAPI Server
2. Session validation → SessionManager
3. Task creation → TaskStateMachine
4. Agentic execution → Manager → Orchestrator
5. Tool execution → ToolExecutor → Governance → Sandbox
6. Event publishing → EventBus → WebSocket clients

---

*Created by Antigravity - Advanced Agentic Coding Assistant*
