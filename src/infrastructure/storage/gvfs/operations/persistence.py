"""State persistence operations."""
import json
import logging
from datetime import datetime
from pathlib import Path
import aiofiles
from ..models.session_mount import SessionMount
from ..models.virtual_file import VirtualFile
from ..models.file_status import FileStatus

logger = logging.getLogger(__name__)


def get_modified_path(storage_path: Path, mount: SessionMount, path: str) -> Path:
    """Get path to modified file in session storage."""
    return storage_path / "sessions" / mount.session_id / "changes" / path


async def persist_file_change(storage_path: Path, mount: SessionMount, vfile: VirtualFile):
    """Persist file change to session storage."""
    modified_path = get_modified_path(storage_path, mount, vfile.path)
    modified_path.parent.mkdir(parents=True, exist_ok=True)
    
    async with aiofiles.open(modified_path, "wb") as f:
        await f.write(vfile.content)
    
    await save_mount_state(storage_path, mount)


async def save_mount_state(storage_path: Path, mount: SessionMount):
    """Persist mount state to disk."""
    state_file = storage_path / "sessions" / mount.session_id / "vfs_state.json"
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


async def restore_mount_state(mount: SessionMount, state_file: Path):
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