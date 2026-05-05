"""Session request models."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class WorkspaceBinding(BaseModel):
    type: str = Field(..., pattern="^(local|git)$")
    path: Optional[str] = None
    url: Optional[str] = None
    branch: str = "main"
    slug: Optional[str] = None


class SessionCreateRequest(BaseModel):
    name: str = "New Session"
    workspaces: List[WorkspaceBinding] = Field(default_factory=list)
    mode: str = "web"


class SessionConfigRequest(BaseModel):
    model: Optional[str] = None
    api_key: Optional[str] = None
    github_token: Optional[str] = None
    base_url: Optional[str] = None
    extra_body: Optional[Dict[str, Any]] = None


class SessionRenameRequest(BaseModel):
    name: str


class WorkspaceAddRequest(BaseModel):
    workspace: WorkspaceBinding
