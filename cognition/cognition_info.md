# cognition Module Information

This file provides an ultra-dense context mapping for agentic AI ingestion.


## File: `context_cluster.py`
Imports: typing.{Dict,List,Any}, collections.{defaultdict}, integrations.a2a_protocol.{AgentCard}
Class `ClusterState` (L10-14):
Class `SwarmCluster` (L16-36):
  > Docs: A dynamic, self-organizing cluster of specialized agents.
  - `def __init__(self, name, focus)` (L19-24)
  - `def add_member(self, agent)` (L26-27)
  - `def to_dict(self)` (L29-36)
Class `ClusterManager` (L38-69):
  > Docs: Manages the lifecycle and distribution of agents into Context Clusters.
  - `def __init__(self)` (L41-46)
  - `def organize_mesh(self, available_peers, active_context)` (L48-66) - Dynamically assign peers to clusters based on the current context.
  - `def get_cluster_topology(self)` (L68-69)

## File: `llm_provider.py`
Imports: asyncio, logging, os, time, dataclasses.{dataclass,field}, typing.{Any,AsyncGenerator,Dict,List,Optional}, datetime.{datetime,timezone}
Class `LLMMessage` (L32-38):
  > Docs: A message in the LLM conversation.
Class `LLMResponse` (L42-52):
  > Docs: Response from an LLM call.
Class `UsageStats` (L56-63):
  > Docs: Aggregate usage statistics.
Class `LLMProvider` (L70-390):
  > Docs: Unified LLM provider with multi-model support, streaming, and tool calling.
  - `def __init__(self, config)` (L84-116)
  - `def get_model_for_task(self, task_type)` (L118-120) - Route task to optimal model via model router.
  - `async def complete(self, messages, model, temperature, max_tokens, tools, task_type)` (L122-172) - Send a completion request to the LLM.
  - `async def stream(self, messages, model, temperature, max_tokens, task_type)` (L174-213) - Stream a completion response token by token.
  - `async def _call_litellm(self, messages, model, temperature, max_tokens, tools)` (L215-304) - Call LLM via litellm (supports Ollama, OpenAI, Anthropic, etc.).
  - `def set_ollama_base_url(self, host, port)` (L306-310) - Update the Ollama API base URL at runtime (from UI provider switch).
  - `def _configure_litellm_provider(self, model)` (L312-326) - Set litellm environment for the model's provider.
  - `def _detect_provider(self, model)` (L328-336) - Detect which provider a model belongs to.
  - `def _messages_to_dicts(messages)` (L339-351) - Convert LLMMessage objects to dict format for litellm.
  - `def _track_usage(self, response)` (L353-379) - Track token usage and cost.
  - `def get_usage_stats(self)` (L381-390) - Get aggregate usage statistics.
Func `def _env_provider()` (L397-398)
Func `def summarize_text(text, strategy, max_chars)` (L401-419) - Legacy provider abstraction — kept for backward compatibility.

## File: `self_attention.py`
Imports: logging, typing.{Any,Dict,List}
Class `SelfAttentionLoop` (L16-95):
  > Docs: Validates reasoning consistency across agent steps.
  - `def __init__(self, orchestrator)` (L19-21)
  - `async def reflect_on_reasoning(self, task_id, recent_steps)` (L23-61) - Analyze recent reasoning steps for contradictions.
  - `def _detect_contradictions(self, texts)` (L63-88) - Simple rule-based contradiction detection.
  - `def get_confidence_score(self, task_id)` (L90-95) - Get latest confidence score for a task.