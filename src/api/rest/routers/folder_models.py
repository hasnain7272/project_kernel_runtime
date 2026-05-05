"""Folder request models."""
from pydantic import BaseModel


class FolderCreateRequest(BaseModel):
    name: str
    description: str = ""
    color: str = "cyan"
    shared_with: str = ""


class FolderUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    color: str | None = None
    shared_with: str | None = None
    permission: str | None = None


class FolderGitCloneRequest(BaseModel):
    name: str
    repo_url: str
    branch: str = "main"
    description: str = ""
    color: str = "violet"


class FolderLocalImportRequest(BaseModel):
    name: str
    local_path: str
    description: str = ""
    color: str = "sky"
