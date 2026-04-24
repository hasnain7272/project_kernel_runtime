"""Environment configuration constants for Kubernetes sandbox."""
import os

# K8s configuration
KUBECONFIG_PATH = os.environ.get("KUBECONFIG", "")
K8S_NAMESPACE = os.environ.get("K8S_NAMESPACE", "antigravity-sandbox")
K8S_WORKSPACE_PVC = os.environ.get("K8S_WORKSPACE_PVC", "workspace-pvc")
K8S_IMAGE = os.environ.get("K8S_SANDBOX_IMAGE", "python:3.11-slim")
K8S_SERVICE_ACCOUNT = os.environ.get("K8S_SERVICE_ACCOUNT", "sandbox-runner")

# Resource limits
DEFAULT_CPU_LIMIT = os.environ.get("K8S_CPU_LIMIT", "1000m")
DEFAULT_MEMORY_LIMIT = os.environ.get("K8S_MEMORY_LIMIT", "512Mi")
DEFAULT_CPU_REQUEST = os.environ.get("K8S_CPU_REQUEST", "100m")
DEFAULT_MEMORY_REQUEST = os.environ.get("K8S_MEMORY_REQUEST", "128Mi")

# Security
DEFAULT_TIMEOUT = int(os.environ.get("K8S_JOB_TIMEOUT_SECONDS", "300"))
MAX_OUTPUT_SIZE = int(os.environ.get("K8S_MAX_OUTPUT_BYTES", "50000"))
