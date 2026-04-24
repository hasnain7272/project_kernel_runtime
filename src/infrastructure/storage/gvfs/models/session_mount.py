"""Session mount model."""
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from .virtual_file import VirtualFile


@dataclass
class SessionMount:
    """Git repository mount for a session."""
    session_id: str
    repo_url: str
    branch: str = "main"
    commit_sha: Optional[str] = None
    local_path: Optional[Path] = None
    virtual_root: str = "/workspace"
    auth_token: Optional[str] = None
    files: Dict[str, VirtualFile] = field(default_factory=dict)
    loaded: bool = False
    last_sync: Optional[datetime] = None