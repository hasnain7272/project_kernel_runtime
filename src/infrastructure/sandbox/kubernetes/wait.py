"""Pod and job waiting utilities."""
import asyncio
import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

from .config import K8S_NAMESPACE

if TYPE_CHECKING:
    from kubernetes_asyncio import client

logger = logging.getLogger(__name__)


async def wait_for_pod(
    core_v1: Any,
    job_name: str,
    timeout: int = 60
) -> Optional[str]:
    """Wait for job pod to be created and running."""
    start = asyncio.get_event_loop().time()

    while asyncio.get_event_loop().time() - start < timeout:
        try:
            pods = await core_v1.list_namespaced_pod(
                namespace=K8S_NAMESPACE,
                label_selector=f"job-name={job_name}"
            )
            for pod in pods.items:
                if pod.status.phase in ["Pending", "Running"]:
                    return pod.metadata.name
        except Exception as e:
            logger.warning(f"[K8sSandbox] Error waiting for pod: {e}")
        await asyncio.sleep(1)
    return None


async def wait_for_completion(
    batch_v1: Any,
    core_v1: Any,
    job_name: str,
    pod_name: str,
    timeout: int
) -> Dict[str, Any]:
    """Wait for job to complete."""
    start = asyncio.get_event_loop().time()

    while asyncio.get_event_loop().time() - start < timeout:
        try:
            job = await batch_v1.read_namespaced_job(
                name=job_name,
                namespace=K8S_NAMESPACE
            )
            if job.status.succeeded is not None and job.status.succeeded > 0:
                return {"exit_code": 0}
            if job.status.failed is not None and job.status.failed > 0:
                pod = await core_v1.read_namespaced_pod(
                    name=pod_name,
                    namespace=K8S_NAMESPACE
                )
                exit_code = pod.status.container_statuses[0].state.terminated.exit_code
                return {"exit_code": exit_code}
        except Exception as e:
            logger.warning(f"[K8sSandbox] Error checking job status: {e}")
        await asyncio.sleep(1)
    raise asyncio.TimeoutError()


async def get_logs(core_v1: Any, pod_name: str) -> tuple:
    """Get stdout/stderr from completed pod."""
    try:
        logs = await core_v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=K8S_NAMESPACE,
            timestamps=False
        )
        return logs, ""
    except Exception as e:
        logger.error(f"[K8sSandbox] Failed to get logs: {e}")
        return "", str(e)


async def cleanup_job(batch_v1: Any, job_name: str):
    """Delete job and associated pods."""
    try:
        await batch_v1.delete_namespaced_job(
            name=job_name,
            namespace=K8S_NAMESPACE,
            body={"propagationPolicy": "Foreground"}
        )
        logger.debug(f"[K8sSandbox] Cleaned up job {job_name}")
    except Exception as e:
        logger.warning(f"[K8sSandbox] Failed to cleanup job {job_name}: {e}")
