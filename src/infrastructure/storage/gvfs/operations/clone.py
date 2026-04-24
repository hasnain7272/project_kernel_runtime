"""Repository cloning operations."""
import asyncio
import logging
import os
from pathlib import Path
from ..models.session_mount import SessionMount
from ..models.virtual_file import VirtualFile
from ..models.file_status import FileStatus
from src.infrastructure.security.crypto import decrypt_string

logger = logging.getLogger(__name__)


async def clone_repository(mount: SessionMount) -> None:
    """Clone repository to ephemeral storage."""
    import subprocess
    
    cmd = ["git", "clone", "--depth", "1", "--branch", mount.branch]
    
    if mount.commit_sha:
        cmd = ["git", "clone", mount.repo_url, str(mount.local_path)]
    else:
        cmd.extend([mount.repo_url, str(mount.local_path)])
    
    env = os.environ.copy()
    if mount.auth_token:
        token = decrypt_string(mount.auth_token)
        if "github.com" in mount.repo_url:
            env["GITHUB_TOKEN"] = token
            mount.repo_url = mount.repo_url.replace(
                "https://github.com/",
                f"https://{token}@github.com/"
            )
    
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env
    )
    
    stdout, stderr = await proc.communicate()
    
    if proc.returncode != 0:
        raise RuntimeError(f"Git clone failed: {stderr.decode()}")
    
    if mount.commit_sha:
        checkout_proc = await asyncio.create_subprocess_exec(
            "git", "checkout", mount.commit_sha,
            cwd=str(mount.local_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await checkout_proc.communicate()
    
    await index_repository(mount)


async def index_repository(mount: SessionMount) -> None:
    """Build virtual file index from repository."""
    import subprocess
    
    proc = await asyncio.create_subprocess_exec(
        "git", "ls-tree", "-r", "HEAD",
        cwd=str(mount.local_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, _ = await proc.communicate()
    
    for line in stdout.decode().strip().split("\n"):
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) == 2:
            meta, path = parts
            sha = meta.split()[2]
            mount.files[path] = VirtualFile(
                path=path,
                sha=sha,
                status=FileStatus.UNCHANGED,
                head_sha=sha
            )
    
    logger.info(f"[GVFS] Indexed {len(mount.files)} files")