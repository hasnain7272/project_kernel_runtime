"""Folder serialization, access, and tree helpers."""
import os
import re
import uuid
from typing import Dict, List

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.auth.jwt_auth import TokenPayload
from src.infrastructure.db.models.folder_model import FolderModel

FOLDER_COLORS = ["cyan", "violet", "amber", "emerald", "rose", "sky", "slate"]


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9\-_]", "", name.lower().replace(" ", "-"))
    return f"{slug or 'folder'}-{uuid.uuid4().hex[:6]}"


def permission_for(folder: FolderModel, user_id: str) -> str:
    if folder.owner_id == user_id:
        return "owner"
    if folder.shared_with and user_id in folder.shared_with.split(","):
        return "editor"
    return "viewer"


def serialize_folder(folder: FolderModel, user: TokenPayload) -> Dict:
    return {
        "id": folder.id,
        "name": folder.name,
        "slug": folder.slug,
        "tenant_id": folder.tenant_id,
        "color": folder.color,
        "description": folder.description,
        "permission": permission_for(folder, user.user_id),
        "created_at": folder.created_at.isoformat() if folder.created_at else None,
    }


async def get_accessible_folder(db: AsyncSession, folder_id: str, user: TokenPayload) -> FolderModel:
    result = await db.execute(select(FolderModel).where(and_(FolderModel.id == folder_id, FolderModel.tenant_id == user.tenant_id)))
    folder = result.scalar_one_or_none()
    if not folder:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Folder not found")
    if folder.owner_id != user.user_id and user.user_id not in (folder.shared_with or "").split(","):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")
    return folder


async def get_owned_folder(db: AsyncSession, folder_id: str, user: TokenPayload) -> FolderModel:
    result = await db.execute(
        select(FolderModel).where(and_(FolderModel.id == folder_id, FolderModel.tenant_id == user.tenant_id, FolderModel.owner_id == user.user_id))
    )
    folder = result.scalar_one_or_none()
    if not folder:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Folder not found or access denied")
    return folder


def scan_folder_tree(root: str, max_depth: int = 3, depth: int = 0) -> List[Dict]:
    if depth >= max_depth or not os.path.isdir(root):
        return []
    entries: List[Dict] = []
    for name in sorted(os.listdir(root)):
        if name.startswith(".") or name in {"__pycache__", "node_modules", ".venv", ".git"}:
            continue
        full = os.path.join(root, name)
        if os.path.isdir(full):
            entries.append({"name": name, "type": "directory", "children": scan_folder_tree(full, max_depth, depth + 1)})
        else:
            entries.append({"name": name, "type": "file", "size": os.path.getsize(full)})
    return entries
