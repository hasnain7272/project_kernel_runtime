"""Virtual file model."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from .file_status import FileStatus


@dataclass
class VirtualFile:
    """Represents a file in the virtual filesystem."""
    path: str
    content: Optional[bytes] = None
    sha: str = ""
    size: int = 0
    status: FileStatus = FileStatus.UNCHANGED
    created_at: datetime = field(default_factory=datetime.utcnow)
    modified_at: datetime = field(default_factory=datetime.utcnow)
    is_binary: bool = False
    head_sha: Optional[str] = None
    head_content: Optional[bytes] = None
    
    @property
    def has_changes(self) -> bool:
        return self.status in (FileStatus.MODIFIED, FileStatus.ADDED, FileStatus.DELETED)