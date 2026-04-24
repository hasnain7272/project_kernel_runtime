"""Kubernetes Job manifest creation."""
import base64
import hashlib
from typing import Any, Dict

from .config import K8S_NAMESPACE, K8S_SERVICE_ACCOUNT, K8S_WORKSPACE_PVC
from .models import SandboxConfig
from .security import (
    get_container_security_context,
    get_default_environment,
    get_network_policy,
    get_node_selector,
    get_pod_security_context,
    get_service_account_token_config,
    get_tolerations,
)


def create_job_manifest(config: SandboxConfig, job_name: str) -> Dict[str, Any]:
    """Create Kubernetes Job manifest with security hardening."""
    # Prepare environment variables
    env_vars = get_default_environment()
    if config.environment:
        for key, value in config.environment.items():
            env_vars.append({"name": key, "value": str(value)})

    # Base64 encode the script to avoid shell escaping issues
    script_b64 = base64.b64encode(config.command.encode()).decode()

    # The actual command runs the decoded script
    container_command = [
        "/bin/sh",
        "-c",
        f'echo "{script_b64}" | base64 -d | /bin/sh'
    ]

    # Security contexts
    security_context = get_pod_security_context()
    container_security = get_container_security_context()

    # Volumes - workspace is read-only, /tmp is ephemeral
    volumes = [
        {
            "name": "workspace",
            "persistentVolumeClaim": {
                "claimName": K8S_WORKSPACE_PVC,
                "readOnly": True
            }
        },
        {
            "name": "tmp",
            "emptyDir": {
                "sizeLimit": config.memory_limit
            }
        },
    ]

    volume_mounts = [
        {
            "name": "workspace",
            "mountPath": "/workspace",
            "readOnly": True
        },
        {
            "name": "tmp",
            "mountPath": "/tmp"
        },
    ]

    # Network policy
    dns_policy = get_network_policy(config.allow_network)

    # Labels for tracking and cleanup
    labels = {
        "app": "antigravity-sandbox",
        "component": "code-execution",
        "managed-by": "antigravity-runtime",
        "session-id": config.session_id or "none",
        "user-id": config.user_id or "system",
    }

    # TTL for automatic cleanup
    ttl_seconds = min(config.timeout + 300, 3600)  # Max 1 hour

    return {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": job_name,
            "namespace": K8S_NAMESPACE,
            "labels": labels,
            "annotations": {
                "created-by": "antigravity-runtime",
                "session-id": config.session_id or "",
                "command-hash": hashlib.md5(config.command.encode()).hexdigest()[:16],
            }
        },
        "spec": {
            "ttlSecondsAfterFinished": ttl_seconds,
            "backoffLimit": 0,  # No retries - we handle that ourselves
            "activeDeadlineSeconds": config.timeout,
            "template": {
                "metadata": {
                    "labels": labels,
                    "annotations": {
                        "prometheus.io/scrape": "false",  # Don't scrape sandbox pods
                    }
                },
                "spec": {
                    "serviceAccountName": K8S_SERVICE_ACCOUNT,
                    "securityContext": security_context,
                    "restartPolicy": "Never",
                    "dnsPolicy": dns_policy,
                    "automountServiceAccountToken": get_service_account_token_config(),
                    "containers": [
                        {
                            "name": "sandbox",
                            "image": config.image,
                            "imagePullPolicy": "IfNotPresent",
                            "command": container_command,
                            "workingDir": config.working_dir,
                            "env": env_vars,
                            "resources": {
                                "requests": {
                                    "cpu": config.cpu_request,
                                    "memory": config.memory_request
                                },
                                "limits": {
                                    "cpu": config.cpu_limit,
                                    "memory": config.memory_limit
                                }
                            },
                            "securityContext": container_security,
                            "volumeMounts": volume_mounts,
                            "stdin": False,
                            "tty": False,
                        }
                    ],
                    "volumes": volumes,
                    "nodeSelector": get_node_selector(),
                    "tolerations": get_tolerations(),
                }
            }
        }
    }
