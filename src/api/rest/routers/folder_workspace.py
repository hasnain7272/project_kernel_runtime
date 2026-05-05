"""Folder workspace filesystem operations."""
import asyncio
import logging
import os
import shutil
from pathlib import Path

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


async def clone_repo(repo_url: str, branch: str, target_dir: Path) -> None:
    if target_dir.exists():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Project '{target_dir.name}' already exists.")
    proc = await asyncio.create_subprocess_exec(
        "git", "clone", "--depth", "1", "-b", branch, repo_url, str(target_dir),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        detail = stderr.decode(errors="replace")
        logger.error("[Folders] Git clone failed: %s", detail)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Git clone failed: {detail}")


async def link_local_folder(local_path: str, symlink_path: Path) -> Path:
    target_path = Path(local_path).resolve()
    if not target_path.exists():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Local path does not exist: {local_path}")
    if not target_path.is_dir():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Specified path is not a directory.")
    if symlink_path.exists():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Workspace path already exists: {symlink_path.name}")
    await asyncio.to_thread(_link, target_path, symlink_path)
    return target_path


def _link(target_path: Path, symlink_path: Path) -> None:
    if os.name == "nt":
        import subprocess

        subprocess.run(["cmd", "/c", "mklink", "/j", str(symlink_path), str(target_path)], check=True)
    else:
        os.symlink(target_path, symlink_path)


async def remove_workspace_path(target: Path) -> None:
    if not target.exists():
        return
    try:
        await asyncio.to_thread(_remove, target)
    except Exception as exc:
        logger.warning("Failed to cleanup workspace %s: %s", target, exc)


def _remove(target: Path) -> None:
    if target.is_symlink():
        target.unlink()
    elif os.name == "nt" and target.is_dir():
        import subprocess

        subprocess.run(["cmd", "/c", "rmdir", str(target)], check=False)
    elif target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
