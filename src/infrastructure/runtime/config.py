import os
from pathlib import Path


def _flag(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _default_workspace_root() -> Path:
    env_root = os.environ.get("WORKSPACE_ROOT")
    if env_root:
        return Path(env_root).resolve()

    cwd = Path.cwd()
    workspace_dir = cwd / "workspace"
    return workspace_dir.resolve() if workspace_dir.exists() else cwd.resolve()


APP_VERSION = "3.0.0"
WORKSPACE_ROOT = _default_workspace_root()

# Security: Disable anon local by default for production
ALLOW_ANON_LOCAL = _flag("ALLOW_ANON_LOCAL", False)

# Sandbox: Require sandbox by default (security)
SANDBOX_MODE = os.environ.get("SANDBOX_MODE", "docker").strip().lower()
SANDBOX_IMAGE = os.environ.get("SANDBOX_IMAGE", "python:3.11-slim")

# Kubernetes disabled by default (opt-in)
KUBERNETES_MODE = _flag("KUBERNETES_MODE", False)
KUBERNETES_NAMESPACE = os.environ.get("KUBERNETES_NAMESPACE", "default")
KUBERNETES_IMAGE = os.environ.get("KUBERNETES_IMAGE", "python:3.11-slim")

# Hybrid mode: enable worker in same process (dev), disable for production
HYBRID_MODE = _flag("HYBRID_MODE", True)
