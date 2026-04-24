import shutil
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Depends
from typing import Dict, List, Any

from src.infrastructure.runtime.paths import get_session_workspace
from src.api.rest.dependencies import get_current_user_dep, TokenPayload

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.rest.dependencies import get_db
from src.infrastructure.db.models.session_model import SessionModel
from src.infrastructure.db.models.workspace_model import WorkspaceModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/workspace", tags=["Workspace"])


@router.post("/sessions/{session_id}/upload")
async def upload_files_to_workspace(
    session_id: str,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
):
    """Upload multiple files/folders to a session's isolated workspace."""
    session_result = await db.execute(
        select(SessionModel).where(
            and_(
                SessionModel.id == session_id,
                SessionModel.tenant_id == user.tenant_id,
            )
        )
    )
    session_rec = session_result.scalar_one_or_none()
    if not session_rec:
        raise HTTPException(status_code=404, detail="Session not found")

    workspace = get_session_workspace(user.tenant_id, session_id)
    workspace.mkdir(parents=True, exist_ok=True)
    results = []
    for file in files:
        raw_filename = file.filename or "unnamed"
        safe_rel_path = (
            Path(raw_filename.replace("\\", "/")).relative_to("/")
            if raw_filename.startswith("/")
            else Path(raw_filename.replace("\\", "/"))
        )
        safe_rel_path = Path(*[p for p in safe_rel_path.parts if p != ".."])
        dest_path = workspace / safe_rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with dest_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            results.append({
                "filename": str(safe_rel_path),
                "size": dest_path.stat().st_size,
            })
        finally:
            await file.close()

    sandbox_slug = f"session-{session_id[:12]}"
    try:
        ws_result = await db.execute(
            select(WorkspaceModel).where(
                and_(
                    WorkspaceModel.tenant_id == user.tenant_id,
                    WorkspaceModel.slug == sandbox_slug,
                )
            )
        )
        ws_rec = ws_result.scalar_one_or_none()
        if not ws_rec:
            ws_rec = WorkspaceModel(
                tenant_id=user.tenant_id,
                slug=sandbox_slug,
                name="Sandbox Workspace",
                type="local",
                path=str(workspace),
            )
            db.add(ws_rec)
            await db.flush()
        else:
            ws_rec.path = str(workspace)

        if ws_rec not in session_rec.workspaces:
            session_rec.workspaces.append(ws_rec)
        await db.commit()
    except Exception as e:
        logger.error(f"[Upload] DB Link Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Files uploaded but workspace registration failed",
        ) from e

    return {
        "success": True,
        "count": len(results),
        "files": results,
    }


@router.get("/files")
async def list_workspace_files(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
):
    """List files in the session's isolated workspace."""
    session_result = await db.execute(
        select(SessionModel.id).where(
            and_(
                SessionModel.id == session_id,
                SessionModel.tenant_id == user.tenant_id,
            )
        )
    )
    if not session_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Session not found")

    workspace = get_session_workspace(user.tenant_id, session_id)
    if not workspace.exists():
        return {"files": []}

    def _scan(path: Path) -> List[Dict[str, Any]]:
        items = []
        for p in path.iterdir():
            if p.name.startswith("."):
                continue
            item = {
                "name": p.name,
                "path": str(p.relative_to(workspace)),
                "isDir": p.is_dir(),
                "size": p.stat().st_size if p.is_file() else 0,
            }
            if p.is_dir():
                item["children"] = _scan(p)
            items.append(item)
        return items

    return {"files": _scan(workspace)}
