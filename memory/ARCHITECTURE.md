# memory Architecture Documentation

*Generated on: 2026-03-28T15:12:48.106905*

---

#### chroma_store.py *(321 lines)*

> **Imports**: `import logging`, `import os`, `from typing import Any`, `from typing import Dict`, `from typing import List`, `from typing import Optional`, `from datetime import datetime`, `from datetime import timezone`, `from uuid import uuid4`, `import chromadb`

> **Constants**: `logger`=logging.getLogger(__name__), `CODE_EXTENSIONS`={'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs', '.c', '.cpp', '.h', '.cs', '.rb', '.php', '.swift', '.kt', '.yaml', '.yml', '.json', '.toml', '.md', '.txt'}

> **Classes**:
  - **MemoryResult** – *A result from memory recall.* (lines 27-40)
    - `__init__(self, id, content, metadata, distance)` (lines 29-34)
    - `to_dict(self)` (lines 36-40)
  - **CodeSnippet** – *A code snippet from codebase RAG.* (lines 43-59)
    - `__init__(self, file_path, content, start_line, end_line, language, score)` (lines 45-52)
    - `to_dict(self)` (lines 54-59)
  - **ChromaVectorStore** – *ChromaDB-backed vector store for semantic search.

Uses ChromaDB's built-in embedding functions.
Falls back to in-memory store if ChromaDB not installed.* (lines 66-166)
    - `__init__(self, persist_dir)` (lines 74-80)
    - `_init_store(self)` – *Initialize ChromaDB or fall back to in-memory.* (lines 82-98)
    - `count(self)` (lines 163-166)
  - **AgentMemory** – *Long-term agent memory using vector similarity search.

Provides remember/recall/forget operations over the vector store.* (lines 173-201)
    - `__init__(self, vector_store)` (lines 180-181)
  - **CodebaseRAG** – *Codebase semantic indexing and retrieval.

Indexes source files by chunks and enables semantic search.
Inspired by: Cursor's codebase indexing, Windsurf Codemaps* (lines 216-321)
    - `__init__(self, vector_store, persist_dir)` (lines 224-229)
    - `store(self)` (lines 232-238)
    - `_chunk_code(self, content, file_path, chunk_size)` – *Chunk code into segments for indexing.* (lines 306-321)

---

#### state_hub.py *(68 lines)*

> **Imports**: `from typing import Dict`, `from typing import Any`, `from typing import List`, `import time`

> **Constants**: `state_hub`=GlobalStateHub()

> **Classes**:
  - **GlobalStateHub** – *The Single Source of Truth (SSOT) for the entire Antigravity Kernel.
Every agent step, sandbox state, and mesh heartbeat is tracked here.* (lines 9-65)
    - `__init__(self)` (lines 14-19)
    - `update_task_state(self, task_id, status, result)` (lines 21-28)
    - `record_thought(self, agent_id, agent_type, thought)` – *Streams a 'Reasoning Frame' for total observability.* (lines 30-45)
    - `get_snapshot(self)` – *Provides a complete system state for UI/API synchronization.* (lines 47-58)
    - `inject_thought_delta(self, agent_id, new_logic)` – *Hot Reloads 'Self-Attention' logic for a running agent.* (lines 60-65)

---

