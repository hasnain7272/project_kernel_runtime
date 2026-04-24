"""Changes API operations."""
from pathlib import Path
from typing import Dict, Any, List
import aiofiles
from ..models.session_mount import SessionMount
from ..models.virtual_file import VirtualFile
from ..models.file_status import FileStatus


class ChangesAPI:
    """Changes operations handler."""
    
    def __init__(self, storage_path: Path):
        self._storage_path = storage_path
    
    def get_changes(self, mount: SessionMount) -> Dict[str, List[VirtualFile]]:
        """Get all changes in session relative to HEAD."""
        return {
            "modified": [f for f in mount.files.values() if f.status == FileStatus.MODIFIED],
            "added": [f for f in mount.files.values() if f.status == FileStatus.ADDED],
            "deleted": [f for f in mount.files.values() if f.status == FileStatus.DELETED]
        }
    
    async def apply_to_workspace(
        self,
        mount: SessionMount,
        workspace_path: Path
    ) -> Dict[str, Any]:
        """Apply all virtual changes to a real workspace directory."""
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