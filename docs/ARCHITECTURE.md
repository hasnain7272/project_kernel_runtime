# 🏛️ Architecture: Antigravity AgenticOS Project Kernel Runtime

## 1. High-Level System Overview
The **Antigravity Project Kernel Runtime** is a production-grade, state-of-the-art AI agent runtime engineered to operate dynamic, self-orchestrating agentic swarms. Built with the "Horizon 2028 Ascension" roadmap in mind, the platform transcends static single-agent loops (like vanilla copilot scripts) and provides a fully asynchronous, bounded, and distributed operating system for LLM workloads.

Its core paradigm revolves around:
- **Metacognitive Swarms:** Autonomous agents working in specialized swarms (Growth, SRE, Vision).
- **A2A & MCP Compatibility:** First-class support for Agent-to-Agent negotiation and the Model Context Protocol (MCP) for tool/resource discovery.
- **Universal Sandboxing:** A secure `ZeroTrustSandbox` executing untrusted LLM-generated code in Subprocess, Docker, or E2B environments.
- **Declarative Configuration:** Driven natively by a `runtime.yaml` spec for dynamic hot-reloading.

## 2. Technology Stack
* **Language:** Python 3.11+ (Strict types, AsyncIO native)
* **API Framework:** FastAPI (with Uvicorn ASGI Server)
* **LLM Abstraction:** LiteLLM (unifying Ollama, Anthropic, OpenAI)
* **Memory Fabric / RAG:** ChromaDB (local embedding vector database)
* **Tool Isolation:** `asyncio.subprocess`, Docker SDK, E2B Firecracker MicroVMs
* **Protocol Standards:** Model Context Protocol (MCP) v2024-11-05+, Custom A2A Mesh P2P

## 3. Directory Structure
```text
project_kernel_runtime/
├── agents/                 # Specialized autonomous swarm logic
│   ├── sre_swarm.py        # System reliability, auto-healing
│   ├── vision_swarm.py     # Multimodal and UI inspection
│   ├── watchdog.py         # System health daemon
│   └── growth_swarm/       # GTM / Marketing capability agents
├── cognition/              # Core "brain" capabilities
│   ├── llm_provider.py     # LiteLLM routing, failovers, token counting
│   ├── context_cluster.py  # Prompt aggregation and window management
│   └── self_attention.py   # Metacognitive reflection capabilities
├── integrations/           # External service hooks
│   ├── a2a_handshake.py    # Agent-to-Agent discovery
│   ├── browser_mcp.py      # Browser automation (Playwright/Selenium)
│   └── universal_mcp.py    # MCP standard tools wrapper
├── kernel/                 # The OS Core
│   ├── orchestrator.py     # Global state machine and execution loop
│   ├── runtime.py          # Configuration and global states
│   ├── sandbox.py          # ZeroTrust execution environment
│   ├── task_state_machine.py # Tracking task states (pending, running, complete)
│   ├── tool_executor.py    # Tool pipeline (Govern -> Execute -> Audit)
│   └── event_bus.py        # Pub/Sub system for internal metrics and events
├── memory/                 # Persistence Layer
│   ├── chroma_store.py     # Vector Database interactions
│   └── state_hub.py        # Long-term conversational memory
├── observability/          # Tracing and Metrics
│   ├── health.py           # Watchdog endpoints
│   ├── logging.py          # Structured JSON logging
│   └── middleware.py       # FastAPI tracing interceptors
├── protocols/              # Communication Subsystems
│   ├── mcp_client.py       # Calling external MCP servers
│   ├── mcp_server.py       # Exposing tools to external clients
│   └── mesh_p2p.py         # Peer-to-peer agent network
├── services/               # HTTP / Interface layer
│   ├── fastapi_server.py   # ASGI entrypoint
│   └── router_agent.py     # `/agent/execute` endpoints
├── ui/                     # 3D Agentic Spatial UI
│   └── web/                # HTML/JS/CSS assets for the dashboard
└── runtime.yaml            # The core configuration source of truth
```

## 4. Data Flow (Request → Processing → Response)
1. **Ingestion:** User issues a command via the Spatial UI or external API (`POST /agent/execute`).
2. **Routing:** `fastapi_server` hands off to `router_agent.py` which triggers `orchestrator.execute_agentic_loop()`.
3. **State Initialization:** A `TaskStateMachine` instance is created (tracking `pending -> reasoning -> plan -> act -> complete`). 
4. **Cognition (Reasoning & Plan):** 
   - `LLMProvider.complete()` is invoked. `runtime.yaml` dictates the model via `model_router` (e.g., routing `code_generation` to `ollama/qwen2.5-coder`).
   - The LLM streams back an AST of thought and proposed `tool_calls`.
5. **Execution (Act):**
   - The Orchestrator captures `tool_calls`.
   - `ToolExecutor` passes the tool through Governance checks.
   - Code-based tools are delegated to `ZeroTrustSandbox` (Subprocess/Docker/E2B).
6. **Result Handling:**
   - Output/Errors are fed back into the `context_cluster`.
   - The `event_bus` emits metrics to the observability system.
7. **Return:** The agent decides to finish or loops again. Response is pushed via WebSockets/SSE or standard HTTP back to the UI.

## 5. Module Responsibilities
* **Orchestrator:** The "CPU Scheduler" of the AgenticOS. Manages ReAct loops, limits iterations, and coordinates subsystems.
* **LLM Provider:** Abstracts endpoint geometry. Defaults to `127.0.0.1:11500` for local Ollama, handles API key injection for Claude/OpenAI, tracks `UsageStats`.
* **ZeroTrust Sandbox:** Security perimeter. Ensures executed bash or python code doesn't nuke the host machine.
* **Event Bus:** Asynchronous internal message broker decouple components (e.g. SRE Swarm listens for "tool.failed" events without being hardcoded into the Orchestrator).

## 6. Design Patterns
* **Pub / Sub:** `EventBus` enables loosely coupled asynchronous architecture, essential for swarm emergent behaviors.
* **Policy Strategy:** `ToolExecutor` uses an injectible policy approach to validate tools natively instead of relying on hardcoded `if/else`.
* **Facade:** `mcp_bridge` acts as a facade hiding the complexity of standard MCP JSON-RPC protocol behind native Python async awaitables.
* **Fallback Chain:** Used in `LLMProvider` (although locally restricted), cascades from primary local LLM to cloud providers upon networking failures.

## 7. Configuration & Environment
The system relies heavily on `runtime.yaml` representing a strict, Pydantic-validated environment. 
* **Key Env variables:** 
  * `OLLAMA_API_BASE`: Port mapping for local LLM inference (e.g., `http://127.0.0.1:11500`)
  * `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`: Cloud fallbacks.
* Configuration drives *model routing*, *sandbox backend selection*, and *governance rules* without requiring code compilation.

## 8. External Integrations
* **Ollama Daemon**: Native local-first model inference.
* **Blender MCP**: Directly maps 3D rendering pipeline requests from textual intent to Python bpy commands via the `execute_blender_python_script` tool loop.
* **ChromaDB**: Persists vectors to disk in `/data/chroma_db`.
* **Playwright**: Browser-based scraping and automation tools in `browser_mcp`.
