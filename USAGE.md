# Project Kernel Runtime: The Complete Guide

Welcome to the **Project Kernel Runtime**, an advanced AI Agent Orchestration System. This guide covers everything you need to know to use the system for research, code generation, and enterprise-scale agent coordination.

---

## 🚀 Getting Started

### 1. Start the API Server
The core of the system is the FastAPI server which orchestrates all tasks and research sessions.
```powershell
python -m project_kernel_runtime.services.fastapi_server
```
*API will be available at `http://localhost:8000`*

### 2. Launch the Research Dashboard (Web)
Open the premium dashboard to manage sessions with a visual interface.
- **Location**: `src/project_kernel_runtime/ui/web/index.html`
- Simply open this file in any modern browser. It connects to the API automatically.

### 3. Use the Interactive CLI
For terminal power users, use the enhanced interactive CLI.
```powershell
python -m project_kernel_runtime.ui.enhanced_cli --interactive
```

---

## 🔍 Advanced Research Mode

Research sessions can aggregate data from multiple specialized sources.

### Core Research Workflow:
1. **Initialize Session**: `POST /research/` with `user_id` and `query`.
2. **Add Sources**: `POST /research/{session_id}/source` with `source_uri` and `source_type`.
3. **Summarize**: `POST /research/{session_id}/summarize` to generate the final report.
4. **Export**: `GET /research/{session_id}/report/{report_id}/export?format=pdf`

### Supported Source Types:
| Source Type | URI Example | Capabilities |
| :--- | :--- | :--- |
| **Web** | `https://example.com` | Standard extraction and cleaning. |
| **PDF** | `https://path/to/report.pdf` | Text extraction (local or remote). |
| **Repo** | `https://github.com/user/repo` | Analyzes code structure and READMEs. |
| **DB** | `sqlite:///data.db` | Schema discovery and query aggregation. |
| **Browser** | `https://dynamic-site.com` | Dynamic scraping & screenshots via Playwright. |

---

## 🤖 Enterprise Orchestration (Month 9-10)

### Multi-Agent Swarms
Complex tasks are automatically delegated to specialized agents:
- **ResearchSpecialist**: Information gathering and aggregation.
- **CodeTechnician**: Code generation, refactoring, and testing.
- **GovernanceGuard**: Policy enforcement and auditing.

**How to use Swarms:**
Swarms are automatically utilized during complex task execution. You can monitor swarm actions in the **Web Dashboard** or via the **Enhanced CLI**.

### Real-Time Analytics
Monitor the efficiency of your agentic workflows.
- **Bottleneck Detection**: Automatically identifies slow task steps.
- **Metrics Dashboard**: View uptime, error rates, and resource consumption.
- **Endpoint**: `GET /health` (System diagnostics).

---

## 🛡️ Governance & Safety
All operations are filtered through the **Governance Engine**:
- **Tool Permissions**: Actions like `file_write` or `network_access` require specific user entitlements.
- **Audit Trails**: Every action is saved for compliance and security reviews.
- **Skill Levels**: Users are assigned skill levels (`Core`, `Advanced`, `Expert`) which limit tool availability.

---

## 🛠️ Configuration
Manage your runtime environment in `runtime.yaml`:
- **LLM Settings**: Switch between GPT-4, Claude, and local models.
- **MCP Config**: Connect to external tools via Model Context Protocol.
- **Safety Toggles**: Enable/disable network access and domain allowlists.

---
*Created by Antigravity - Advanced Agentic Coding Assistant*
