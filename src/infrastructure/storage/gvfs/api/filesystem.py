"""Filesystem API operations."""
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import aiofiles
from ..models.session_mount import SessionMount
from ..models.virtual_file import VirtualFile
from ..models.file_status import FileStatus
from ..operations.persistence import persist_file_change, get_modified_path

logger = logging.getLogger(__name__)


class FilesystemAPI:
    """Filesystem operations handler."""
    
    def __init__(self, storage_path: Path):
        self._storage_path = storage_path
    
    async def read_file(
        self,
        mount: SessionMount,
        path: str,
        load_content: bool = True
    ) -> Optional[VirtualFile]:
        """Read a file from the virtual filesystem."""
        path = path.lstrip("/").replace("workspace/", "", 1)
        
        vfile = mount.files.get(path)
        if not vfile:
            disk_path = mount.local_path / path
            if disk_path.exists():
                vfile = VirtualFile(path=path, status=FileStatus.UNTRACKED)
                mount.files[path] = vfile
            else:
                return None
        
        if load_content and vfile.content is None:
            await self._load_content(mount, vfile)
        
        return vfile
    
    async def _load_content(self, mount: SessionMount, vfile: VirtualFile):
        """Lazy-load file content."""
        modified_path = get_modified_path(self._storage_path, mount, vfile.path)
        
        if modified_path.exists():
            async with aiofiles.open(modified_path, "rb") as f:
                vfile.content = await f.read()
        else:
            file_path = mount.local_path / vfile.path
            if file_path.exists():
                async with aiofiles.open(file_path, "rb") as f:
                    vfile.content = await f.read()
                    vfile.head_content = vfile.content
                    vfile.head_sha = vfile.sha
        
        vfile.size = len(vfile.content) if vfile.content else 0
    
    async def write_file(
        self,
        mount: SessionMount,
        path: str,
        content: bytes
    ) -> VirtualFile:
        """Write file to virtual filesystem."""
        path = path.lstrip("/").replace("workspace/", "", 1)
        
        if path in mount.files:
            vfile = mount.files[path]
            new_sha = hashlib.sha256(content).hexdigest()[:16]
            vfile.status = FileStatus.MODIFIED if new_sha != vfile.head_sha else FileStatus.UNCHANGED
            vfile.sha = new_sha if vfile.status == FileStatus.MODIFIED else vfile.head_sha
        else:
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
        await persist_file_change(self._storage_path, mount, vfile)
        return vfile
    
    async def delete_file(self, mount: SessionMount, path: str) -> bool:
        """Mark file as deleted in virtual filesystem."""
        path = path.lstrip("/").replace("workspace/", "", 1)
        
        if path in mount.files:
            vfile = mount.files[path]
            if vfile.status == FileStatus.ADDED:
                del mount.files[path]
            else:
                vfile.status = FileStatus.DELETED
                vfile.content = None
                vfile.modified_at = datetime.utcnow()
            return True
        return False
    
    async def list_directory(self, mount: SessionMount, path: str = ".") -> List[VirtualFile]:
        """List files in virtual directory."""
        path = path.lstrip("/").replace("workspace/", "", 1)
        
        files = [f for f in mount.files.values() if f.status != FileStatus.DELETED]
        if path != ".":
            files = [f for f in files if f.path.startswith(path + "/") or f.path == path]
        
        return sorted(files, key=lambda f: f.path)