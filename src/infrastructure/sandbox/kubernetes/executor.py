"""Enterprise-grade Kubernetes sandbox executor."""
import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING

from .config import MAX_OUTPUT_SIZE
from .exceptions import SandboxExecutionError
from .jobs import get_active_jobs, terminate_job
from .manifest import create_job_manifest
from .models import SandboxConfig, SandboxResult
from .wait import cleanup_job, get_logs, wait_for_completion, wait_for_pod

if TYPE_CHECKING:
    from kubernetes_asyncio import client

logger = logging.getLogger(__name__)


class KubernetesSandboxExecutor:
    """Enterprise-grade sandbox execution using Kubernetes Jobs."""

    def __init__(self):
        self._core_v1 = None
        self._batch_v1 = None
        self._initialized = False

    async def _ensure_client(self):
        """Initialize Kubernetes client."""
        if self._initialized:
            return

        try:
            from kubernetes_asyncio import config, client

            try:
                config.load_incluster_config()
                logger.info("[K8sSandbox] Using in-cluster configuration")
            except Exception:
                from .config import KUBECONFIG_PATH
                if KUBECONFIG_PATH:
                    await config.load_kube_config(config_file=KUBECONFIG_PATH)
                else:
                    await config.load_kube_config()
                logger.info("[K8sSandbox] Loaded kubeconfig")

            self._core_v1 = client.CoreV1Api()
            self._batch_v1 = client.BatchV1Api()
            self._initialized = True
        except ImportError:
            logger.error("[K8sSandbox] kubernetes_asyncio not installed")
            raise

    def _generate_job_name(self, session_id: Optional[str] = None) -> str:
        """Generate unique job name with session context."""
        from hashlib import md5
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        unique = uuid.uuid4().hex[:8]

        if session_id:
            session_hash = md5(session_id.encode()).hexdigest()[:8]
            return f"sandbox-{session_hash}-{timestamp}-{unique}"
        return f"sandbox-{timestamp}-{unique}"

    async def execute(self, config: SandboxConfig) -> SandboxResult:
        """Execute command in sandboxed Kubernetes Job."""
        await self._ensure_client()

        job_name = self._generate_job_name(config.session_id)
        start_time = time.time()

        try:
            job_manifest = create_job_manifest(config, job_name)
            logger.info(f"[K8sSandbox] Creating job {job_name}")

            from .config import K8S_NAMESPACE
            await self._batch_v1.create_namespaced_job(
                namespace=K8S_NAMESPACE,
                body=job_manifest
            )

            pod_name = await wait_for_pod(self._core_v1, job_name, timeout=60)
            if not pod_name:
                raise SandboxExecutionError(f"Failed to create pod for job {job_name}")

            result = await wait_for_completion(
                self._batch_v1, self._core_v1,
                job_name, pod_name, timeout=config.timeout
            )

            stdout, stderr = await get_logs(self._core_v1, pod_name)
            await cleanup_job(self._batch_v1, job_name)

            duration_ms = (time.time() - start_time) * 1000

            return SandboxResult(
                exit_code=result.get("exit_code", -1),
                stdout=stdout[:MAX_OUTPUT_SIZE],
                stderr=stderr[:MAX_OUTPUT_SIZE],
                duration_ms=duration_ms,
                job_name=job_name,
                pod_name=pod_name,
                started_at=datetime.utcnow() - timedelta(milliseconds=duration_ms),
                completed_at=datetime.utcnow(),
                resource_usage=result.get("resources")
            )

        except asyncio.TimeoutError:
            await cleanup_job(self._batch_v1, job_name)
            raise SandboxExecutionError(f"Execution timed out after {config.timeout}s")
        except Exception as e:
            await cleanup_job(self._batch_v1, job_name)
            raise SandboxExecutionError(f"Execution failed: {e}")

    async def get_active_jobs(self, session_id: Optional[str] = None):
        """List active sandbox jobs."""
        await self._ensure_client()
        return await get_active_jobs(self._batch_v1, session_id)

    async def terminate_job(self, job_name: str) -> bool:
        """Forcefully terminate a running job."""
        await self._ensure_client()
        return await terminate_job(self._batch_v1, job_name)
