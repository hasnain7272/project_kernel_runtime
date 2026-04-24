"""Diff operations."""
import difflib
from typing import Optional
from ..models.virtual_file import VirtualFile


def is_binary_content(content: Optional[bytes]) -> bool:
    """Detect if content is binary."""
    if not content:
        return False
    return b"\x00" in content[:1024]


def generate_diff(vfile: VirtualFile) -> Optional[str]:
    """Generate unified diff for a modified file."""
    if not vfile or not vfile.has_changes:
        return None
    
    old_content = vfile.head_content or b""
    new_content = vfile.content or b""
    
    old_lines = old_content.decode("utf-8", errors="replace").splitlines(keepends=True)
    new_lines = new_content.decode("utf-8", errors="replace").splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{vfile.path}",
        tofile=f"b/{vfile.path}",
        lineterm=""
    )
    
    return "".join(diff)