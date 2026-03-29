"""Repeatable runtime smoke checks for the package workspace."""

import os
import sys
import time

from fastapi.testclient import TestClient

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC_ROOT = os.path.join(REPO_ROOT, "src")
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from project_kernel_runtime.services.fastapi_server import app


def run() -> int:
    with TestClient(app) as client:
        workspace_path = REPO_ROOT

        checks = [
            ("GET", "/health", None),
            ("GET", "/ui/index.html", None),
            ("GET", "/api/surfaces", None),
            ("GET", "/api/models/status", None),
            ("GET", "/api/governance/config", None),
            (
                "POST",
                "/sessions",
                {
                    "user_id": "smoke_user",
                    "workspace_path": workspace_path,
                    "mode": "web",
                },
            ),
            ("GET", "/sessions/smoke_user", None),
            ("GET", "/status/intelligence?user_id=smoke_user", None),
            (
                "POST",
                "/memory/inject",
                {
                    "content": "smoke memory",
                    "context": "verification",
                    "category": "smoke",
                },
            ),
            ("POST", "/memory/search", {"query": "smoke memory", "limit": 5}),
            ("GET", "/billing/credits", None),
            ("GET", "/api/a2a/status", None),
            ("GET", "/api/jobs", None),
            ("GET", "/api/artifacts", None),
        ]

        for method, path, payload in checks:
            if method == "GET":
                response = client.get(path)
            else:
                response = client.post(path, json=payload)
            if response.status_code >= 400:
                print(f"[fail] {method} {path} -> {response.status_code}")
                print(response.text[:500])
                return 1
            print(f"[ok] {method} {path} -> {response.status_code}")

        job_response = client.post(
            "/api/jobs",
            json={
                "kind": "index_workspace",
                "payload": {
                    "workspace_path": os.path.dirname(__file__),
                    "max_files": 8,
                },
            },
        )
        if job_response.status_code >= 400:
            print(f"[fail] POST /api/jobs -> {job_response.status_code}")
            print(job_response.text[:500])
            return 1
        print(f"[ok] POST /api/jobs -> {job_response.status_code}")

        job_id = job_response.json()["job"]["id"]
        final_job = None
        for _ in range(40):
            poll = client.get(f"/api/jobs/{job_id}")
            if poll.status_code >= 400:
                print(f"[fail] GET /api/jobs/{job_id} -> {poll.status_code}")
                print(poll.text[:500])
                return 1
            final_job = poll.json()["job"]
            if final_job["status"] in {"completed", "failed", "cancelled", "interrupted"}:
                break
            time.sleep(0.25)

        if not final_job or final_job["status"] != "completed":
            print(f"[fail] background job did not complete cleanly: {final_job}")
            return 1
        print(f"[ok] GET /api/jobs/{job_id} -> {final_job['status']}")

        artifact_id = final_job.get("artifact_id")
        if artifact_id:
            artifact_response = client.get(f"/api/artifacts/{artifact_id}")
            if artifact_response.status_code >= 400:
                print(f"[fail] GET /api/artifacts/{artifact_id} -> {artifact_response.status_code}")
                print(artifact_response.text[:500])
                return 1
            print(f"[ok] GET /api/artifacts/{artifact_id} -> {artifact_response.status_code}")

    return 0


if __name__ == "__main__":
    raise SystemExit(run())
