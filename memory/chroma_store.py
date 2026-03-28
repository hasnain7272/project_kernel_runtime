"""
Vector DB v2 — ChromaDB-backed Semantic Memory + Codebase RAG

Upgraded from abstract base to real implementation:
- ChromaDB persistent backend (no external server needed)
- Agent memory layer (remember/recall/forget)
- Codebase RAG pipeline (index workspace, query by meaning)
- Sentence-transformer embeddings (via ChromaDB default)
- Collection management for multi-tenant isolation

Inspired by: Cursor RAG indexing, Windsurf Codemaps, Claude Code project memory
"""

import logging
import os
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from uuid import uuid4

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

class MemoryResult:
    """A result from memory recall."""
    def __init__(self, id: str, content: str, metadata: Dict = None,
                 distance: float = 0.0):
        self.id = id
        self.content = content
        self.metadata = metadata or {}
        self.distance = distance

    def to_dict(self) -> Dict:
        return {
            "id": self.id, "content": self.content,
            "metadata": self.metadata, "distance": self.distance,
        }


class CodeSnippet:
    """A code snippet from codebase RAG."""
    def __init__(self, file_path: str, content: str, start_line: int = 0,
                 end_line: int = 0, language: str = "", score: float = 0.0):
        self.file_path = file_path
        self.content = content
        self.start_line = start_line
        self.end_line = end_line
        self.language = language
        self.score = score

    def to_dict(self) -> Dict:
        return {
            "file_path": self.file_path, "content": self.content,
            "start_line": self.start_line, "end_line": self.end_line,
            "language": self.language, "score": self.score,
        }


# ============================================================================
# ChromaDB Vector Store
# ============================================================================

class ChromaVectorStore:
    """
    ChromaDB-backed vector store for semantic search.
    
    Uses ChromaDB's built-in embedding functions.
    Falls back to in-memory store if ChromaDB not installed.
    """

    def __init__(self, persist_dir: str = "./data/chroma_db"):
        self.persist_dir = persist_dir
        self._client = None
        self._collection = None
        self._fallback_mode = False
        self._fallback_store: List[Dict] = []
        self._init_store()

    def _init_store(self):
        """Initialize ChromaDB or fall back to in-memory."""
        try:
            import chromadb
            os.makedirs(self.persist_dir, exist_ok=True)
            self._client = chromadb.PersistentClient(path=self.persist_dir)
            self._collection = self._client.get_or_create_collection(
                name="agent_memory",
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(f"[VectorDB] ChromaDB initialized at {self.persist_dir}")
        except ImportError:
            self._fallback_mode = True
            logger.warning("[VectorDB] ChromaDB not installed, using in-memory fallback")
        except Exception as e:
            self._fallback_mode = True
            logger.warning(f"[VectorDB] ChromaDB init failed: {e}, using fallback")

    async def store(self, text: str, metadata: Dict = None,
                    id: str = None) -> str:
        """Store text with optional metadata."""
        doc_id = id or f"mem_{uuid4().hex[:12]}"
        metadata = metadata or {}
        metadata["stored_at"] = datetime.now(timezone.utc).isoformat()

        if self._fallback_mode:
            self._fallback_store.append({
                "id": doc_id, "text": text, "metadata": metadata,
            })
        else:
            self._collection.add(
                ids=[doc_id],
                documents=[text],
                metadatas=[metadata],
            )
        return doc_id

    async def search(self, query: str, top_k: int = 5,
                     where: Dict = None) -> List[MemoryResult]:
        """Search for similar documents."""
        if self._fallback_mode:
            # Simple substring matching fallback
            results = []
            q_lower = query.lower()
            for doc in self._fallback_store:
                if q_lower in doc["text"].lower():
                    results.append(MemoryResult(
                        id=doc["id"], content=doc["text"],
                        metadata=doc["metadata"], distance=0.1,
                    ))
            return results[:top_k]

        kwargs = {"query_texts": [query], "n_results": min(top_k, self._collection.count() or 1)}
        if where:
            kwargs["where"] = where

        results = self._collection.query(**kwargs)
        
        memory_results = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                memory_results.append(MemoryResult(
                    id=results["ids"][0][i],
                    content=doc,
                    metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                    distance=results["distances"][0][i] if results["distances"] else 0.0,
                ))
        return memory_results

    async def delete(self, id: str) -> bool:
        """Delete a document."""
        if self._fallback_mode:
            self._fallback_store = [d for d in self._fallback_store if d["id"] != id]
            return True
        try:
            self._collection.delete(ids=[id])
            return True
        except Exception:
            return False

    @property
    def count(self) -> int:
        if self._fallback_mode:
            return len(self._fallback_store)
        return self._collection.count()


# ============================================================================
# Agent Memory
# ============================================================================

class AgentMemory:
    """
    Long-term agent memory using vector similarity search.
    
    Provides remember/recall/forget operations over the vector store.
    """

    def __init__(self, vector_store: ChromaVectorStore = None):
        self.store = vector_store or ChromaVectorStore()

    async def remember(self, content: str, context: str = "",
                       task_id: str = "", category: str = "general") -> str:
        """Store a memory."""
        metadata = {
            "context": context,
            "task_id": task_id,
            "category": category,
        }
        return await self.store.store(content, metadata)

    async def recall(self, query: str, limit: int = 5,
                     category: str = None) -> List[MemoryResult]:
        """Recall memories similar to query."""
        where = {"category": category} if category else None
        return await self.store.search(query, top_k=limit, where=where)

    async def forget(self, memory_id: str) -> bool:
        """Remove a memory."""
        return await self.store.delete(memory_id)


# ============================================================================
# Codebase RAG
# ============================================================================

# File extensions to index
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs",
    ".c", ".cpp", ".h", ".cs", ".rb", ".php", ".swift", ".kt",
    ".yaml", ".yml", ".json", ".toml", ".md", ".txt",
}


