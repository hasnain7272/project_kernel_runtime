"""
Git Virtual File System (GVFS)

Provides a session-scoped virtual filesystem over Git repositories.
Changes are tracked separately from the working tree, enabling:
- Multiple sessions on same repo
- Non-destructive editing
- Easy rollback and comparison
"""
import asyncio
import base64
import hashlib
import json
import logging
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import aiofiles

from src.infrastructure.db.models.session_model import SessionModel
from src.infrastructure.security.crypto import decrypt_string

logger = logging.getLogger(__name__)


class FileStatus(Enum):
    """Virtual file status relative to Git HEAD."""
    UNCHANGED = "unchanged"      # Same as HEAD
    MODIFIED = "modified"          # Modified from HEAD
    ADDED = "added"                # New file (not in HEAD)
    DELETED = "deleted"            # Deleted from HEAD
    CONFLICT = "conflict"          # Merge conflict
    UNTRACKED = "untracked"        # Not tracked by Git


@dataclass
class VirtualFile:
    """Represents a file in the virtual filesystem."""
    path: str                           # Relative path from repo root
    content: Optional[bytes] = None     # File content (None if not loaded)
    sha: str = ""                       # Content hash
    size: int = 0
    status: FileStatus = FileStatus.UNCHANGED
    created_at: datetime = field(default_factory=datetime.utcnow)
    modified_at: datetime = field(default_factory=datetime.utcnow)
    is_binary: bool = False
    
    # Git metadata
    head_sha: Optional[str] = None      # SHA at HEAD
    head_content: Optional[bytes] = None  # Content at HEAD (for diff)
    
    @property
    def has_changes(self) -> bool:
        return self.status in (FileStatus.MODIFIED, FileStatus.ADDED, FileStatus.DELETED)


@dataclass  
class SessionMount:
    """Git repository mount for a session."""
    session_id: str
    repo_url: str
    branch: str = "main"
    commit_sha: Optional[str] = None
    local_path: Optional[Path] = None     # Local clone path (ephemeral)
    virtual_root: str = "/workspace"      # Virtual path exposed to tools
    auth_token: Optional[str] = None     # Encrypted Git auth
    
    # State tracking
    files: Dict[str, VirtualFile] = field(default_factory=dict)
    loaded: bool = False
    last_sync: Optional[datetime] = None


