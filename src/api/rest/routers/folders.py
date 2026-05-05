"""Tenant-scoped project folder router."""
import asyncio
from typing import Any, Dict

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import get_current_user_dep, get_db
from src.api.rest.routers.folder_models import FolderCreateRequest, FolderGitCloneRequest, FolderLocalImportRequest
from src.api.rest.routers.folder_utils import FOLDER_COLORS, get_accessible_folder, get_owned_folder, scan_folder_tree, serialize_folder, slugify
from src.api.rest.routers.folder_workspace import clone_repo, link_local_folder, remove_workspace_path
from src.infrastructure.auth.jwt_auth import TokenPayload
from src.infrastructure.db.models.folder_model import FolderModel
from src.infrastructure.runtime.paths import workspace_root

router = APIRouter(prefix="/api/v1/folders", tags=["Folders"])


def new_folder(req: FolderCreateRequest, user: TokenPayload, slug: str) -> FolderModel:
    color = req.color if req.color in FOLDER_COLORS else "cyan"
    return FolderModel(
        tenant_id=user.tenant_id,
        name=req.name.strip()[:64],
        owner_id=user.user_id,
        slug=slug,
        description=req.description[:256],
        color=color,
        shared_with=req.shared_with,
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_folder(req: FolderCreateRequest, db: AsyncSession = Depends(get_db), user: TokenPayload = Depends(get_current_user_dep)) -> Dict[str, Any]:
    slug = slugify(req.name)
    folder = new_folder(req, user, slug)
    db.add(folder)
    (workspace_root() / user.tenant_id / slug).mkdir(parents=True, exist_ok=True)
    await db.commit()
    await db.refresh(folder)
    return {**serialize_folder(folder, user), "status": "created"}


@router.get("/")
async def list_folders(db: AsyncSession = Depends(get_db), user: TokenPayload = Depends(get_current_user_dep)) -> Dict[str, Any]:
    result = await db.execute(select(FolderModel).where(and_(FolderModel.tenant_id == user.tenant_id, FolderModel.is_active == True)))
    return {"folders": [serialize_folder(folder, user) for folder in result.scalars().all()]}


@router.get("/{folder_id}")
async def get_folder(folder_id: str, db: AsyncSession = Depends(get_db), user: TokenPayload = Depends(get_current_user_dep)) -> Dict[str, Any]:
    return serialize_folder(await get_accessible_folder(db, folder_id, user), user)


@router.get("/{folder_id}/tree")
async def get_folder_tree(
    folder_id: str,
    max_depth: int = Query(default=3, le=5),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Dict[str, Any]:
    folder = await get_accessible_folder(db, folder_id, user)
    folder_path = workspace_root() / folder.tenant_id / folder.slug
    return {"folder": folder.name, "slug": folder.slug, "tree": await asyncio.to_thread(scan_folder_tree, str(folder_path), max_depth)}


@router.post("/clone", status_code=status.HTTP_201_CREATED)
async def clone_git_repo(req: FolderGitCloneRequest, db: AsyncSession = Depends(get_db), user: TokenPayload = Depends(get_current_user_dep)) -> Dict[str, Any]:
    slug = slugify(req.name)
    folder = new_folder(FolderCreateRequest(name=req.name, description=req.description or f"Cloned from {req.repo_url}", color=req.color), user, slug)
    tenant_root = workspace_root() / user.tenant_id
    tenant_root.mkdir(parents=True, exist_ok=True)
    await clone_repo(req.repo_url, req.branch, tenant_root / slug)
    db.add(folder)
    await db.commit()
    await db.refresh(folder)
    return {**serialize_folder(folder, user), "status": "cloned"}


@router.post("/import-local", status_code=status.HTTP_201_CREATED)
async def import_local_folder(req: FolderLocalImportRequest, db: AsyncSession = Depends(get_db), user: TokenPayload = Depends(get_current_user_dep)) -> Dict[str, Any]:
    slug = slugify(req.name)
    folder = new_folder(FolderCreateRequest(name=req.name, description=req.description, color=req.color), user, slug)
    tenant_root = workspace_root() / user.tenant_id
    tenant_root.mkdir(parents=True, exist_ok=True)
    target_path = await link_local_folder(req.local_path, tenant_root / slug)
    db.add(folder)
    await db.commit()
    await db.refresh(folder)
    return {**serialize_folder(folder, user), "local_path": str(target_path), "status": "mounted"}


@router.delete("/{folder_id}")
async def delete_folder(folder_id: str, db: AsyncSession = Depends(get_db), user: TokenPayload = Depends(get_current_user_dep)) -> Dict[str, str]:
    folder = await get_owned_folder(db, folder_id, user)
    await remove_workspace_path(workspace_root() / user.tenant_id / folder.slug)
    folder.is_active = False
    await db.commit()
    return {"status": "deleted", "folder_id": folder_id}
