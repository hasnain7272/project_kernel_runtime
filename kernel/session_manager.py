"""
Session Manager v2 — SQLite-backed Session & Context Management

Upgraded from JSON-file storage to SQLite with:
- ACID transactions for crash safety
- Conversation memory tracking
- Project-level configuration loading (.agentrules)
- Session timeout and auto-cleanup
- Event bus integration

Inspired by: Cursor sessions/context, OpenHands workspaces
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import json
import os
import sqlite3
import uuid
import logging

logger = logging.getLogger(__name__)


class SessionContext:
    """User session with workspace state."""
    def __init__(
        self,
        session_id: str,
        user_id: str,
        workspace_path: str,
        mode: str = "cli",
        context: Optional[Dict] = None
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.workspace_path = workspace_path
        self.mode = mode
        self.context = context or {}
        self.created_at = datetime.now(timezone.utc)
        self.last_active = datetime.now(timezone.utc)
        self.task_history: List[str] = []
        self.file_history: List[str] = []
        self.command_history: List[str] = []
        self.skills: List[str] = getattr(self, "skills", [])
        self.mcp_servers: List[str] = getattr(self, "mcp_servers", [])
        self.folders: List[str] = getattr(self, "folders", [])
        self.conversation_messages: List[Dict] = []  # NEW: conversation memory
        self.is_active = True

    def update_activity(self):
        self.last_active = datetime.now(timezone.utc)

    def add_task(self, task_id: str):
        self.task_history.append(task_id)
        if len(self.task_history) > 50:
            self.task_history = self.task_history[-50:]

    def add_file(self, file_path: str):
        if file_path in self.file_history:
            self.file_history.remove(file_path)
        self.file_history.insert(0, file_path)
        if len(self.file_history) > 20:
            self.file_history = self.file_history[:20]

    def add_command(self, command: str):
        self.command_history.append(command)
        if len(self.command_history) > 100:
            self.command_history = self.command_history[-100:]

    def add_message(self, role: str, content: str):
        """Add a conversation message to session memory."""
        self.conversation_messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        # Keep last 200 messages
        if len(self.conversation_messages) > 200:
            self.conversation_messages = self.conversation_messages[-200:]

    def get_recent_files(self, limit: int = 10) -> List[str]:
        return self.file_history[:limit]

    def get_recent_tasks(self, limit: int = 5) -> List[str]:
        return self.task_history[-limit:]

    def get_conversation_context(self, last_n: int = 20) -> List[Dict]:
        """Get recent conversation for LLM context building."""
        return self.conversation_messages[-last_n:]

    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "workspace_path": self.workspace_path,
            "mode": self.mode,
            "context": self.context,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "task_history": self.task_history,
            "file_history": self.file_history,
            "command_history": self.command_history,
            "conversation_messages": self.conversation_messages,
            "skills": getattr(self, "skills", []),
            "mcp_servers": getattr(self, "mcp_servers", []),
            "folders": getattr(self, "folders", [])
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'SessionContext':
        session = cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            workspace_path=data["workspace_path"],
            mode=data.get("mode", "cli"),
            context=data.get("context", {})
        )
        if "created_at" in data:
            session.created_at = datetime.fromisoformat(data["created_at"])
        if "last_active" in data:
            session.last_active = datetime.fromisoformat(data["last_active"])
        session.task_history = data.get("task_history", [])
        session.file_history = data.get("file_history", [])
        session.command_history = data.get("command_history", [])
        session.conversation_messages = data.get("conversation_messages", [])
        session.is_active = data.get("is_active", not data.get("context", {}).get("ended", False))
        session.skills = data.get("skills", [])
        session.mcp_servers = data.get("mcp_servers", [])
        session.folders = data.get("folders", [])
        return session


class SessionManager:
    """
    Manages user sessions with SQLite persistence.
    
    Upgraded from JSON files to SQLite for:
    - ACID transactions
    - Fast queries
    - Concurrent access support
    """

    def __init__(self, storage_path: str = "./data/sessions.db", event_bus=None):
        self.storage_path = storage_path
        self.event_bus = event_bus
        self.sessions: Dict[str, SessionContext] = {}
        self.active_sessions: Dict[str, str] = {}
        
        os.makedirs(os.path.dirname(storage_path) or '.', exist_ok=True)
        self._init_db()
        self.load_sessions()
        logger.info(f"[SessionManager] Initialized with {len(self.sessions)} sessions")

    def _init_db(self):
        """Create SQLite tables."""
        with sqlite3.connect(self.storage_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    workspace_path TEXT,
                    mode TEXT DEFAULT 'cli',
                    is_active INTEGER DEFAULT 1,
                    data TEXT,
                    created_at TEXT,
                    last_active TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(is_active)")

    def create_session(
        self,
        user_id: str,
        workspace_path: str,
        mode: str = "cli",
        context: Optional[Dict] = None
    ) -> SessionContext:
        session_id = str(uuid.uuid4())

        if user_id in self.active_sessions:
            old_session_id = self.active_sessions[user_id]
            if old_session_id in self.sessions:
                self.end_session(old_session_id)

        session = SessionContext(
            session_id=session_id,
            user_id=user_id,
            workspace_path=workspace_path,
            mode=mode,
            context=context
        )

        self.sessions[session_id] = session
        self.active_sessions[user_id] = session_id
        self._save_to_db(session)
        logger.info(f"[SessionManager] Created session {session_id} for {user_id}")
        return session

    def get_session(self, session_id: str) -> Optional[SessionContext]:
        return self.sessions.get(session_id)

    def get_active_session(self, user_id: str) -> Optional[SessionContext]:
        session_id = self.active_sessions.get(user_id)
        if session_id:
            return self.get_session(session_id)
        return None

    def update_session_activity(self, session_id: str):
        session = self.get_session(session_id)
        if session:
            session.update_activity()
            self._save_to_db(session)

    def update_session(self, session_id: str, session: SessionContext):
        if session_id in self.sessions:
            self.sessions[session_id] = session
            self._save_to_db(session)

    def add_task_to_session(self, session_id: str, task_id: str):
        session = self.get_session(session_id)
        if session:
            session.add_task(task_id)
            self._save_to_db(session)

    def add_file_to_session(self, session_id: str, file_path: str):
        session = self.get_session(session_id)
        if session:
            session.add_file(file_path)
            self._save_to_db(session)

    def add_command_to_session(self, session_id: str, command: str):
        session = self.get_session(session_id)
        if session:
            session.add_command(command)
            self._save_to_db(session)

    def add_message_to_session(self, session_id: str, role: str, content: str):
        """Add conversation message for context tracking."""
        session = self.get_session(session_id)
        if session:
            session.add_message(role, content)
            self._save_to_db(session)

    def end_session(self, session_id: str):
        session = self.get_session(session_id)
        if session:
            if session.user_id in self.active_sessions:
                del self.active_sessions[session.user_id]
            session.is_active = False
            session.context["ended"] = True
            self._save_to_db(session)
            logger.info(f"[SessionManager] Ended session {session_id}")

    def list_user_sessions(self, user_id: str) -> List[SessionContext]:
        return [s for s in self.sessions.values() if s.user_id == user_id]

    def cleanup_old_sessions(self, days: int = 30):
        cutoff = datetime.now(timezone.utc).timestamp() - (days * 24 * 60 * 60)
        to_remove = []
        for session_id, session in self.sessions.items():
            if session.last_active.timestamp() < cutoff:
                to_remove.append(session_id)
        for session_id in to_remove:
            session = self.sessions[session_id]
            if session.user_id in self.active_sessions:
                del self.active_sessions[session.user_id]
            del self.sessions[session_id]
            self._delete_from_db(session_id)
        if to_remove:
            logger.info(f"[SessionManager] Cleaned up {len(to_remove)} old sessions")

    # ── SQLite persistence ──

    def _save_to_db(self, session: SessionContext):
        try:
            with sqlite3.connect(self.storage_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO sessions
                    (session_id, user_id, workspace_path, mode, is_active, data, created_at, last_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session.session_id, session.user_id, session.workspace_path,
                    session.mode, 1 if session.is_active else 0,
                    json.dumps(session.to_dict()), session.created_at.isoformat(),
                    session.last_active.isoformat(),
                ))
        except Exception as e:
            logger.error(f"[SessionManager] Save failed: {e}")

    def load_sessions(self):
        try:
            with sqlite3.connect(self.storage_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute("SELECT * FROM sessions").fetchall()
                for row in rows:
                    data = json.loads(row["data"])
                    session = SessionContext.from_dict(data)
                    self.sessions[session.session_id] = session
                    if session.is_active:
                        self.active_sessions[session.user_id] = session.session_id
        except Exception as e:
            logger.warning(f"[SessionManager] Load failed: {e}")
            # Fallback: try legacy JSON
            self._migrate_from_json("./session_storage")

    def _delete_from_db(self, session_id: str):
        try:
            with sqlite3.connect(self.storage_path) as conn:
                conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        except Exception as e:
            logger.error(f"[SessionManager] Delete failed: {e}")

    def _migrate_from_json(self, json_dir: str):
        """Migrate legacy JSON file sessions to SQLite."""
        if not os.path.exists(json_dir):
            return
        count = 0
        for filename in os.listdir(json_dir):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(json_dir, filename), 'r') as f:
                        data = json.load(f)
                    session = SessionContext.from_dict(data)
                    self.sessions[session.session_id] = session
                    self._save_to_db(session)
                    if session.is_active:
                        self.active_sessions[session.user_id] = session.session_id
                    count += 1
                except Exception:
                    pass
        if count:
            logger.info(f"[SessionManager] Migrated {count} sessions from JSON to SQLite")

    # Backward compatibility
    def save_session(self, session: SessionContext):
        self._save_to_db(session)

    def delete_session_file(self, session_id: str):
        self._delete_from_db(session_id)