class GitVirtualFileSystem:
    """
    Virtual filesystem manager for Git-mounted sessions.
    
    Architecture:
    1. Clone repo to ephemeral storage (or use existing)
    2. Track changes in virtual overlay
    3. Persist only deltas to session storage
    4. Lazy-load file contents
    """
    
    def __init__(self, session_storage_path: Path):
        self._storage_path = session_storage_path
        self._mounts: Dict[str, SessionMount] = {}
        self._lock = asyncio.Lock()
        
    async def mount_repository(
        self,
        session_id: str,
        repo_url: str,
        branch: str = "main",
        commit_sha: Optional[str] = None,
        auth_token: Optional[str] = None
    ) -> SessionMount:
        """
        Mount a Git repository for a session.
        
        If the session already has a mount, returns existing mount.
        If commit_sha provided, checks out specific commit (detached HEAD).
        """
        async with self._lock:
            # Return existing mount if present
            if session_id in self._mounts:
                mount = self._mounts[session_id]
                if mount.repo_url == repo_url and mount.branch == branch:
                    logger.info(f"[GVFS] Returning existing mount for {session_id}")
                    return mount
            
            # Create new mount
            mount = SessionMount(
                session_id=session_id,
                repo_url=repo_url,
                branch=branch,
                commit_sha=commit_sha,
                auth_token=auth_token
            )
            
            # Clone or restore from session storage
            await self._initialize_mount(mount)
            self._mounts[session_id] = mount
            
            logger.info(f"[GVFS] Mounted {repo_url}@{branch} for session {session_id}")
            return mount
    
    async def _initialize_mount(self, mount: SessionMount):
        """Initialize the mount by cloning or restoring."""
        # Create ephemeral directory for this session
        session_dir = self._storage_path / "sessions" / mount.session_id / "repo"
        session_dir.mkdir(parents=True, exist_ok=True)
        mount.local_path = session_dir
        
        # Check if we have persisted state
        state_file = self._storage_path / "sessions" / mount.session_id / "vfs_state.json"
        
        if state_file.exists():
            # Restore from persisted state
            await self._restore_mount_state(mount, state_file)
        else:
            # Fresh clone
            await self._clone_repository(mount)
        
        mount.loaded = True
        mount.last_sync = datetime.utcnow()
    
    async def _clone_repository(self, mount: SessionMount):
        """Clone repository to ephemeral storage."""
        import subprocess
        
        cmd = ["git", "clone", "--depth", "1", "--branch", mount.branch]
        
        if mount.commit_sha:
            # Clone then checkout specific commit
            cmd = ["git", "clone", mount.repo_url, str(mount.local_path)]
        else:
            cmd.extend([mount.repo_url, str(mount.local_path)])
        
        # Handle auth
        env = os.environ.copy()
        if mount.auth_token:
            token = decrypt_string(mount.auth_token)
            if "github.com" in mount.repo_url:
                env["GITHUB_TOKEN"] = token
                # Rewrite URL with token
                mount.repo_url = mount.repo_url.replace(
                    "https://github.com/",
                    f"https://{token}@github.com/"
                )
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            raise RuntimeError(f"Git clone failed: {stderr.decode()}")
        
        # Checkout specific commit if provided
        if mount.commit_sha:
            checkout_proc = await asyncio.create_subprocess_exec(
                "git", "checkout", mount.commit_sha,
                cwd=str(mount.local_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await checkout_proc.communicate()
        
        # Build initial file index
        await self._index_repository(mount)
    
    async def _index_repository(self, mount: SessionMount):
        """Build virtual file index from repository."""
        import subprocess
        
        # Get file list from Git
        proc = await asyncio.create_subprocess_exec(
            "git", "ls-tree", "-r", "HEAD",
            cwd=str(mount.local_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, _ = await proc.communicate()
        
        for line in stdout.decode().strip().split("\n"):
            if not line:
                continue
            # Parse: <mode> <type> <sha> <tab> <path>
            parts = line.split("\t")
            if len(parts) == 2:
                meta, path = parts
                sha = meta.split()[2]
                
                mount.files[path] = VirtualFile(
                    path=path,
                    sha=sha,
                    status=FileStatus.UNCHANGED,
                    head_sha=sha
                )
        
        logger.info(f"[GVFS] Indexed {len(mount.files)} files")
    
    async def read_file(
        self,
        session_id: str,
        path: str,
        load_content: bool = True
    ) -> Optional[VirtualFile]:
        """
        Read a file from the virtual filesystem.
        
        Returns virtual file with content loaded if requested.
        """
        mount = self._mounts.get(session_id)
        if not mount:
            raise ValueError(f"No mount found for session {session_id}")
        
        # Normalize path
        path = path.lstrip("/")
        if path.startswith("workspace/"):
            path = path[len("workspace/"):]
        
        vfile = mount.files.get(path)
        
        if not vfile:
            # Check if it's an untracked file on disk
            disk_path = mount.local_path / path
            if disk_path.exists():
                vfile = VirtualFile(
                    path=path,
                    status=FileStatus.UNTRACKED
                )
                mount.files[path] = vfile
            else:
                return None
        
        if load_content and vfile.content is None:
            await self._load_file_content(mount, vfile)
        
        return vfile
    
    async def _load_file_content(self, mount: SessionMount, vfile: VirtualFile):
        """Lazy-load file content."""
        # Check if we have modified version in session
        modified_path = self._get_modified_path(mount, vfile.path)
        
        if modified_path.exists():
            # Load modified version
            async with aiofiles.open(modified_path, "rb") as f:
                vfile.content = await f.read()
        else:
            # Load from Git HEAD
            file_path = mount.local_path / vfile.path
            if file_path.exists():
                async with aiofiles.open(file_path, "rb") as f:
                    vfile.content = await f.read()
                    vfile.head_content = vfile.content
                    vfile.head_sha = vfile.sha
        
        vfile.size = len(vfile.content) if vfile.content else 0
        vfile.is_binary = self._is_binary_content(vfile.content)
    
    async def write_file(
        self,
        session_id: str,
        path: str,
        content: bytes
    ) -> VirtualFile:
        """
        Write file to virtual filesystem.
        
        Changes are stored separately from the Git working tree.
        """
        mount = self._mounts.get(session_id)
        if not mount:
            raise ValueError(f"No mount found for session {session_id}")
        
        path = path.lstrip("/").replace("workspace/", "", 1)
        
        # Determine status
        if path in mount.files:
            vfile = mount.files[path]
            new_sha = hashlib.sha256(content).hexdigest()[:16]
            
            if new_sha != vfile.head_sha:
                vfile.status = FileStatus.MODIFIED
                vfile.sha = new_sha
            else:
                # Reverted to HEAD
                vfile.status = FileStatus.UNCHANGED
                vfile.sha = vfile.head_sha
        else:
            # New file
            vfile = VirtualFile(
                path=path,
                content=content,
                sha=hashlib.sha256(content).hexdigest()[:16],
                size=len(content),
                status=FileStatus.ADDED
            )
            mount.files[path] = vfile
        
        vfile.content = content
        vfile.modified_at = datetime.utcnow()
        
        # Persist to session storage (not Git working tree)
        await self._persist_file_change(mount, vfile)
        
        return vfile
    
    async def _persist_file_change(self, mount: SessionMount, vfile: VirtualFile):
        """Persist file change to session storage."""
        modified_path = self._get_modified_path(mount, vfile.path)
        modified_path.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiofiles.open(modified_path, "wb") as f:
            await f.write(vfile.content)
        
        # Update state file
        await self._save_mount_state(mount)
    
    async def delete_file(self, session_id: str, path: str) -> bool:
        """Mark file as deleted in virtual filesystem."""
        mount = self._mounts.get(session_id)
        if not mount:
            return False
        
        path = path.lstrip("/").replace("workspace/", "", 1)
        
        if path in mount.files:
            vfile = mount.files[path]
            
            if vfile.status == FileStatus.ADDED:
                # Was added in this session, just remove
                del mount.files[path]
                modified_path = self._get_modified_path(mount, path)
                if modified_path.exists():
                    modified_path.unlink()
            else:
                # Mark as deleted
                vfile.status = FileStatus.DELETED
                vfile.content = None
                vfile.modified_at = datetime.utcnow()
            
            await self._save_mount_state(mount)
            return True
        
        return False
    
    async def list_directory(
        self,
        session_id: str,
        path: str = "."
    ) -> List[VirtualFile]:
        """List files in virtual directory."""
        mount = self._mounts.get(session_id)
        if not mount:
            return []
        
        path = path.lstrip("/").replace("workspace/", "", 1)
        
        files = []
        for vfile in mount.files.values():
            if vfile.status != FileStatus.DELETED:
                if path == "." or vfile.path.startswith(path + "/") or vfile.path == path:
                    files.append(vfile)
        
        return sorted(files, key=lambda f: f.path)
    
    async def get_changes(self, session_id: str) -> Dict[str, List[VirtualFile]]:
        """
        Get all changes in session relative to HEAD.
        
        Returns dict with 'modified', 'added', 'deleted' lists.
        """
        mount = self._mounts.get(session_id)
        if not mount:
            return {"modified": [], "added": [], "deleted": []}
        
        changes = {"modified": [], "added": [], "deleted": []}
        
        for vfile in mount.files.values():
            if vfile.status == FileStatus.MODIFIED:
                changes["modified"].append(vfile)
            elif vfile.status == FileStatus.ADDED:
                changes["added"].append(vfile)
            elif vfile.status == FileStatus.DELETED:
                changes["deleted"].append(vfile)
        
        return changes
    
    async def get_diff(self, session_id: str, path: str) -> Optional[str]:
        """Get unified diff for a modified file."""
        mount = self._mounts.get(session_id)
        if not mount:
            return None
        
        vfile = await self.read_file(session_id, path, load_content=True)
        if not vfile or not vfile.has_changes:
            return None
        
        # Generate unified diff
        import difflib
        
        old_content = vfile.head_content or b""
        new_content = vfile.content or b""
        
        old_lines = old_content.decode("utf-8", errors="replace").splitlines(keepends=True)
        new_lines = new_content.decode("utf-8", errors="replace").splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{vfile.path}",
            tofile=f"b/{vfile.path}",
            lineterm=""
        )
        
        return "".join(diff)
    
    async def apply_to_workspace(
        self,
        session_id: str,
        workspace_path: Path
    ) -> Dict[str, Any]:
        """
        Apply all virtual changes to a real workspace directory.
        
        Used when user wants to persist changes to actual filesystem.
        """
        mount = self._mounts.get(session_id)
        if not mount:
            return {"applied": 0, "errors": ["No mount found"]}
        
        applied = 0
        errors = []
        
        for vfile in mount.files.values():
            if not vfile.has_changes:
                continue
            
            target_path = workspace_path / vfile.path
            
            try:
                if vfile.status == FileStatus.DELETED:
                    if target_path.exists():
                        target_path.unlink()
                elif vfile.content is not None:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    async with aiofiles.open(target_path, "wb") as f:
                        await f.write(vfile.content)
                    applied += 1
            except Exception as e:
                errors.append(f"{vfile.path}: {e}")
        
        return {"applied": applied, "errors": errors}
    
    async def commit_changes(
        self,
        session_id: str,
        message: str,
        author: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Commit changes back to Git repository.
        
        Creates a commit on the mounted branch.
        """
        mount = self._mounts.get(session_id)
        if not mount:
            return {"success": False, "error": "No mount found"}
        
        # Apply changes to working tree
        await self.apply_to_workspace(session_id, mount.local_path)
        
        import subprocess
        
        # Git add all changes
        add_proc = await asyncio.create_subprocess_exec(
            "git", "add", "-A",
            cwd=str(mount.local_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await add_proc.communicate()
        
        # Commit
        commit_proc = await asyncio.create_subprocess_exec(
            "git", "commit", "-m", message,
            *("--author", author) if author else [],
            cwd=str(mount.local_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await commit_proc.communicate()
        
        if commit_proc.returncode == 0:
            # Get new commit SHA
            rev_proc = await asyncio.create_subprocess_exec(
                "git", "rev-parse", "HEAD",
                cwd=str(mount.local_path),
                stdout=asyncio.subprocess.PIPE
            )
            new_sha, _ = await rev_proc.communicate()
            
            # Update mount
            mount.commit_sha = new_sha.decode().strip()
            
            # Reset file statuses
            for vfile in mount.files.values():
                if vfile.has_changes:
                    vfile.status = FileStatus.UNCHANGED
                    vfile.head_sha = vfile.sha
                    vfile.head_content = vfile.content
            
            await self._save_mount_state(mount)
            
            return {
                "success": True,
                "commit_sha": mount.commit_sha,
                "files_changed": len([f for f in mount.files.values() if f.has_changes])
            }
        else:
            return {
                "success": False,
                "error": stderr.decode()
            }
    
    async def unmount(self, session_id: str, persist: bool = True):
        """
        Unmount repository for session.
        
        If persist=True, saves state for later resumption.
        If persist=False, cleans up all session data.
        """
        async with self._lock:
            mount = self._mounts.pop(session_id, None)
            if not mount:
                return
            
            if persist:
                await self._save_mount_state(mount)
                logger.info(f"[GVFS] Unmounted {session_id} (state persisted)")
            else:
                # Clean up ephemeral storage
                import shutil
                session_dir = self._storage_path / "sessions" / session_id
                if session_dir.exists():
                    shutil.rmtree(session_dir)
                logger.info(f"[GVFS] Unmounted {session_id} (cleaned up)")
    
    def _get_modified_path(self, mount: SessionMount, path: str) -> Path:
        """Get path to modified file in session storage."""
        return self._storage_path / "sessions" / mount.session_id / "changes" / path
    
    def _is_binary_content(self, content: Optional[bytes]) -> bool:
        """Detect if content is binary."""
        if not content:
            return False
        # Check for null bytes
        return b"\x00" in content[:1024]
    
    async def _save_mount_state(self, mount: SessionMount):
        """Persist mount state to disk."""
        state_file = self._storage_path / "sessions" / mount.session_id / "vfs_state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        
        state = {
            "session_id": mount.session_id,
            "repo_url": mount.repo_url,
            "branch": mount.branch,
            "commit_sha": mount.commit_sha,
            "virtual_root": mount.virtual_root,
            "files": [
                {
                    "path": f.path,
                    "sha": f.sha,
                    "size": f.size,
                    "status": f.status.value,
                    "head_sha": f.head_sha,
                    "modified_at": f.modified_at.isoformat(),
                }
                for f in mount.files.values()
            ],
            "last_sync": mount.last_sync.isoformat() if mount.last_sync else None
        }
        
        async with aiofiles.open(state_file, "w") as f:
            await f.write(json.dumps(state, indent=2))
    
    async def _restore_mount_state(self, mount: SessionMount, state_file: Path):
        """Restore mount state from disk."""
        async with aiofiles.open(state_file, "r") as f:
            state = json.loads(await f.read())
        
        mount.repo_url = state["repo_url"]
        mount.branch = state["branch"]
        mount.commit_sha = state.get("commit_sha")
        mount.virtual_root = state.get("virtual_root", "/workspace")
        
        for fstate in state.get("files", []):
            vfile = VirtualFile(
                path=fstate["path"],
                sha=fstate["sha"],
                size=fstate["size"],
                status=FileStatus(fstate["status"]),
                head_sha=fstate.get("head_sha"),
                modified_at=datetime.fromisoformat(fstate["modified_at"])
            )
            mount.files[vfile.path] = vfile
        
        mount.last_sync = datetime.fromisoformat(state["last_sync"]) if state.get("last_sync") else None


# ──────────────────────────────────────────────────
# Global instance
# ──────────────────────────────────────────────────

_gvfs: Optional[GitVirtualFileSystem] = None

async def get_gvfs() -> GitVirtualFileSystem:
    """Get or create the global GVFS instance."""
    global _gvfs
    if _gvfs is None:
        from src.infrastructure.runtime.paths import WORKSPACE_ROOT
        storage_path = Path(WORKSPACE_ROOT) / ".gvfs_storage"
        storage_path.mkdir(parents=True, exist_ok=True)
        _gvfs = GitVirtualFileSystem(storage_path)
    return _gvfs