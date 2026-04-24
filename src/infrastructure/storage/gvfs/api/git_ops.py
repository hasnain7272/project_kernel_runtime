"""Git operations API."""
import asyncio
import logging
from pathlib import Path
from typing import Any, Dict
from ..models.session_mount import SessionMount
from ..models.file_status import FileStatus
from ..operations.persistence import save_mount_state
from .changes import ChangesAPI

logger = logging.getLogger(__name__)


class GitOperationsAPI:
    """Git operations handler."""
    
    def __init__(self, storage_path: Path):
        self._storage_path = storage_path
        self._changes_api = ChangesAPI(storage_path)
    
    async def commit_changes(
        self,
        mount: SessionMount,
        message: str,
        author: str = None
    ) -> Dict[str, Any]:
        """Commit changes back to Git repository."""
        await self._changes_api.apply_to_workspace(mount, mount.local_path)
        
        add_proc = await asyncio.create_subprocess_exec(
            "git", "add", "-A",
            cwd=str(mount.local_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await add_proc.communicate()
        
        cmd = ["git", "commit", "-m", message]
        if author:
            cmd.extend(["--author", author])
        
        commit_proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(mount.local_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await commit_proc.communicate()
        
        if commit_proc.returncode == 0:
            rev_proc = await asyncio.create_subprocess_exec(
                "git", "rev-parse", "HEAD",
                cwd=str(mount.local_path),
                stdout=asyncio.subprocess.PIPE
            )
            new_sha, _ = await rev_proc.communicate()
            mount.commit_sha = new_sha.decode().strip()
            
            for vfile in mount.files.values():
                if vfile.has_changes:
                    vfile.status = FileStatus.UNCHANGED
                    vfile.head_sha = vfile.sha
                    vfile.head_content = vfile.content
            
            await save_mount_state(self._storage_path, mount)
            
            return {
                "success": True,
                "commit_sha": mount.commit_sha,
                "files_changed": len([f for f in mount.files.values() if f.has_changes])
            }
        else:
            return {"success": False, "error": stderr.decode()}
    
    async def unmount(self, mount: SessionMount, persist: bool = True):
        """Unmount repository for session."""
        if persist:
            await save_mount_state(self._storage_path, mount)
            logger.info(f"[GVFS] Unmounted {mount.session_id} (state persisted)")
        else:
            import shutil
            session_dir = self._storage_path / "sessions" / mount.session_id
            if session_dir.exists():
                shutil.rmtree(session_dir)
            logger.info(f"[GVFS] Unmounted {mount.session_id} (cleaned up)")