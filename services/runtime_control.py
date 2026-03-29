import asyncio
import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RuntimeJob:
    id: str
    kind: str
    status: str
    payload: Dict[str, Any]
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    artifact_id: Optional[str]
    created_at: str
    updated_at: str
    started_at: Optional[str]
    finished_at: Optional[str]


class RuntimeControlPlane:
    def __init__(self, db_path: Optional[str] = None, max_concurrency: int = 2):
        base_dir = Path(__file__).resolve().parent.parent / "data"
        base_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = str(Path(db_path) if db_path else base_dir / "runtime_control.db")
        self.max_concurrency = max_concurrency
        self._live_tasks: Dict[str, asyncio.Task] = {}
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._init_db()
        self._mark_interrupted_jobs()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    result TEXT,
                    error TEXT,
                    artifact_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def _mark_interrupted_jobs(self):
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status = 'interrupted',
                    error = COALESCE(error, 'Process restarted while job was running'),
                    updated_at = ?,
                    finished_at = ?
                WHERE status IN ('queued', 'running')
                """,
                (_utcnow(), _utcnow()),
            )

    def _row_to_job(self, row: sqlite3.Row) -> RuntimeJob:
        return RuntimeJob(
            id=row["id"],
            kind=row["kind"],
            status=row["status"],
            payload=json.loads(row["payload"]),
            result=json.loads(row["result"]) if row["result"] else None,
            error=row["error"],
            artifact_id=row["artifact_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
        )

    def list_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_job(row).__dict__ for row in rows]

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return self._row_to_job(row).__dict__ if row else None

    def list_artifacts(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, name, type, metadata, created_at FROM artifacts ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        artifacts = []
        for row in rows:
            artifacts.append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "type": row["type"],
                    "metadata": json.loads(row["metadata"]),
                    "created_at": row["created_at"],
                }
            )
        return artifacts

    def get_artifact(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM artifacts WHERE id = ?", (artifact_id,)).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "name": row["name"],
            "type": row["type"],
            "content": json.loads(row["content"]),
            "metadata": json.loads(row["metadata"]),
            "created_at": row["created_at"],
        }

    def create_artifact(
        self,
        name: str,
        artifact_type: str,
        content: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        artifact_id = f"artifact_{uuid4().hex[:10]}"
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO artifacts (id, name, type, content, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    artifact_id,
                    name,
                    artifact_type,
                    json.dumps(content, default=str),
                    json.dumps(metadata or {}, default=str),
                    _utcnow(),
                ),
            )
        return artifact_id

    async def create_job(self, orchestrator, kind: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        job_id = f"job_{uuid4().hex[:10]}"
        timestamp = _utcnow()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs (id, kind, status, payload, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    kind,
                    "queued",
                    json.dumps(payload, default=str),
                    timestamp,
                    timestamp,
                ),
            )
        self._live_tasks[job_id] = asyncio.create_task(self._run_job(orchestrator, job_id, kind, payload))
        return self.get_job(job_id)

    async def cancel_job(self, job_id: str) -> Dict[str, Any]:
        task = self._live_tasks.get(job_id)
        if task and not task.done():
            task.cancel()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status = 'cancelled', updated_at = ?, finished_at = ?
                WHERE id = ?
                """,
                (_utcnow(), _utcnow(), job_id),
            )
        return self.get_job(job_id)

    async def _run_job(self, orchestrator, job_id: str, kind: str, payload: Dict[str, Any]):
        async with self._semaphore:
            self._update_job(job_id, status="running", started_at=_utcnow())
            try:
                result = await self._execute_job(orchestrator, kind, payload)
                artifact_id = self.create_artifact(
                    name=f"{kind}:{job_id}",
                    artifact_type=kind,
                    content=result,
                    metadata={"job_id": job_id, "kind": kind},
                )
                self._update_job(
                    job_id,
                    status="completed",
                    result=result,
                    artifact_id=artifact_id,
                    finished_at=_utcnow(),
                )
            except asyncio.CancelledError:
                self._update_job(
                    job_id,
                    status="cancelled",
                    error="Cancelled by user",
                    finished_at=_utcnow(),
                )
                raise
            except Exception as exc:
                self._update_job(
                    job_id,
                    status="failed",
                    error=str(exc),
                    finished_at=_utcnow(),
                )
            finally:
                self._live_tasks.pop(job_id, None)

    async def _ensure_session(self, orchestrator, user_id: str, workspace_path: Optional[str], mode: str = "job") -> Optional[str]:
        if not user_id:
            return None

        existing = await orchestrator.get_session_context(user_id)
        if existing and (not workspace_path or existing.workspace_path == workspace_path):
            return existing.session_id

        if workspace_path:
            session = await orchestrator.start_session(user_id, workspace_path, mode)
            return session.session_id

        return existing.session_id if existing else None

    def _update_job(self, job_id: str, **fields):
        allowed = {
            "status",
            "result",
            "error",
            "artifact_id",
            "updated_at",
            "started_at",
            "finished_at",
        }
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        updates.setdefault("updated_at", _utcnow())
        assignments = []
        values: List[Any] = []
        for key, value in updates.items():
            assignments.append(f"{key} = ?")
            if key == "result" and value is not None:
                values.append(json.dumps(value, default=str))
            else:
                values.append(value)
        values.append(job_id)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE jobs SET {', '.join(assignments)} WHERE id = ?",
                values,
            )

    async def _execute_job(self, orchestrator, kind: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if kind == "agent_execute":
            session_id = payload.get("session_id") or await self._ensure_session(
                orchestrator,
                payload.get("user_id", "api_user"),
                payload.get("workspace_path"),
            )
            return await orchestrator.execute_agentic_loop(
                payload["description"],
                user_id=payload.get("user_id", "api_user"),
                session_id=session_id,
                max_iterations=int(payload.get("max_iterations", 8)),
            )

        if kind == "index_workspace":
            workspace_path = payload["workspace_path"]
            max_files = int(payload.get("max_files", 200))
            return await orchestrator.vector_db.codebase_rag.index_workspace(
                workspace_path,
                max_files=max_files,
            )

        if kind == "tool_call":
            session_id = payload.get("session_id") or await self._ensure_session(
                orchestrator,
                payload.get("user_id", "api_user"),
                payload.get("workspace_path"),
            )
            result = await orchestrator.call_tool(
                payload.get("user_id", "api_user"),
                payload["tool_name"],
                payload.get("arguments", {}),
                session_id,
            )
            return {
                "tool_name": result.tool_name,
                "success": result.success,
                "output": result.output,
                "error": result.error,
                "duration_ms": result.duration_ms,
            }

        if kind == "research_summary":
            session = await orchestrator.start_research_session(
                payload.get("user_id", "api_user"),
                payload["query"],
                payload.get("params", {}),
            )
            for source in payload.get("sources", []):
                await orchestrator.add_research_source(
                    payload.get("user_id", "api_user"),
                    session.session_id,
                    source["uri"],
                    source.get("type", "web"),
                )
            report = await orchestrator.summarize_session(
                payload.get("user_id", "api_user"),
                session.session_id,
                payload.get("strategy", "default"),
            )
            return {
                "session_id": session.session_id,
                "report_id": report.id,
                "summary": report.summary,
            }

        raise ValueError(f"Unsupported job kind: {kind}")


_control_plane: Optional[RuntimeControlPlane] = None


def get_control_plane() -> RuntimeControlPlane:
    global _control_plane
    if _control_plane is None:
        _control_plane = RuntimeControlPlane()
    return _control_plane
