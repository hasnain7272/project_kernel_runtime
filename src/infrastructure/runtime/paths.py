from pathlib import Path

from src.domain.exceptions import GovernanceDeniedError
from src.infrastructure.runtime.config import WORKSPACE_ROOT


def workspace_root() -> Path:
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    return WORKSPACE_ROOT


def resolve_workspace_path(path: str | None = None) -> Path:
    root = workspace_root().resolve()
    if not path or path == ".":
        return root

    candidate = Path(path)
    
    # If it's absolute, resolve it first.
    # If it's relative, join with root and then resolve.
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (root / candidate).resolve()

    # Security Check: Ensure the resolved path is within the workspace root
    # This prevents path traversal attacks (e.g. "../../etc/passwd")
    try:
        # On Windows, we need to ensure case-insensitive comparison or consistent drive letters
        # resolved.relative_to(root) will raise ValueError if not a subpath
        resolved.relative_to(root)
    except ValueError as exc:
        # Special case: If we are precisely matching the root itself (sometimes happens with resolve)
        if resolved == root:
            return root
        raise GovernanceDeniedError(f"Path escapes workspace root: {resolved}") from exc
        
    return resolved
