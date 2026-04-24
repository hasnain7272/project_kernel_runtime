"""Job management utilities for Kubernetes sandbox."""
import logging
from typing import Dict, List, Optional, TYPE_CHECKING

from .config import K8S_NAMESPACE
from .wait import cleanup_job

if TYPE_CHECKING:
    from kubernetes_asyncio import client

logger = logging.getLogger(__name__)


async def get_active_jobs(
    batch_v1,
    session_id: Optional[str] = None
) -> List[Dict]:
    """List active sandbox jobs."""
    try:
        jobs = await batch_v1.list_namespaced_job(
            namespace=K8S_NAMESPACE,
            label_selector="app=antigravity-sandbox"
        )

        result = []
        for job in jobs.items:
            if session_id and job.metadata.labels.get("session-id") != session_id:
                continue
            result.append({
                "name": job.metadata.name,
                "status": {
                    "active": job.status.active,
                    "succeeded": job.status.succeeded,
                    "failed": job.status.failed,
                },
                "created": job.metadata.creation_timestamp,
                "session_id": job.metadata.labels.get("session-id"),
            })
        return result

    except Exception as e:
        logger.error(f"[K8sSandbox] Failed to list jobs: {e}")
        return []


async def terminate_job(
    batch_v1,
    job_name: str
) -> bool:
    """Forcefully terminate a running job."""
    try:
        await batch_v1.delete_namespaced_job(
            name=job_name,
            namespace=K8S_NAMESPACE,
            body={"propagationPolicy": "Foreground"}
        )
        logger.info(f"[K8sSandbox] Terminated job {job_name}")
        return True
    except Exception as e:
        logger.error(f"[K8sSandbox] Failed to terminate job {job_name}: {e}")
        return False


async def cleanup_job_safely(batch_v1, job_name: str):
    """Safely cleanup a job, ignoring errors."""
    try:
        await cleanup_job(batch_v1, job_name)
    except Exception:
        pass
