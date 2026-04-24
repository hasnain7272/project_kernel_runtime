"""Git Virtual File System (GVFS) - session-scoped virtual filesystem over Git."""
from pathlib import Path
from typing import Optional

from .models.file_status import FileStatus
from .models.virtual_file import VirtualFile
from .models.session_mount import SessionMount
from .core import GitVirtualFileSystem

__all__ = ["GitVirtualFileSystem", "FileStatus", "VirtualFile", "SessionMount"]

_gvfs: Optional[GitVirtualFileSystem] = None

async def get_gvfs() -> GitVirtualFileSystem:
    """Get or create the global GVFS instance."""
    global _gvfs
    if _gvfs is None:
        from src.infrastructure.runtime.paths import workspace_root
        storage_path = workspace_root() / "gvfs_metadata"
        storage_path.mkdir(parents=True, exist_ok=True)
        _gvfs = GitVirtualFileSystem(storage_path)
    return _gvfs