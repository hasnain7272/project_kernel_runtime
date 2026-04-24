"""Security contexts and configurations for Kubernetes sandbox."""
from typing import Any, Dict


def get_pod_security_context(fs_group: int = 1000) -> Dict[str, Any]:
    """Get pod-level security context with hardening."""
    return {
        "runAsNonRoot": True,
        "runAsUser": 1000,
        "runAsGroup": 1000,
        "fsGroup": fs_group,
        "seccompProfile": {
            "type": "RuntimeDefault"
        },
    }


def get_container_security_context(
    allow_privilege_escalation: bool = False,
    read_only_root_fs: bool = True
) -> Dict[str, Any]:
    """Get container-level security context with hardening."""
    return {
        "allowPrivilegeEscalation": allow_privilege_escalation,
        "readOnlyRootFilesystem": read_only_root_fs,
        "capabilities": {
            "drop": ["ALL"]
        },
        "runAsNonRoot": True,
        "runAsUser": 1000,
    }


def get_default_environment() -> list:
    """Get default environment variables for sandbox containers."""
    return [
        {"name": "PYTHONDONTWRITEBYTECODE", "value": "1"},
        {"name": "PYTHONUNBUFFERED", "value": "1"},
        {"name": "HOME", "value": "/tmp"},  # Non-root home
    ]


def get_network_policy(allow_network: bool = False) -> str:
    """Get DNS policy based on network permissions."""
    return "ClusterFirst" if allow_network else "Default"


def get_node_selector() -> Dict[str, str]:
    """Get node selector for sandbox-enabled nodes."""
    return {"sandbox-enabled": "true"}


def get_tolerations() -> list:
    """Get pod tolerations for sandbox nodes."""
    return [
        {
            "key": "sandbox",
            "operator": "Equal",
            "value": "true",
            "effect": "NoSchedule"
        }
    ]


def get_service_account_token_config() -> bool:
    """Whether to automount service account token (False for security)."""
    return False
