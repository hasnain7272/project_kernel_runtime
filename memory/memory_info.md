# memory Module Information

This file provides an ultra-dense context mapping for agentic AI ingestion.


## File: `chroma_store.py`
Imports: logging, os, typing.{Any,Dict,List,Optional}, datetime.{datetime,timezone}, uuid.{uuid4}
Class `MemoryResult` (L27-40):
  > Docs: A result from memory recall.
  - `def __init__(self, id, content, metadata, distance)` (L29-34)
  - `def to_dict(self)` (L36-40)
Class `CodeSnippet` (L43-59):
  > Docs: A code snippet from codebase RAG.
  - `def __init__(self, file_path, content, start_line, end_line, language, score)` (L45-52)
  - `def to_dict(self)` (L54-59)
Class `ChromaVectorStore` (L66-166):
  > Docs: ChromaDB-backed vector store for semantic search.
  - `def __init__(self, persist_dir)` (L74-80)
  - `def _init_store(self)` (L82-98) - Initialize ChromaDB or fall back to in-memory.
  - `async def store(self, text, metadata, id)` (L100-117) - Store text with optional metadata.
  - `async def search(self, query, top_k, where)` (L119-149) - Search for similar documents.
  - `async def delete(self, id)` (L151-160) - Delete a document.
  - `def count(self)` (L163-166)
Class `AgentMemory` (L173-201):
  > Docs: Long-term agent memory using vector similarity search.
  - `def __init__(self, vector_store)` (L180-181)
  - `async def remember(self, content, context, task_id, category)` (L183-191) - Store a memory.
  - `async def recall(self, query, limit, category)` (L193-197) - Recall memories similar to query.
  - `async def forget(self, memory_id)` (L199-201) - Remove a memory.
Class `CodebaseRAG` (L216-321):
  > Docs: Codebase semantic indexing and retrieval.
  - `def __init__(self, vector_store, persist_dir)` (L224-229)
  - `def store(self)` (L232-238)
  - `async def index_workspace(self, workspace_path, max_files)` (L240-289) - Index a workspace for semantic search.
  - `async def query(self, question, top_k)` (L291-304) - Query indexed codebase by semantic meaning.
  - `def _chunk_code(self, content, file_path, chunk_size)` (L306-321) - Chunk code into segments for indexing.

## File: `state_hub.py`
Imports: typing.{Dict,Any,List}, time
Class `GlobalStateHub` (L9-65):
  > Docs: The Single Source of Truth (SSOT) for the entire Antigravity Kernel.
  - `def __init__(self)` (L14-19)
  - `def update_task_state(self, task_id, status, result)` (L21-28)
  - `def record_thought(self, agent_id, agent_type, thought)` (L30-45) - Streams a 'Reasoning Frame' for total observability.
  - `def get_snapshot(self)` (L47-58) - Provides a complete system state for UI/API synchronization.
  - `def inject_thought_delta(self, agent_id, new_logic)` (L60-65) - Hot Reloads 'Self-Attention' logic for a running agent.