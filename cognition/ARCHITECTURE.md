# cognition Architecture Documentation

*Generated on: 2026-03-28T15:12:48.050398*

---

#### context_cluster.py *(69 lines)*

> **Imports**: `from typing import Dict`, `from typing import List`, `from typing import Any`, `from collections import defaultdict`, `from integrations.a2a_protocol import AgentCard`

> **Classes**:
  - **ClusterState** (lines 10-14)
  - **SwarmCluster** – *A dynamic, self-organizing cluster of specialized agents.* (lines 16-36)
    - `__init__(self, name, focus)` (lines 19-24)
    - `add_member(self, agent)` (lines 26-27)
    - `to_dict(self)` (lines 29-36)
  - **ClusterManager** – *Manages the lifecycle and distribution of agents into Context Clusters.* (lines 38-69)
    - `__init__(self)` (lines 41-46)
    - `organize_mesh(self, available_peers, active_context)` – *Dynamically assign peers to clusters based on the current context.* (lines 48-66)
    - `get_cluster_topology(self)` (lines 68-69)

---

#### llm_provider.py *(419 lines)*

> **Imports**: `import asyncio`, `import logging`, `import os`, `import time`, `from dataclasses import dataclass`, `from dataclasses import field`, `from typing import Any`, `from typing import AsyncGenerator`, `from typing import Dict`, `from typing import List`, `from typing import Optional`, `from datetime import datetime`, `from datetime import timezone`, `from research import simple_summarize`, `import litellm`, `import litellm`, `import litellm`, `from providers.openai_provider import openai_summarize`, `from research import simple_summarize`, `from providers.anthropic_provider import anthropic_summarize`

> **Constants**: `logger`=logging.getLogger(__name__)

> **Classes**:
  - **LLMMessage** – *A message in the LLM conversation.* (lines 32-38)
  - **LLMResponse** – *Response from an LLM call.* (lines 42-52)
  - **UsageStats** – *Aggregate usage statistics.* (lines 56-63)
  - **LLMProvider** – *Unified LLM provider with multi-model support, streaming, and tool calling.

Features:
- Multiple provider backends (Ollama, OpenAI, Anthropic via litellm)
- Streaming responses with proper async generators
- Tool/function calling support
- Model router (route tasks to optimal models)
- Cost and token usage tracking
- Automatic provider fallback
- Rate limiting (configurable RPM)* (lines 70-390)
    - `__init__(self, config)` (lines 84-116)
    - `get_model_for_task(self, task_type)` – *Route task to optimal model via model router.* (lines 118-120)
    - `set_ollama_base_url(self, host, port)` – *Update the Ollama API base URL at runtime (from UI provider switch).* (lines 306-310)
    - `_configure_litellm_provider(self, model)` – *Set litellm environment for the model's provider.* (lines 312-326)
    - `_detect_provider(self, model)` – *Detect which provider a model belongs to.* (lines 328-336)
    - `_messages_to_dicts(messages)` – *Convert LLMMessage objects to dict format for litellm.* (lines 339-351)
    - `_track_usage(self, response)` – *Track token usage and cost.* (lines 353-379)
    - `get_usage_stats(self)` – *Get aggregate usage statistics.* (lines 381-390)

> **Functions**:
  - `_env_provider()` (lines 397-398)
  - `summarize_text(text, strategy, max_chars)` – *Legacy provider abstraction — kept for backward compatibility.* (lines 401-419)

---

#### self_attention.py *(95 lines)*

> **Imports**: `import logging`, `from typing import Any`, `from typing import Dict`, `from typing import List`

> **Constants**: `logger`=logging.getLogger(__name__)

> **Classes**:
  - **SelfAttentionLoop** – *Validates reasoning consistency across agent steps.* (lines 16-95)
    - `__init__(self, orchestrator)` (lines 19-21)
    - `_detect_contradictions(self, texts)` – *Simple rule-based contradiction detection.* (lines 63-88)
    - `get_confidence_score(self, task_id)` – *Get latest confidence score for a task.* (lines 90-95)

---

