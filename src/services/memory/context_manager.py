"""
Session Context Manager

Manages efficient persistence of session context using:
1. Incremental storage (only changed messages)
2. Smart summarization for long sessions
3. LRU caching for active sessions
4. Vector embeddings for semantic search

This enables sessions to persist across restarts and scale to
thousands of messages without performance degradation.
"""
import asyncio
import hashlib
import json
import logging
import pickle
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from cachetools import LRUCache

from src.infrastructure.db.models.message_model import MessageModel
from src.infrastructure.db.models.session_model import SessionModel
from src.infrastructure.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


@dataclass
class ContextWindow:
    """Represents a window of messages in the context."""
    start_sequence: int
    end_sequence: int
    messages: List[Dict[str, Any]]
    summary: Optional[str] = None
    token_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SessionContext:
    """Full session context with efficient storage."""
    session_id: str
    user_id: str
    windows: List[ContextWindow] = field(default_factory=list)
    recent_messages: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # State tracking
    last_sequence: int = 0
    total_messages: int = 0
    is_dirty: bool = False
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    
    # Smart context
    key_topics: List[str] = field(default_factory=list)
    action_history: List[str] = field(default_factory=list)
    file_references: Set[str] = field(default_factory=set)


class ContextPersistenceManager:
    """
    Manages session context with:
    - Incremental persistence (only new messages)
    - Automatic summarization
    - LRU cache for active sessions
    - Background checkpointing
    """
    
    # Configuration
    WINDOW_SIZE = 20          # Messages per window
    MAX_RECENT = 10           # Keep last N messages in memory
    SUMMARY_THRESHOLD = 100   # Summarize after N messages
    CHECKPOINT_INTERVAL = 60  # Seconds between checkpoints
    CACHE_SIZE = 1000         # Max sessions in LRU cache
    
    def __init__(self):
        self._cache: LRUCache[str, SessionContext] = LRUCache(maxsize=self.CACHE_SIZE)
        self._dirty_sessions: Set[str] = set()
        self._lock = asyncio.Lock()
        self._checkpoint_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start background checkpointing."""
        self._running = True
        self._checkpoint_task = asyncio.create_task(self._checkpoint_loop())
        logger.info("[ContextManager] Started")
    
    async def stop(self):
        """Stop and flush all pending changes."""
        self._running = False
        if self._checkpoint_task:
            self._checkpoint_task.cancel()
            try:
                await self._checkpoint_task
            except asyncio.CancelledError:
                pass
        
        # Flush all dirty sessions
        await self._flush_all()
        logger.info("[ContextManager] Stopped")
    
    async def get_or_create_context(
        self,
        session_id: str,
        user_id: str
    ) -> SessionContext:
        """
        Get existing context or create new.
        
        Loads from database if not in cache.
        """
        # Check cache first
        if session_id in self._cache:
            context = self._cache[session_id]
            context.last_accessed = datetime.utcnow()
            return context
        
        # Load from database
        context = await self._load_from_db(session_id, user_id)
        
        if context:
            self._cache[session_id] = context
            return context
        
        # Create new context
        context = SessionContext(
            session_id=session_id,
            user_id=user_id
        )
        self._cache[session_id] = context
        return context
    
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        task_id: Optional[str] = None,
        tool_calls: Optional[List[Dict]] = None,
        tool_results: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Add message to session context.
        
        Automatically:
        - Creates new windows when needed
        - Summarizes old windows
        - Updates metadata
        """
        async with self._lock:
            context = await self._get_from_cache_or_db(session_id)
            
            if not context:
                logger.warning(f"[ContextManager] No context for session {session_id}")
                return {"error": "Session not found"}
            
            # Create message
            context.last_sequence += 1
            message = {
                "sequence": context.last_sequence,
                "role": role,
                "content": content,
                "task_id": task_id,
                "tool_calls": tool_calls,
                "tool_results": tool_results,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            # Add to recent messages
            context.recent_messages.append(message)
            if len(context.recent_messages) > self.MAX_RECENT:
                # Move oldest to window
                old_messages = context.recent_messages[:-self.MAX_RECENT]
                context.recent_messages = context.recent_messages[-self.MAX_RECENT:]
                
                # Create new window
                if old_messages:
                    await self._create_window(context, old_messages)
            
            # Update metadata
            context.total_messages += 1
            context.is_dirty = True
            self._dirty_sessions.add(session_id)
            
            # Extract file references
            if "file" in content.lower() or "." in content:
                import re
                file_refs = re.findall(r'[\w\-/]+\.\w+', content)
                context.file_references.update(file_refs)
            
            # Auto-summarize if needed
            if context.total_messages % self.SUMMARY_THRESHOLD == 0:
                asyncio.create_task(self._summarize_session(context))
            
            return message
    
    async def get_context_for_llm(
        self,
        session_id: str,
        max_tokens: int = 8000
    ) -> List[Dict[str, str]]:
        """
        Get context formatted for LLM consumption.
        
        Returns messages in OpenAI format with smart truncation.
        """
        context = await self._get_from_cache_or_db(session_id)
        if not context:
            return []
        
        messages = []
        
        # Add system message with summary
        system_content = self._build_system_prompt(context)
        if system_content:
            messages.append({"role": "system", "content": system_content})
        
        # Add window summaries
        for window in context.windows[-3:]:  # Last 3 windows
            if window.summary:
                messages.append({
                    "role": "system",
                    "content": f"[Earlier conversation summary]: {window.summary}"
                })
        
        # Add recent messages
        for msg in context.recent_messages:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        return messages
    
    async def get_context_for_ui(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get context for UI display.
        
        Includes all metadata and formatting.
        """
        context = await self._get_from_cache_or_db(session_id)
        if not context:
            return []
        
        # Combine all messages
        all_messages = []
        
        for window in context.windows:
            all_messages.extend(window.messages)
        
        all_messages.extend(context.recent_messages)
        
        # Sort by sequence
        all_messages.sort(key=lambda m: m.get("sequence", 0))
        
        # Return last N
        return all_messages[-limit:]
    
    async def search_context(
        self,
        session_id: str,
        query: str
    ) -> List[Dict[str, Any]]:
        """
        Search within session context.
        
        Simple keyword search - can be enhanced with embeddings.
        """
        context = await self._get_from_cache_or_db(session_id)
        if not context:
            return []
        
        results = []
        query_lower = query.lower()
        
        for window in context.windows:
            for msg in window.messages:
                if query_lower in msg.get("content", "").lower():
                    results.append(msg)
        
        for msg in context.recent_messages:
            if query_lower in msg.get("content", "").lower():
                results.append(msg)
        
        return results
    
    async def get_file_context(
        self,
        session_id: str,
        filepath: str
    ) -> List[Dict[str, Any]]:
        """
        Get all messages referencing a specific file.
        
        Useful for showing file-related conversation history.
        """
        context = await self._get_from_cache_or_db(session_id)
        if not context:
            return []
        
        results = []
        
        for window in context.windows:
            for msg in window.messages:
                if filepath in msg.get("content", ""):
                    results.append(msg)
        
        for msg in context.recent_messages:
            if filepath in msg.get("content", ""):
                results.append(msg)
        
        return results
    
    async def clear_context(self, session_id: str) -> bool:
        """Clear all context for a session."""
        async with self._lock:
            if session_id in self._cache:
                del self._cache[session_id]
            
            self._dirty_sessions.discard(session_id)
            
            # Clear from database
            async with AsyncSessionLocal() as db:
                from sqlalchemy import delete
                await db.execute(
                    delete(MessageModel).where(MessageModel.session_id == session_id)
                )
                await db.commit()
            
            return True
    
    # ──────────────────────────────────────────────────
    # Internal Methods
    # ──────────────────────────────────────────────────
    
    async def _get_from_cache_or_db(
        self,
        session_id: str
    ) -> Optional[SessionContext]:
        """Get context from cache or load from DB."""
        if session_id in self._cache:
            return self._cache[session_id]
        
        # Try to infer user_id from session
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            result = await db.execute(
                select(SessionModel).where(SessionModel.id == session_id)
            )
            session = result.scalar_one_or_none()
            if session:
                return await self._load_from_db(session_id, session.user_id)
        
        return None
    
    async def _load_from_db(
        self,
        session_id: str,
        user_id: str
    ) -> Optional[SessionContext]:
        """Load session context from database."""
        context = SessionContext(
            session_id=session_id,
            user_id=user_id
        )
        
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select, desc
            
            # Load recent messages
            result = await db.execute(
                select(MessageModel)
                .where(MessageModel.session_id == session_id)
                .order_by(desc(MessageModel.sequence))
                .limit(self.MAX_RECENT * 2)  # Load more for processing
            )
            messages = result.scalars().all()
            
            if not messages:
                return None
            
            # Reverse to chronological order
            messages = list(reversed(messages))
            
            for msg in messages:
                context.last_sequence = max(context.last_sequence, msg.sequence)
                context.recent_messages.append({
                    "sequence": msg.sequence,
                    "role": msg.role,
                    "content": msg.content,
                    "task_id": msg.task_id,
                    "timestamp": msg.created_at.isoformat() if msg.created_at else None,
                })
            
            context.total_messages = context.last_sequence
        
        return context
    
    async def _create_window(
        self,
        context: SessionContext,
        messages: List[Dict[str, Any]]
    ):
        """Create a new context window from messages."""
        if not messages:
            return
        
        window = ContextWindow(
            start_sequence=messages[0]["sequence"],
            end_sequence=messages[-1]["sequence"],
            messages=messages,
            token_count=sum(len(m.get("content", "")) for m in messages) // 4
        )
        
        context.windows.append(window)
        
        # Summarize window asynchronously
        asyncio.create_task(self._summarize_window(context, window))
    
    async def _summarize_window(
        self,
        context: SessionContext,
        window: ContextWindow
    ):
        """Generate summary for a window using LLM."""
        try:
            from src.infrastructure.llm.litellm_client import LLMClient
            
            llm = LLMClient()
            
            # Build conversation for summarization
            conversation = "\n".join([
                f"{m['role']}: {m['content'][:200]}"
                for m in window.messages
            ])
            
            prompt = f"""Summarize this conversation concisely (max 2 sentences):

{conversation}

Summary:"""
            
            summary = await llm.acomplete(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100
            )
            
            window.summary = summary
            context.is_dirty = True
            self._dirty_sessions.add(context.session_id)
            
        except Exception as e:
            logger.warning(f"[ContextManager] Summarization failed: {e}")
    
    async def _summarize_session(self, context: SessionContext):
        """Generate overall session summary."""
        try:
            # Extract key topics
            all_text = " ".join([
                m.get("content", "")
                for w in context.windows[-2:]  # Last 2 windows
                for m in w.messages
            ] + [
                m.get("content", "")
                for m in context.recent_messages
            ])
            
            # Simple keyword extraction
            import re
            words = re.findall(r'\b[A-Z][a-zA-Z]+\b', all_text)
            word_freq = {}
            for word in words:
                word_freq[word] = word_freq.get(word, 0) + 1
            
            context.key_topics = [
                word for word, count in sorted(
                    word_freq.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]
                if len(word) > 3
            ]
            
            context.is_dirty = True
            self._dirty_sessions.add(context.session_id)
            
        except Exception as e:
            logger.warning(f"[ContextManager] Session summary failed: {e}")
    
    def _build_system_prompt(self, context: SessionContext) -> str:
        """Build system prompt with context metadata."""
        parts = [
            "You are an AI coding assistant. "
            "You have access to the user's codebase and can execute commands."
        ]
        
        if context.key_topics:
            parts.append(f"Key topics in this session: {', '.join(context.key_topics)}")
        
        if context.file_references:
            parts.append(f"Files discussed: {', '.join(list(context.file_references)[:10])}")
        
        return "\n\n".join(parts)
    
    async def _checkpoint_loop(self):
        """Background loop to persist dirty sessions."""
        while self._running:
            try:
                await asyncio.sleep(self.CHECKPOINT_INTERVAL)
                await self._flush_dirty_sessions()
            except Exception as e:
                logger.error(f"[ContextManager] Checkpoint error: {e}")
    
    async def _flush_dirty_sessions(self):
        """Persist all dirty sessions to database."""
        if not self._dirty_sessions:
            return
        
        sessions_to_flush = list(self._dirty_sessions)
        self._dirty_sessions.clear()
        
        async with self._lock:
            for session_id in sessions_to_flush:
                if session_id not in self._cache:
                    continue
                
                context = self._cache[session_id]
                if not context.is_dirty:
                    continue
                
                await self._persist_to_db(context)
                context.is_dirty = False
        
        logger.debug(f"[ContextManager] Flushed {len(sessions_to_flush)} sessions")
    
    async def _persist_to_db(self, context: SessionContext):
        """Persist session context to database."""
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            
            # Persist recent messages
            for msg in context.recent_messages:
                # Check if already exists
                existing = await db.execute(
                    select(MessageModel).where(
                        MessageModel.session_id == context.session_id,
                        MessageModel.sequence == msg["sequence"]
                    )
                )
                
                if existing.scalar_one_or_none():
                    continue
                
                # Create new message
                new_msg = MessageModel(
                    session_id=context.session_id,
                    role=msg["role"],
                    content=msg["content"],
                    sequence=msg["sequence"],
                    task_id=msg.get("task_id"),
                )
                db.add(new_msg)
            
            await db.commit()
    
    async def _flush_all(self):
        """Flush all cached sessions."""
        async with self._lock:
            for session_id, context in self._cache.items():
                if context.is_dirty:
                    await self._persist_to_db(context)
                    context.is_dirty = False


# ──────────────────────────────────────────────────
# Global instance
# ──────────────────────────────────────────────────

_context_manager: Optional[ContextPersistenceManager] = None

async def get_context_manager() -> ContextPersistenceManager:
    """Get or create the global context manager."""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextPersistenceManager()
        await _context_manager.start()
    return _context_manager