class CodebaseRAG:
    """
    Codebase semantic indexing and retrieval.
    
    Indexes source files by chunks and enables semantic search.
    Inspired by: Cursor's codebase indexing, Windsurf Codemaps
    """

    def __init__(self, vector_store: ChromaVectorStore = None,
                 persist_dir: str = "./data/codebase_index"):
        self._store = None
        self._persist_dir = persist_dir
        self._custom_store = vector_store
        self._indexed_files = 0

    @property
    def store(self):
        if self._store is None:
            if self._custom_store:
                self._store = self._custom_store
            else:
                self._store = ChromaVectorStore(persist_dir=self._persist_dir)
        return self._store

    async def index_workspace(self, workspace_path: str,
                               max_files: int = 500) -> Dict[str, Any]:
        """Index a workspace for semantic search."""
        indexed = 0
        skipped = 0
        errors = 0

        for root, dirs, files in os.walk(workspace_path):
            # Skip hidden/venv/node_modules
            dirs[:] = [d for d in dirs if not d.startswith('.')
                       and d not in ('node_modules', '__pycache__', '.venv', 'venv', '.git')]

            for fname in files:
                if indexed >= max_files:
                    break

                ext = os.path.splitext(fname)[1].lower()
                if ext not in CODE_EXTENSIONS:
                    skipped += 1
                    continue

                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    if len(content) > 50000:
                        content = content[:50000]

                    # Chunk by functions/classes (simple line-based chunking)
                    chunks = self._chunk_code(content, fpath)
                    for chunk in chunks:
                        rel_path = os.path.relpath(fpath, workspace_path)
                        await self.store.store(
                            chunk["content"],
                            metadata={
                                "file_path": rel_path,
                                "start_line": chunk["start_line"],
                                "end_line": chunk["end_line"],
                                "language": ext.lstrip('.'),
                                "type": "code",
                            },
                        )
                    indexed += 1
                except Exception as e:
                    errors += 1

        self._indexed_files = indexed
        logger.info(f"[CodebaseRAG] Indexed {indexed} files, skipped {skipped}, errors {errors}")
        return {"indexed": indexed, "skipped": skipped, "errors": errors}

    async def query(self, question: str, top_k: int = 5) -> List[CodeSnippet]:
        """Query indexed codebase by semantic meaning."""
        results = await self.store.search(question, top_k=top_k)
        snippets = []
        for r in results:
            snippets.append(CodeSnippet(
                file_path=r.metadata.get("file_path", ""),
                content=r.content,
                start_line=r.metadata.get("start_line", 0),
                end_line=r.metadata.get("end_line", 0),
                language=r.metadata.get("language", ""),
                score=1 - r.distance,
            ))
        return snippets

    def _chunk_code(self, content: str, file_path: str,
                    chunk_size: int = 60) -> List[Dict]:
        """Chunk code into segments for indexing."""
        lines = content.split('\n')
        chunks = []
        
        for i in range(0, len(lines), chunk_size):
            chunk_lines = lines[i:i + chunk_size]
            if not any(line.strip() for line in chunk_lines):
                continue
            chunks.append({
                "content": '\n'.join(chunk_lines),
                "start_line": i + 1,
                "end_line": min(i + chunk_size, len(lines)),
            })
        return chunks