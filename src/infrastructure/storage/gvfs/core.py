"""Core GVFS implementation."""
import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import shutil
from .models.session_mount import SessionMount
from .models.virtual_file import VirtualFile
from .operations.clone import clone_repository
from .operations.persistence import restore_mount_state, save_mount_state
from .api.filesystem import FilesystemAPI
from .api.changes import ChangesAPI
from .api.git_ops import GitOperationsAPI

logger = logging.getLogger(__name__)


class GitVirtualFileSystem:
    """Virtual filesystem manager for Git-mounted sessions."""
    
    def __init__(self, session_storage_path: Path):
        self._storage_path = session_storage_path
        self._mounts: Dict[str, SessionMount] = {}
        self._lock = asyncio.Lock()
        self._fs_api = FilesystemAPI(session_storage_path)
        self._changes_api = ChangesAPI(session_storage_path)
        self._git_api = GitOperationsAPI(session_storage_path)
    
    async def mount_repository(
        self,
        session_id: str,
        repo_url: str,
        branch: str = "main",
        commit_sha: Optional[str] = None,
        auth_token: Optional[str] = None
    ) -> SessionMount:
        """Mount a Git repository for a session."""
        async with self._lock:
            if session_id in self._mounts:
                mount = self._mounts[session_id]
                if mount.repo_url == repo_url and mount.branch == branch:
                    return mount
            
            mount = SessionMount(
                session_id=session_id,
                repo_url=repo_url,
                branch=branch,
                commit_sha=commit_sha,
                auth_token=auth_token
            )
            
            await self._initialize_mount(mount)
            self._mounts[session_id] = mount
            
            logger.info(f"[GVFS] Mounted {repo_url}@{branch} for session {session_id}")
            return mount
    
    async def _initialize_mount(self, mount: SessionMount):
        """Initialize the mount by cloning or restoring."""
        # Align with agent's expected topology: /workspace/repos/<repo_name>
        repo_name = mount.repo_url.split("/")[-1].replace(".git", "")
        
        # We need to find the session's folder. 
        # For simplicity in this runtime, we'll look it up or derive it.
        # Ideally we should pass tenant_id, but we can derive it from the DB.
        from src.infrastructure.db.session import get_db_context
        from src.infrastructure.db.models.session_model import SessionModel
        from sqlalchemy import select
        from src.infrastructure.runtime.paths import get_session_root
        
        async with get_db_context() as db:
            result = await db.execute(select(SessionModel.tenant_id).where(SessionModel.id == mount.session_id))
            tenant_id = result.scalar_one_or_none() or "local"
        
        session_root = get_session_root(tenant_id, mount.session_id)
        session_dir = session_root / "repos" / repo_name
        session_dir.mkdir(parents=True, exist_ok=True)
        mount.local_path = session_dir
        
        state_file = self._storage_path / "sessions" / mount.session_id / "vfs_state.json"
        
        if state_file.exists():
            await restore_mount_state(mount, state_file)
        else:
            await clone_repository(mount)
        
        mount.loaded = True
        mount.last_sync = datetime.utcnow()
    
    async def read_file(self, session_id: str, path: str, load_content: bool = True):
        mount = self._mounts.get(session_id)
        if not mount:
            raise ValueError(f"No mount found for session {session_id}")
        return await self._fs_api.read_file(mount, path, load_content)
    
    async def write_file(self, session_id: str, path: str, content: bytes):
        mount = self._mounts.get(session_id)
        if not mount:
            raise ValueError(f"No mount found for session {session_id}")
        return await self._fs_api.write_file(mount, path, content)
    
    async def delete_file(self, session_id: str, path: str):
        mount = self._mounts.get(session_id)
        if not mount:
            return False
        return await self._fs_api.delete_file(mount, path)
    
    async def list_directory(self, session_id: str, path: str = "."):
        mount = self._mounts.get(session_id)
        if not mount:
            return []
        return await self._fs_api.list_directory(mount, path)
    
    async def get_changes(self, session_id: str):
        mount = self._mounts.get(session_id)
        if not mount:
            return {"modified": [], "added": [], "deleted": []}
        return self._changes_api.get_changes(mount)
    
    async def get_diff(self, session_id: str, path: str):
        from .operations.diff import generate_diff
        mount = self._mounts.get(session_id)
        if not mount:
            return None
        vfile = await self.read_file(session_id, path, load_content=True)
        return generate_diff(vfile)
    
    async def apply_to_workspace(self, session_id: str, workspace_path: Path):
        mount = self._mounts.get(session_id)
        if not mount:
            return {"applied": 0, "errors": ["No mount found"]}
        return await self._changes_api.apply_to_workspace(mount, workspace_path)
    
    async def commit_changes(self, session_id: str, message: str, author: Optional[str] = None):
        mount = self._mounts.get(session_id)
        if not mount:
            return {"success": False, "error": "No mount found"}
        return await self._git_api.commit_changes(mount, message, author)
    
    async def unmount(self, session_id: str, persist: bool = True):
        async with self._lock:
            mount = self._mounts.pop(session_id, None)
            if mount:
                await self._git_api.unmount(mount, persist)