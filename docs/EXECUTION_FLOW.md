# ⚙️ Execution Flow: Antigravity AgenticOS

This document details the exact sequence of events during runtime of the Antigravity Project Kernel Runtime, mapping the user request through to task completion.

## 1. Application Startup Sequence
1. **Boot:** `python main.py` or `python src/project_kernel_runtime/services/fastapi_server.py` is executed.
2. **Environment Initialization:**
   - FastAPI constructs the app instance (`app = FastAPI(...)`).
   - `runtime.yaml` is parsed by `RuntimeConfig.from_yaml()`.
   - Environment variables (e.g., `OLLAMA_API_BASE=11500`) override the baseline YAML.
3. **Core Subsystem Boot (Lifespan Context Manager):**
   - The `EventBus` spins up its asyncio queue.
   - `TaskStateMachine` memory states are hydrated.
   - `LLMProvider` initializes the connection to the designated local or remote model.
   - `ToolExecutor` registers universal tools and prepares the `ZeroTrustSandbox` backend (e.g., pre-warming the Subprocess or checking Docker availability).
4. **Agent Instantiation:**
   - Swarm logic controllers (GTM Swarm, SRE Swarm, Watchdog) attach their listeners to the EventBus.
5. **Server Listen:** `Uvicorn` starts accepting requests on port `8089`.

## 2. API Request & Data Flow
When a user submits a prompt via the UI (e.g., `POST /agent/execute` with `{"description": "say hello"}`):

1. **Ingress:** `router_agent.py` catches the payload.
2. **Task Registration:** `Orchestrator` receives the payload, creating a unique `Task` in `TaskStateMachine`. Status: `pending`.
3. **Event Emitted:** The `EventBus` publishes `task.started`.
4. **Execution Handoff:** The orchestrator invokes `execute_agentic_loop(task.id)`.

## 3. The Agentic Cognitive Loop (ReAct Flow)
Inside `orchestrator.execute_agentic_loop`:

1. **Iteration Check:** The loop checks if `iteration < max_iterations`.
2. **Context Assembly:** `ContextCluster` pulls system prompts, conversational memory, and recent tool outputs, converting them to list of `LLMMessage`.
3. **Reasoning (Cognition):** 
   - `LLMProvider.complete()` is called. 
   - Model determines if a direct textual answer is sufficient or if tools are required.
4. **Tool Parsing (Plan):**
   - If the LLM generates `tool_calls` without valid content, they are extracted.
   - *Model Quirk Check:* If an LLM sends a tool call with an empty or malformed name, it is immediately skipped to prevent crashing the executor.
5. **Tool Execution (Act):**
   - For every valid `tool_call`, the `ToolExecutor` engages the sandbox.
   - Result (`stdout`, `stderr`, or programmatic exit code) is captured in an `ExecutionContext`.
6. **Observation (Reflect):**
   - `tool_results` are formatted back into a new `tool` role LLMMessage.
   - The loop continues back to step 1 (Reasoning) with the updated context.
7. **Termination:** 
   - If no tool calls are emitted, or max iterations are reached, the loop breaks.
   - Final content is structured into a response payload. Status: `completed`.

## 4. State Management Flow
- **Ephemeral State:** Task execution is tracked via `TaskStateMachine` during an active websocket or HTTP request. 
- **Persistence:** Upon loop termination, conversational outcomes and metadata are serialized into SQLite or ChromaDB (via `state_hub.py` and `chroma_store.py`) enabling the Context Cluster to recall context in future sessions.

## 5. Error Handling & SRE Recovery Flow
1. **Tool Failure:**
   - If a tool fails (e.g., syntax error in a Bash script), the `ZeroTrustSandbox` catches it.
   - Sandbox returns `exit_code != 0` and error strings.
   - Orchestrator injects the raw error into the next LLM prompt (`"Tool failed with error: X. Please fix."`).
2. **System Failure:**
   - If the FastAPI endpoint or Orchestrator crashes catastrophically, standard exception middleware handles the 500 response.
   - `SRE_Swarm` (listening to the EventBus for `system.error`) aggregates failure modes and attempts automated patching (restart sub-services).
3. **LLM Connection Loss:**
   - Primary LLM fails -> Fallback chain engages (if `fallback_enabled: true` in `runtime.yaml`).
   - E.g., drops from Ollama -> Tries Anthropic Claude if the `ANTHROPIC_API_KEY` is present.

## 6. Asynchronous Background Jobs
- **Watchdog Daemon:** Runs a dedicated `asyncio.sleep` loop measuring system CPU/Memory, publishing metrics to the UI.
- **Predictive Nudging:** Generates asynchronous suggestions for the user interface context-aware based on the current conversational topic.
- **Garbage Collection:** Ephemeral Sandboxes (like dirty `/workspace/` folders) are wiped clean by background teardown routines.
