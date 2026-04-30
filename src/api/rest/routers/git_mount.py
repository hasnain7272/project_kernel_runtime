"""
Git Mount API Router — Composed from sub-routers.

Aggregates mount core, file operations, git operations, and streaming
into a single prefixed router for clean gateway registration.
"""
from fastapi import APIRouter

from .git_mount_core import router as core_router
from .git_mount_files import router as files_router
from .git_mount_ops import router as ops_router
from .git_mount_stream import router as stream_router

# Re-export shared helpers for backward compatibility (used by github_auth.py)
from .git_mount_models import create_signed_state, parse_signed_state  # noqa: F401

router = APIRouter(prefix="/api/v1/git", tags=["Git Mount"])

router.include_router(core_router)
router.include_router(files_router)
router.include_router(ops_router)
router.include_router(stream_router)
