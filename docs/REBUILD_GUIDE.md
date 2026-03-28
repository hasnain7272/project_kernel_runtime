# 🏗️ Rebuild Guide: Antigravity AgenticOS (Horizon 2028)

This guide provides a comprehensive, step-by-step blueprint for a developer to reconstruct the entire Antigravity Project Kernel Runtime from scratch, even if the original source code is lost.

## 1. Prerequisites and Environment Setup
Before writing a single line of code, establish the correct environment.
* **Language:** Python 3.11+
* **Package Manager:** `pip` (or `poetry` for structured management).
* **Core Dependencies (requirements.txt):**
  ```text
  fastapi>=0.111.0
  uvicorn>=0.30.1
  litellm>=1.40.0
  pydantic>=2.7.0
  pyyaml>=6.0.1
  chromadb>=0.5.0
  httpx>=0.27.0
  # Optional plugins:
  playwright   # For Vision/Browser Swarms
  e2b          # For E2B Sandbox support
  docker       # For Docker Sandbox support
  ```

## 2. Order of Implementation (Zero to One)

To construct this architecture efficiently, build from the inside out:

### Phase 1: The Config & Data Layer
1. **`runtime.yaml`:** Create the schema definition representing the entire OS (LLM models, API keys, Sandbox settings, MCP ports).
2. **`kernel/runtime.py`:** Write Pydantic data models (`RuntimeConfig`, `LLMProviderConfig`, etc.) that parse `runtime.yaml`.
3. **`kernel/task_state_machine.py`:** Create the `Task` entity holding `status`, `history`, `tool_results`.

### Phase 2: The Action & Communication Primitives
1. **`kernel/event_bus.py`:** Build a lightweight asynchronous Pub/Sub broker. Centralize events for decoupling.
2. **`kernel/sandbox.py`:** Build the `ZeroTrustSandbox`. Start with the `subprocess` backend: use `asyncio.create_subprocess_exec` to execute bash strings and safely capture `stdout`/`stderr` with timeouts.
3. **`kernel/tool_executor.py`:** Implement the tool mapping dictionary connecting string commands to Python execution blocks (via the Sandbox).

### Phase 3: The Brain (Cognition Layer)
1. **`cognition/llm_provider.py`:** Wrap `litellm`. 
   - Crucial detail: Ensure dynamic swapping of `OLLAMA_API_BASE`.
   - Implement the Fallback mechanism looping array indices in the provider configuration.
2. **`cognition/context_cluster.py`:** Create the prompt builder taking `Task` history and flattening it into `{role: "...", content: "..."}` formats.

### Phase 4: The Loop (Orchestrator)
1. **`kernel/orchestrator.py`:** Bind it all together. 
   - Initialize the `TaskStateMachine`.
   - Implement the `while iteration < max_iterations` ReAct loop.
   - Inject context to `LLMProvider`. Parse output for `tool_calls`.
   - Delegate tools to `ToolExecutor`.
   - Inject Sandbox outputs back into LLM memory as a `tool` role message. Ensure you skip empty tool names.

### Phase 5: The Interface & External Edges
1. **`services/fastapi_server.py` & `router_agent.py`:** Spin up the Uvicorn shell, define `POST /agent/execute`. Initialize the singleton Orchestrator.
2. **`ui/web/`:** Mount static files for the Spatial Dashboard.
3. **`agents/`:** Write specialized controllers (`SRE_Swarm`, `GTM_Swarm`) that inherit from base observer classes listening to the `EventBus`.

## 3. Critical Dependencies & Hidden Assumptions
* **Model Specificity:** LiteLLM strictly requires the `ollama/` prefix for local models (e.g., `ollama/qwen2.5-coder:7b-instruct-q4_K_M`). If you supply a vanilla name like `gpt-4o`, LiteLLM will implicitly route it to OpenAI and fail without API keys.
* **Tool Call Quirks:** Different models (especially quantized local models like Qwen) sometimes emit malformed JSON tool calls or empty `name` keys. The Orchestrator *must* defensively check `if not tool_name: continue`.
* **Async Event Handling:** Fast-firing events across the EventBus can pile up. The singleton queue requires consumers (`asyncio.create_task`) running in the background.

## 4. Common Pitfalls to Avoid
- 🚫 **Hardcoding Ports:** Do not hardcode `11434` for Ollama; dynamically inject `OLLAMA_API_BASE` (e.g., to `11500`) based on `runtime.yaml`.
- 🚫 **Unsafe `eval()`/`exec()`:** Do not use `os.system()` or `subprocess.run()` without resource limits or timeout wraps; the LLM *will* lock the main thread with infinite loops. Always use `asyncio.create_subprocess_exec` inside the Sandbox.
- 🚫 **Sync in Async:** Avoid blocking `requests.get` inside the FastAPI event loop. Always use `httpx.AsyncClient` or `asyncio.to_thread`.

## 5. Testing Strategy
1. **LLM Connectivity:** Ensure `test_llm_provider.py` sends a simple `"hello"` and expects a string back, verifying connection and token incrementing.
2. **Sandbox Isolation:** Run an integration test with `while(true)` and ensure the timeout successfully interrupts the `SubprocessSandbox`.
3. **Tool Execution:** Inject a fake tool call payload into `Orchestrator.execute_agentic_loop()` without an LLM to guarantee the JSON parser properly handles the arguments without panicking.
