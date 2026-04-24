"""
Folders Router — Production-grade Multi-tenant workspace isolation.

Clean architecture: All queries use tenant_id from JWT.
No backward compatibility - clean new code.
"""
import os
import re
import uuid
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import get_db, get_current_user_dep
from src.infrastructure.auth.jwt_auth import TokenPayload
from src.infrastructure.db.models.folder_model import FolderModel
from src.infrastructure.runtime.paths import workspace_root

router = APIRouter(prefix="/api/v1/folders", tags=["Folders"])

FOLDER_COLORS = ["cyan", "violet", "amber", "emerald", "rose", "sky", "slate"]


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9\-_]", "", name.lower().replace(" ", "-"))
    if not slug:
        slug = f"folder-{uuid.uuid4().hex[:6]}"
    return f"{slug}-{uuid.uuid4().hex[:6]}"


def _scan_folder_tree(root: str, max_depth: int = 3, depth: int = 0) -> List[Dict]:
    if depth >= max_depth or not os.path.isdir(root):
        return []
    entries: List[Dict] = []
    try:
        for name in sorted(os.listdir(root)):
            if name.startswith(".") or name in {"__pycache__", "node_modules", ".venv", ".git"}:
                continue
            full = os.path.join(root, name)
            if os.path.isdir(full):
                entries.append({
                    "name": name,
                    "type": "directory",
                    "children": _scan_folder_tree(full, max_depth, depth + 1),
                })
            else:
                entries.append({
                    "name": name,
                    "type": "file",
                    "size": os.path.getsize(full),
                })
    except PermissionError:
        pass
    return entries


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


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_folder(
    req: FolderCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Dict[str, Any]:
    """Create folder with tenant isolation."""
    if req.color not in FOLDER_COLORS:
        req.color = "cyan"
    
    slug = _slugify(req.name)
    
    folder = FolderModel(
        tenant_id=user.tenant_id,
        name=req.name.strip()[:64],
        owner_id=user.user_id,
        slug=slug,
        description=req.description[:256],
        color=req.color,
        shared_with=req.shared_with,
    )
    db.add(folder)
    
    folder_workspace = workspace_root() / user.tenant_id / slug
    folder_workspace.mkdir(parents=True, exist_ok=True)
    
    await db.commit()
    await db.refresh(folder)
    
    return {
        "id": folder.id,
        "name": folder.name,
        "slug": folder.slug,
        "tenant_id": folder.tenant_id,
        "color": folder.color,
        "permission": "owner",
        "status": "created",
    }


@router.get("/")
async def list_folders(
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Dict[str, Any]:
    """List folders for tenant."""
    result = await db.execute(
        select(FolderModel).where(
            and_(
                FolderModel.tenant_id == user.tenant_id,
                FolderModel.is_active == True,
            )
        )
    )
    rows = result.scalars().all()
    
    folders = []
    for f in rows:
        perm = "owner" if f.owner_id == user.user_id else "viewer"
        if f.shared_with and user.user_id in f.shared_with.split(","):
            perm = "editor"
        folders.append({
            "id": f.id,
            "name": f.name,
            "slug": f.slug,
            "color": f.color,
            "description": f.description,
            "permission": perm,
            "created_at": f.created_at.isoformat(),
        })
    
    return {"folders": folders}


@router.get("/{folder_id}")
async def get_folder(
    folder_id: str,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Dict[str, Any]:
    """Get folder by ID."""
    result = await db.execute(
        select(FolderModel).where(
            and_(
                FolderModel.id == folder_id,
                FolderModel.tenant_id == user.tenant_id,
            )
        )
    )
    folder = result.scalar_one_or_none()
    
    if not folder:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Folder not found")
    
    if folder.owner_id != user.user_id and user.user_id not in folder.shared_with.split(","):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")
    
    perm = "owner" if folder.owner_id == user.user_id else "viewer"
    if folder.shared_with and user.user_id in folder.shared_with.split(","):
        perm = "editor"
    
    return {
        "id": folder.id,
        "name": folder.name,
        "slug": folder.slug,
        "tenant_id": folder.tenant_id,
        "color": folder.color,
        "description": folder.description,
        "permission": perm,
        "created_at": folder.created_at.isoformat(),
    }


@router.get("/{folder_id}/tree")
async def get_folder_tree(
    folder_id: str,
    max_depth: int = Query(default=3, le=5),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Dict[str, Any]:
    """Get folder contents."""
    result = await db.execute(
        select(FolderModel).where(
            and_(
                FolderModel.id == folder_id,
                FolderModel.tenant_id == user.tenant_id,
            )
        )
    )
    folder = result.scalar_one_or_none()
    
    if not folder:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Folder not found")
    
    if folder.owner_id != user.user_id and user.user_id not in folder.shared_with.split(","):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")
    
    folder_workspace = workspace_root() / folder.tenant_id / folder.slug
    
    import asyncio
    
    return {
        "folder": folder.name,
        "slug": folder.slug,
        "tree": await asyncio.to_thread(_scan_folder_tree, str(folder_workspace), max_depth),
    }


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

@router.post("/clone", status_code=status.HTTP_201_CREATED)
async def clone_git_repo(
    req: FolderGitCloneRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Dict[str, Any]:
    """
    Clone a remote Git repository as a workspace.
    Uses the GVFS system for virtualized file access.
    """
    from src.infrastructure.storage.gvfs import get_gvfs
    
    # 1. Prep Folder Entry
    slug = _slugify(req.name)
    folder = FolderModel(
        tenant_id=user.tenant_id,
        name=req.name.strip()[:64],
        owner_id=user.user_id,
        slug=slug,
        description=req.description[:256] or f"Cloned from {req.repo_url}",
        color=req.color,
    )
    db.add(folder)
    
    # 2. Trigger Physical Clone
    # We clone into the tenant's workspace directory
    # Note: For GVFS-style 'mounting', we might prefer a different approach, 
    # but for a 'Folder' project, a real clone is more predictable for tool execution.
    tenant_root = workspace_root() / user.tenant_id
    tenant_root.mkdir(parents=True, exist_ok=True)
    
    target_dir = tenant_root / slug
    if target_dir.exists():
         raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Project '{slug}' already exists.")

    try:
        import asyncio
        cmd = ["git", "clone", "--depth", "1", "-b", req.branch, req.repo_url, str(target_dir)]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            logger.error(f"[Folders] Git clone failed: {stderr.decode()}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Git clone failed: {stderr.decode()}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Folders] Error during clone: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    
    await db.commit()
    await db.refresh(folder)
    
    return {
        "id": folder.id,
        "name": folder.name,
        "slug": folder.slug,
        "status": "cloned",
    }


@router.post("/import-local", status_code=status.HTTP_201_CREATED)
async def import_local_folder(
    req: FolderLocalImportRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Dict[str, Any]:
    """
    Import a local directory from the host machine.
    Creates a 'virtual' project pointing to real hardware paths.
    """
    import os
    from pathlib import Path
    
    # 1. Path Safety & Existence
    target_path = Path(req.local_path).resolve()
    if not target_path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Local path does not exist: {req.local_path}"
        )
    if not target_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Specified path is not a directory."
        )
    
    # 2. Slug & DB Entry
    slug = _slugify(req.name)
    folder = FolderModel(
        tenant_id=user.tenant_id,
        name=req.name.strip()[:64],
        owner_id=user.user_id,
        slug=slug,
        description=req.description[:256],
        color=req.color,
        # Store the actual physical path in context/metdata if needed, 
        # but for now we'll symlink it in the workspace root.
    )
    db.add(folder)
    
    # 3. Workspace Symlinking
    # This allows the agent (running in the workspace root) to see the files
    # without moving them.
    tenant_root = workspace_root() / user.tenant_id
    tenant_root.mkdir(parents=True, exist_ok=True)
    
    symlink_path = tenant_root / slug
    
    try:
        if os.name == 'nt':
            # Windows requires admin or specific privileges for symlinks, 
            # alternative is a directory junction or just storing the path.
            # For maximum compatibility in this runtime, we'll try to create a junction.
            import subprocess
            subprocess.run(['mklink', '/j', str(symlink_path), str(target_path)], shell=True, check=True)
        else:
            os.symlink(target_path, symlink_path)
    except Exception as e:
        logger.error(f"[Folders] Failed to link local path: {e}")
        # Rollback: delete entry if link fails (transactional integrity)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to link local directory: {str(e)}"
        )
    
    await db.commit()
    await db.refresh(folder)
    
    return {
        "id": folder.id,
        "name": folder.name,
        "slug": folder.slug,
        "local_path": str(target_path),
        "status": "mounted",
    }


@router.delete("/{folder_id}")
async def delete_folder(
    folder_id: str,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Dict[str, str]:
    """Delete folder (owner only). Also removes symlink/junction."""
    import os
    import shutil
    
    result = await db.execute(
        select(FolderModel).where(
            and_(
                FolderModel.id == folder_id,
                FolderModel.tenant_id == user.tenant_id,
                FolderModel.owner_id == user.user_id,
            )
        )
    )
    folder = result.scalar_one_or_none()
    
    if not folder:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Folder not found or access denied")
    
    # Cleanup physical workspace (link or folder)
    target = workspace_root() / user.tenant_id / folder.slug
    if target.exists():
        try:
            import asyncio
            def _remove(t):
                if t.is_symlink() or os.name == 'nt':
                    if os.name == 'nt' and t.is_dir():
                        import subprocess
                        subprocess.run(['rmdir', str(t)], shell=True)
                    else:
                        t.unlink()
                else:
                    shutil.rmtree(t)
            await asyncio.to_thread(_remove, target)
        except Exception as e:
            logger.warning(f"Failed to cleanup workspace {target}: {e}")

    folder.is_active = False
    await db.commit()
    
    return {"status": "deleted", "folder_id": folder_id}