from pathlib import Path

from src.domain.exceptions import GovernanceDeniedError
from src.infrastructure.runtime.config import WORKSPACE_ROOT


def workspace_root() -> Path:
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    return WORKSPACE_ROOT


def get_session_root(tenant_id: str, session_id: str) -> Path:
    """Get the root storage directory for a session."""
    return workspace_root() / f"tenant_{tenant_id}" / f"session_{session_id}"


def resolve_workspace_path(
    path: str | None = None, 
    session_id: str = None,
    tenant_id: str = "local",
) -> Path:
    """
    Resolve workspace path with strict session isolation.
    
    The path is always relative to the session root.
    '/workspace' is mapped to the session root.
    """
    if not session_id:
        # Fallback to global root if no session (legacy/global tools)
        root = workspace_root()
    else:
        root = get_session_root(tenant_id, session_id)
    
    root.mkdir(parents=True, exist_ok=True)
    root = root.resolve()
    
    path_str = str(path or ".")
    
    # Handle agent virtual roots
    if path_str == "/" or path_str == "/workspace":
        return root

    if path_str.startswith("/workspace/"):
        candidate = Path(path_str.replace("/workspace/", "", 1))
    else:
        candidate = Path(path_str)
        
    if candidate.is_absolute():
        # Security: Absolute paths must still be within the root
        resolved = candidate.resolve()
    else:
        resolved = (root / candidate).resolve()

    # Security Check: the resolved path must always stay within the root.
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        if resolved == root:
            return root
        raise GovernanceDeniedError(f"Path escapes session root: {resolved}") from exc

    return resolved


def get_session_workspace(tenant_id: str, session_id: str, folder_name: str = None) -> Path:
    """Legacy compatibility: returns the session root."""
    return get_session_root(tenant_id, session_id)
