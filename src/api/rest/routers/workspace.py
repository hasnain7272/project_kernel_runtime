"""
Workspace router.
"""
import os
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query

from src.domain.exceptions import GovernanceDeniedError
from src.infrastructure.runtime.paths import resolve_workspace_path

router = APIRouter(prefix="/api/v1/workspace", tags=["Workspace"])


def _scan_tree(root: str, max_depth: int = 3, depth: int = 0) -> List[Dict]:
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
                    "path": full,
                    "children": _scan_tree(full, max_depth, depth + 1),
                })
            else:
                entries.append({
                    "name": name,
                    "type": "file",
                    "path": full,
                    "size": os.path.getsize(full),
                })
    except PermissionError:
        pass
    return entries


@router.get("/tree")
async def get_workspace_tree(
    path: str = Query(default="."),
    max_depth: int = Query(default=3, le=5),
) -> Dict[str, Any]:
    try:
        abs_path = str(resolve_workspace_path(path))
    except GovernanceDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {"workspace": abs_path, "tree": _scan_tree(abs_path, max_depth)}


@router.get("/file")
async def read_file(
    path: str = Query(...),
    max_bytes: int = Query(default=50000, le=200000),
) -> Dict[str, Any]:
    try:
        abs_path = str(resolve_workspace_path(path))
    except GovernanceDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if not os.path.isfile(abs_path):
        return {"error": "File not found", "path": abs_path}
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read(max_bytes)
        return {
            "path": abs_path,
            "content": content,
            "lines": content.count("\n") + 1,
            "truncated": os.path.getsize(abs_path) > max_bytes,
        }
    except UnicodeDecodeError:
        return {"error": "Binary file", "path": abs_path}
