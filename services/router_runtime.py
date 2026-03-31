from pathlib import Path
from typing import Any, Dict, List, Optional
import os, json, asyncio

from fastapi import APIRouter, HTTPException
from fastapi import APIRouter, HTTPException, Body
import yaml

from project_kernel_runtime.services.project_registry import (
    build_project_registry,
    build_skill_catalog,
    ensure_project_registry,
)
from project_kernel_runtime.services.runtime_control import get_control_plane

router = APIRouter()

@router.get("/yaml")
async def get_runtime_yaml():
    path = _runtime_yaml_path()
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return {"yaml": f.read()}
        return {"yaml": ""}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/yaml")
async def save_runtime_yaml(payload: dict = Body(...)):
    path = _runtime_yaml_path()
    try:
        content = payload.get("yaml", "")
        # validate it's parseable
        yaml.safe_load(content)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"status": "success"}
    except yaml.YAMLError as ye:
        raise HTTPException(status_code=400, detail=f"Invalid YAML Syntax: {str(ye)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _get_orchestrator():
    from project_kernel_runtime.services.fastapi_server import orchestrator

    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return orchestrator


def _runtime_yaml_path() -> Path:
    return Path(__file__).resolve().parent.parent / "runtime.yaml"


def _load_runtime_yaml() -> Dict[str, Any]:
    path = _runtime_yaml_path()
    if path.exists():
        with open(path, "r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
    return {}


def _save_runtime_yaml(data: Dict[str, Any]) -> None:
    with open(_runtime_yaml_path(), "w", encoding="utf-8") as handle:
        yaml.dump(data, handle, default_flow_style=False, sort_keys=False)


def _resolve_workspace_path(path: Optional[str]) -> Path:
    root = Path(__file__).resolve().parent.parent
    candidate = Path(path) if path else root
    if not candidate.is_absolute():
        candidate = (root / candidate).resolve()
    else:
        candidate = candidate.resolve()
    return candidate


@router.get("/api/project/registry")
async def get_project_registry():
    orchestrator = _get_orchestrator()
    config = _load_runtime_yaml()
    return build_project_registry(orchestrator=orchestrator, config=config)


@router.get("/api/project/folders")
async def list_project_folders():
    config = _load_runtime_yaml()
    registry = ensure_project_registry(config)
    return {"folders": registry.get("folders", [])}


@router.post("/api/project/folders")
async def add_project_folder(payload: Dict[str, Any]):
    path = (payload.get("path") or "").strip()
    if not path:
        raise HTTPException(status_code=400, detail="path required")
    config = _load_runtime_yaml()
    registry = ensure_project_registry(config)
    folders = registry.setdefault("folders", [])
    if path not in folders:
        folders.append(path)
    registry["folders"] = folders
    _save_runtime_yaml(config)
    return {"folders": folders}


@router.delete("/api/project/folders")
async def remove_project_folder(path: str):
    config = _load_runtime_yaml()
    registry = ensure_project_registry(config)
    registry["folders"] = [folder for folder in registry.get("folders", []) if folder != path]
    _save_runtime_yaml(config)
    return {"folders": registry["folders"]}


def _provider_to_dict(provider: Any) -> Dict[str, Any]:
    if isinstance(provider, dict):
        return dict(provider)
    return {
        "name": getattr(provider, "name", ""),
        "api_key_env": getattr(provider, "api_key_env", ""),
        "base_url": getattr(provider, "base_url", None),
        "default_model": getattr(provider, "default_model", ""),
        "enabled": getattr(provider, "enabled", True),
        "priority": getattr(provider, "priority", 0),
    }


def _update_runtime_models(orchestrator, payload: Dict[str, Any]) -> Dict[str, Any]:
    config = _load_runtime_yaml()
    llm_cfg = config.setdefault("llm", {})

    if payload.get("active_model"):
        llm_cfg["active_model"] = payload["active_model"]
        orchestrator.config.llm.active_model = payload["active_model"]
        orchestrator.llm.active_model = payload["active_model"]

    host = payload.get("ollama_host")
    port = payload.get("ollama_port")
    if host and port:
        orchestrator.llm.set_ollama_base_url(str(host), str(port))
        for provider in llm_cfg.get("providers", []):
            if provider.get("name") == "ollama":
                provider["base_url"] = orchestrator.llm.ollama_base_url

    if payload.get("router"):
        router_map = dict(payload["router"])
        llm_cfg["model_router"] = router_map
        orchestrator.config.llm.model_router = router_map
        orchestrator.llm.model_router = router_map

    if payload.get("providers"):
        desired = {item["name"]: item for item in payload["providers"] if item.get("name")}
        for provider in llm_cfg.get("providers", []):
            if provider.get("name") in desired:
                update = desired[provider["name"]]
                if "enabled" in update:
                    provider["enabled"] = bool(update["enabled"])
                if "default_model" in update and update["default_model"]:
                    provider["default_model"] = update["default_model"]
                if "api_key_env" in update and update["api_key_env"] and "sk-" in update["api_key_env"]:
                    provider["api_key"] = update["api_key_env"] # Store in YAML for locals
            
        if hasattr(orchestrator.config.llm, "providers"):
            for provider in orchestrator.config.llm.providers:
                update = desired.get(getattr(provider, "name", ""))
                if update:
                    if "enabled" in update:
                        provider.enabled = bool(update["enabled"])
                    if "default_model" in update and update["default_model"]:
                        provider.default_model = update["default_model"]
                    if "api_key_env" in update and update["api_key_env"]:
                        env_var_name = getattr(provider, "api_key_env", None)
                        if env_var_name:
                            os.environ[env_var_name] = update["api_key_env"]

    _save_runtime_yaml(config)
    return config


def _update_runtime_governance(orchestrator, payload: Dict[str, Any]) -> Dict[str, Any]:
    config = _load_runtime_yaml()
    governance_cfg = config.setdefault("governance", {})
    sandbox_cfg = config.setdefault("sandbox", {})

    for key in ["enabled", "default_role", "require_approval_for", "network_allowlist"]:
        if key in payload:
            governance_cfg[key] = payload[key]
            setattr(orchestrator.config.governance, key, payload[key])
            setattr(orchestrator.governance.config, key, payload[key])

    if "policy_matrix" in payload:
        governance_cfg["policy_matrix"] = payload["policy_matrix"]

    for key in ["backend", "network_mode", "timeout_seconds"]:
        if key in payload:
            sandbox_cfg[key] = payload[key]
            setattr(orchestrator.config.sandbox, key, payload[key])
            if "sandbox" in orchestrator.__dict__ and getattr(orchestrator.sandbox, "config", None):
                setattr(orchestrator.sandbox.config, key, payload[key])

    _save_runtime_yaml(config)
    return config


@router.get("/api/surfaces")
async def get_surfaces():
    orchestrator = _get_orchestrator()

    return {
        "surfaces": [
            {"id": "web_ui", "label": "Web UI", "url": "/ui/index.html", "status": "ready"},
            {"id": "api", "label": "REST API", "url": "/health", "status": "ready"},
            {"id": "ui_ws", "label": "UI WebSocket", "url": "/ws/ui", "status": "ready"},
            {"id": "agent", "label": "Agent Execute", "url": "/agent/execute", "status": "ready"},
            {"id": "jobs", "label": "Background Jobs", "url": "/api/jobs", "status": "ready"},
            {"id": "mcp", "label": "MCP Streamable HTTP", "url": "/mcp", "status": "ready"},
            {"id": "a2a", "label": "A2A Endpoint", "url": "/a2a", "status": "ready"},
            {"id": "agent_card", "label": "Agent Card", "url": "/.well-known/agent.json", "status": "ready"},
        ],
        "mesh": orchestrator.mesh_p2p.get_mesh_status(),
        "mcp": orchestrator.mcp_bridge.get_status(),
    }


@router.get("/api/models/status")
async def get_models_status():
    orchestrator = _get_orchestrator()
    providers = [_provider_to_dict(provider) for provider in orchestrator.config.llm.providers]
    return {
        "active_model": orchestrator.llm.active_model,
        "ollama_base_url": orchestrator.llm.ollama_base_url,
        "router": dict(orchestrator.llm.model_router),
        "providers": providers,
        "usage": orchestrator.llm.get_usage_stats(),
    }


@router.put("/api/models/status")
async def update_models_status(payload: Dict[str, Any]):
    orchestrator = _get_orchestrator()
    _update_runtime_models(orchestrator, payload)
    return await get_models_status()


@router.get("/api/runtime/config")
async def get_system_config():
    orchestrator = _get_orchestrator()
    config = _load_runtime_yaml()
    return {"features": config.get("features", {})}

@router.patch("/api/runtime/config")
async def patch_system_config(payload: Dict[str, Any]):
    orchestrator = _get_orchestrator()
    config = _load_runtime_yaml()
    if "features" in payload:
        feats = config.setdefault("features", {})
        for k, v in payload["features"].items():
            feats[k] = bool(v)
            if hasattr(orchestrator.config, "features") and hasattr(orchestrator.config.features, k):
                setattr(orchestrator.config.features, k, bool(v))
    _save_runtime_yaml(config)
    return {"status": "success", "features": config.get("features", {})}

@router.get("/api/governance/config")
async def get_governance_config():
    orchestrator = _get_orchestrator()
    return {
        "governance": orchestrator.config.governance.model_dump(),
        "sandbox": orchestrator.config.sandbox.model_dump(),
        "security": orchestrator.sandbox.calculate_security_score(),
    }


@router.put("/api/governance/config")
async def update_governance_config(payload: Dict[str, Any]):
    orchestrator = _get_orchestrator()
    _update_runtime_governance(orchestrator, payload)
    return await get_governance_config()


@router.get("/api/jobs")
async def list_jobs(limit: int = 50):
    _get_orchestrator()
    return {"jobs": get_control_plane().list_jobs(limit=limit)}


@router.post("/api/jobs")
async def create_job(payload: Dict[str, Any]):
    orchestrator = _get_orchestrator()
    kind = payload.get("kind")
    job_payload = payload.get("payload", {})
    if not kind:
        raise HTTPException(status_code=400, detail="kind required")
    job = await get_control_plane().create_job(orchestrator, kind, job_payload)
    return {"job": job}


@router.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    _get_orchestrator()
    job = get_control_plane().get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job": job}


@router.post("/api/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    _get_orchestrator()
    job = await get_control_plane().cancel_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job": job}


@router.get("/api/artifacts")
async def list_artifacts(limit: int = 50):
    _get_orchestrator()
    return {"artifacts": get_control_plane().list_artifacts(limit=limit)}


@router.get("/api/artifacts/{artifact_id}")
async def get_artifact(artifact_id: str):
    _get_orchestrator()
    artifact = get_control_plane().get_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact


# ════════════════════════════════════════════════════════════════════
# Phase 2 APIs — Governance, MCP Management, A2A, Auto-Tune, File Tree
# ════════════════════════════════════════════════════════════════════

@router.get("/api/governance/audit")
async def governance_audit(limit: int = 100):
    """Return governance audit trail for the dashboard timeline."""
    from project_kernel_runtime.services.fastapi_server import orchestrator
    config_data = _load_runtime_yaml()
    gov_cfg = config_data.get("governance", {})
    entries, security = [], {"score": 0, "isolation_type": "subprocess"}
    try:
        if orchestrator:
            entries = orchestrator.governance.get_audit_log(limit=limit)
            security = orchestrator.sandbox.calculate_security_score()
    except Exception:
        pass
    return {
        "entries": entries,
        "policy_matrix": gov_cfg.get("policy_matrix", {}),
        "active_role": gov_cfg.get("default_role", "developer"),
        "security": security,
        "guardrail_counts": {
            "require_approval_for": gov_cfg.get("require_approval_for", []),
            "network_allowlist": gov_cfg.get("network_allowlist", []),
        },
    }


@router.get("/api/governance/approvals")
async def governance_approvals():
    orchestrator = _get_orchestrator()
    pending = getattr(orchestrator.governance, "_pending_approvals", {})
    approvals = []
    for approval_id, item in pending.items():
        approvals.append({"approval_id": approval_id, **item})
    approvals.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return {"approvals": approvals}


@router.post("/api/governance/approvals/{approval_id}")
async def resolve_governance_approval(approval_id: str, payload: Dict[str, Any]):
    orchestrator = _get_orchestrator()
    approved = bool(payload.get("approved", False))
    reviewer_id = payload.get("reviewer_id", "web-ui")
    success = await orchestrator.governance.resolve_approval(approval_id, approved, reviewer_id=reviewer_id)
    if not success:
        raise HTTPException(status_code=404, detail="Approval not found")
    return {"approval_id": approval_id, "approved": approved}


@router.get("/api/events")
async def list_event_stream(limit: int = 100, session_id: Optional[str] = None, task_id: Optional[str] = None):
    orchestrator = _get_orchestrator()
    events = orchestrator.event_bus.get_event_log(last_n=limit)
    payload = []
    for event in events:
        if session_id and event.session_id != session_id:
            continue
        if task_id and event.task_id != task_id:
            continue
        payload.append({
            "id": event.id,
            "type": event.type,
            "source": event.source,
            "timestamp": event.timestamp.isoformat(),
            "session_id": event.session_id,
            "task_id": event.task_id,
            "payload": event.payload,
        })
    return {"events": payload}


@router.post("/api/mcp/registry")
async def register_mcp_server(payload: Dict[str, Any]):
    """Add a new MCP server configuration dynamically to runtime.yaml."""
    config = _load_runtime_yaml()
    name = payload.get("name")
    if not name or not payload.get("command"):
        raise HTTPException(status_code=400, detail="Missing name or command")
    
    servers = config.setdefault("mcpServers", {})
    servers[name] = {
        "command": payload.get("command"),
        "args": payload.get("args", []),
        "disabled": payload.get("disabled", False),
        "auto_start": payload.get("auto_start", True),
        "env": payload.get("env", {})
    }
    _save_runtime_yaml(config)
    return {"status": "success", "server": name}

@router.get("/api/mcp/registry")
async def mcp_full_registry():
    """Full MCP registry with runtime status for management UI."""
    from project_kernel_runtime.services.fastapi_server import orchestrator
    config = _load_runtime_yaml()
    registered = config.get("mcpServers", {})
    bridge_status = {}
    try:
        if orchestrator:
            bridge_status = orchestrator.mcp_bridge.get_status()
    except Exception:
        pass
    servers = []
    for name, cfg in registered.items():
        live = bridge_status.get("servers", {}).get(name, {})
        servers.append({
            "name": name,
            "command": cfg.get("command", ""),
            "args": cfg.get("args", []),
            "disabled": cfg.get("disabled", False),
            "auto_start": cfg.get("auto_start", False),
            "status": live.get("status", "stopped"),
            "transport": cfg.get("transport", "stdio"),
            "tool_count": live.get("tool_count", 0),
        })
    external_tools = []
    try:
        if orchestrator:
            external_tools = orchestrator.mcp_bridge.get_all_external_tools()
    except Exception:
        pass
    return {
        "servers": servers,
        "bridge": bridge_status,
        "external_tool_count": len(external_tools),
    }


@router.post("/api/mcp/servers/{name}/toggle")
async def toggle_mcp_server(name: str, payload: Dict[str, Any]):
    """Enable/disable an MCP server and persist to runtime.yaml."""
    config = _load_runtime_yaml()
    servers = config.get("mcpServers", {})
    if name not in servers:
        raise HTTPException(status_code=404, detail=f"Server '{name}' not in registry")
    servers[name]["disabled"] = payload.get("disabled", servers[name].get("disabled", False))
    _save_runtime_yaml(config)
    return {"name": name, "disabled": servers[name]["disabled"]}


@router.post("/api/mcp/servers/{name}/start")
async def start_mcp_server(name: str):
    orchestrator = _get_orchestrator()
    config = _load_runtime_yaml()
    server_cfg = (config.get("mcpServers", {}) or {}).get(name)
    if not server_cfg:
        raise HTTPException(status_code=404, detail=f"Server '{name}' not in registry")
    if server_cfg.get("disabled"):
        raise HTTPException(status_code=400, detail=f"Server '{name}' is disabled")

    connected = await orchestrator.mcp_bridge.connect(name, server_cfg)
    status = orchestrator.mcp_bridge.get_status()
    return {
        "started": bool(connected),
        "server": name,
        "status": status.get("servers", {}).get(name, {"status": "error" if not connected else "connected"}),
    }


@router.post("/api/mcp/servers/{name}/stop")
async def stop_mcp_server(name: str):
    orchestrator = _get_orchestrator()
    disconnected = await orchestrator.mcp_bridge.disconnect(name)
    if not disconnected:
        raise HTTPException(status_code=404, detail=f"Server '{name}' is not connected")
    return {"stopped": True, "server": name}


@router.get("/api/a2a/topology")
async def a2a_topology():
    """Return graph nodes/edges for A2A mesh visualization."""
    from project_kernel_runtime.services.fastapi_server import orchestrator
    config = _load_runtime_yaml()
    a2a_cfg = config.get("a2a", {})
    mesh, peers = {}, []
    try:
        if orchestrator:
            mesh = orchestrator.mesh_p2p.get_mesh_status()
            peers = orchestrator.mesh_p2p.discover_peers()
    except Exception:
        pass

    self_node = {
        "id": "self",
        "label": a2a_cfg.get("agent_name", "Antigravity Kernel"),
        "type": "self",
    }
    nodes = [self_node]
    edges = []
    for i, peer in enumerate(peers):
        peer_data = peer.to_dict() if hasattr(peer, "to_dict") else {"id": f"peer_{i}", "name": f"Peer {i}"}
        pid = peer_data.get("peer_id", peer_data.get("id", f"peer_{i}"))
        nodes.append({
            "id": pid,
            "label": peer_data.get("name", pid),
            "type": "peer",
            "status": peer_data.get("status", "healthy"),
        })
        edges.append({"from": "self", "to": pid, "label": "A2A"})

    return {
        "nodes": nodes,
        "edges": edges,
        "mesh": mesh,
        "protocol_version": a2a_cfg.get("version", "0.3"),
    }


@router.post("/api/a2a/delegate")
async def delegate_a2a_task(payload: Dict[str, Any]):
    orchestrator = _get_orchestrator()
    description = (payload.get("description") or "").strip()
    if not description:
        raise HTTPException(status_code=400, detail="description required")

    peers = []
    try:
        peers = orchestrator.mesh_p2p.discover_peers()
    except Exception:
        peers = []

    target_peer = payload.get("target_peer")
    if not target_peer and peers:
        first_peer = peers[0]
        target_peer = getattr(first_peer, "peer_id", None) or getattr(first_peer, "id", None)
    if not target_peer:
        target_peer = "mesh-fallback"

    job = await get_control_plane().create_job(
        orchestrator,
        "a2a_delegate",
        {
            "target_peer": target_peer,
            "description": description,
            "session_id": payload.get("session_id"),
            "workspace_path": payload.get("workspace_path"),
            "user_id": payload.get("user_id", "web-ui"),
            "max_iterations": int(payload.get("max_iterations", 6)),
        },
    )
    return {"job": job, "target_peer": target_peer}


@router.post("/api/auto-tune")
async def auto_tune(payload: Dict[str, Any]):
    """AI-driven auto-tune: suggest optimal parameter changes."""
    from project_kernel_runtime.services.fastapi_server import orchestrator
    config = _load_runtime_yaml()
    usage = {}
    try:
        if orchestrator:
            usage = orchestrator.llm.get_usage_stats()
    except Exception:
        pass

    suggestions = []

    # Smart suggestions based on current state
    llm_cfg = config.get("llm", {})
    active = llm_cfg.get("active_model", "")
    sandbox_cfg = config.get("sandbox", {})

    if "q4_K_M" in active or "7b" in active.lower():
        suggestions.append({
            "id": "model_upgrade",
            "category": "llm",
            "title": "Upgrade Code Model",
            "description": "Current 7B model may struggle with complex multi-step tasks. Consider upgrading to 14B+ for production.",
            "action": {"param": "llm.active_model", "value": "ollama/qwen2.5-coder:14b-instruct"},
            "impact": "high",
        })

    if sandbox_cfg.get("backend") == "subprocess":
        suggestions.append({
            "id": "sandbox_docker",
            "category": "sandbox",
            "title": "Enable Docker Sandbox",
            "description": "Subprocess isolation is limited. Docker provides stronger security boundaries.",
            "action": {"param": "sandbox.backend", "value": "docker"},
            "impact": "medium",
        })

    if not config.get("observability", {}).get("tracing_enabled", False):
        suggestions.append({
            "id": "enable_tracing",
            "category": "observability",
            "title": "Enable Distributed Tracing",
            "description": "Tracing is disabled. Enable for end-to-end visibility across agent loops.",
            "action": {"param": "observability.tracing_enabled", "value": True},
            "impact": "medium",
        })

    features = config.get("features", {})
    for feature, enabled in features.items():
        if not enabled and feature in ("sre_swarm", "predictive", "self_attention"):
            suggestions.append({
                "id": f"enable_{feature}",
                "category": "features",
                "title": f"Enable {feature.replace('_', ' ').title()}",
                "description": f"Feature '{feature}' is disabled. Enable for improved autonomy.",
                "action": {"param": f"features.{feature}", "value": True},
                "impact": "low",
            })

    return {
        "suggestions": suggestions,
        "current_usage": usage,
        "config_summary": {
            "model": active,
            "sandbox": sandbox_cfg.get("backend", "subprocess"),
            "features_enabled": sum(1 for v in features.values() if v),
            "features_total": len(features),
        },
    }


@router.post("/api/auto-tune/apply")
async def apply_auto_tune(payload: Dict[str, Any]):
    """Apply an auto-tune suggestion by updating runtime.yaml."""
    param = payload.get("param", "")
    value = payload.get("value")
    if not param:
        raise HTTPException(status_code=400, detail="param required")

    config = _load_runtime_yaml()
    parts = param.split(".")
    target = config
    for part in parts[:-1]:
        if part not in target:
            target[part] = {}
        target = target[part]
    target[parts[-1]] = value
    _save_runtime_yaml(config)

    return {"applied": True, "param": param, "value": value}


@router.get("/api/workspace/tree")
async def workspace_file_tree(path: Optional[str] = None, depth: int = 3):
    """Return a file/folder tree for IDE-style explorer in the UI."""

    root = _resolve_workspace_path(path)
    if not root.exists():
        return {
            "tree": {
                "name": root.name or str(root),
                "path": str(root),
                "type": "directory",
                "missing": True,
                "children": [],
            },
            "root": str(root),
            "exists": False,
        }

    IGNORE = {".git", "__pycache__", "node_modules", ".venv", "venv", ".eggs", "data", ".tox"}

    def walk(p: Path, current_depth: int) -> Dict[str, Any]:
        node: Dict[str, Any] = {"name": p.name, "path": str(p)}
        if p.is_dir():
            node["type"] = "directory"
            children = []
            if current_depth < depth:
                try:
                    for child in sorted(p.iterdir(), key=lambda c: (not c.is_dir(), c.name.lower())):
                        if child.name in IGNORE or child.name.startswith("."):
                            continue
                        children.append(walk(child, current_depth + 1))
                except PermissionError:
                    pass
            node["children"] = children
        else:
            node["type"] = "file"
            node["size"] = p.stat().st_size if p.exists() else 0
            node["ext"] = p.suffix
        return node

    tree = walk(root, 0)
    return {"tree": tree, "root": str(root), "exists": True}


@router.get("/api/workspace/file")
async def read_workspace_file(path: str = ""):
    """Read a file's content for the IDE viewer."""
    fp = _resolve_workspace_path(path)
    if not fp.exists() or not fp.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    BINARY_EXT = {".pyc", ".db", ".ico", ".png", ".jpg", ".woff", ".ttf", ".wasm", ".so", ".dll"}
    if fp.suffix.lower() in BINARY_EXT:
        return {"path": str(fp), "binary": True, "size": fp.stat().st_size}

    try:
        content = fp.read_text(encoding="utf-8", errors="replace")[:100_000]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"path": str(fp), "content": content, "lines": content.count("\n") + 1, "size": fp.stat().st_size}


# ════════════════════════════════════════════════════════════════════
# Phase 3 APIs — Skills Registry, Provider Live Check, Heartbeat
# ════════════════════════════════════════════════════════════════════

@router.get("/api/skills/registry")
async def get_skills_registry():
    """Return the full skills registry from runtime.yaml."""
    config = _load_runtime_yaml()
    catalog = build_skill_catalog(config)
    return {
        "available_packs": [item["name"] for item in catalog if item["enabled"]],
        "core": [item for item in catalog if item["pack"] == "core"],
        "domain": [item for item in catalog if item["pack"] != "core"],
        "auto_discover": config.get("skills", {}).get("auto_discover", False),
    }


@router.post("/api/skills/{name}/toggle")
async def toggle_skill(name: str, payload: Dict[str, Any]):
    """Enable or disable a skill globally in runtime.yaml."""
    enabled = payload.get("enabled", True)
    config = _load_runtime_yaml()
    skills = config.setdefault("skills", {})
    target_section = payload.get("pack", "core")

    for section in ("core", "domain"):
        items = skills.get(section, [])
        if not enabled and name in items:
            items.remove(name)
            skills[section] = items

    if enabled:
        items = skills.get(target_section, [])
        if name not in items:
            items.append(name)
            skills[target_section] = items

    _save_runtime_yaml(config)
    return {"name": name, "enabled": enabled}


@router.get("/api/providers/live")
async def get_providers_live():
    """Return live provider status from runtime.yaml with reachability check."""
    config = _load_runtime_yaml()
    llm_cfg = config.get("llm", {})
    providers = llm_cfg.get("providers", [])

    results = []
    for p in providers:
        name = p.get("name", "unknown")
        base_url = p.get("base_url", "")
        reachable = False
        latency_ms = -1

        # Quick reachability check for ollama
        if name == "ollama" and base_url:
            import time
            import urllib.request
            try:
                t0 = time.time()
                req = urllib.request.Request(base_url, method="HEAD")
                urllib.request.urlopen(req, timeout=2)
                latency_ms = int((time.time() - t0) * 1000)
                reachable = True
            except Exception:
                reachable = False
        elif p.get("api_key_env"):
            # Cloud providers — check if env var is set
            reachable = bool(os.environ.get(p["api_key_env"]))

        results.append({
            "name": name,
            "enabled": p.get("enabled", False),
            "reachable": reachable,
            "latency_ms": latency_ms,
            "default_model": p.get("default_model", ""),
            "base_url": base_url or None,
            "api_key_env": p.get("api_key_env", ""),
        })

    return {
        "active_model": llm_cfg.get("active_model", ""),
        "providers": results,
        "router": llm_cfg.get("model_router", {}),
    }


# ── Heartbeat Scheduler (SQLite-backed) ───────────────────────────

import sqlite3
import uuid
from datetime import datetime as _dt

_HEARTBEAT_DB = str(Path(__file__).resolve().parent.parent / "data" / "heartbeat.db")


def _hb_conn() -> sqlite3.Connection:
    """Get or create the heartbeat SQLite DB."""
    os.makedirs(os.path.dirname(_HEARTBEAT_DB), exist_ok=True)
    conn = sqlite3.connect(_HEARTBEAT_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS heartbeat_tasks (
            id TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            cron TEXT NOT NULL,
            task TEXT NOT NULL,
            user_id TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            last_run TEXT,
            next_run TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


@router.get("/api/heartbeat")
async def get_heartbeat_schedule():
    """Return all scheduled heartbeat tasks."""
    conn = _hb_conn()
    rows = conn.execute("SELECT * FROM heartbeat_tasks ORDER BY created_at DESC").fetchall()
    conn.close()
    return {"tasks": [dict(r) for r in rows]}


@router.post("/api/heartbeat")
async def create_heartbeat_task(payload: Dict[str, Any]):
    """Schedule a new proactive heartbeat task (persisted to SQLite)."""
    label = payload.get("label", "Heartbeat Task")
    cron = payload.get("cron", "0 9 * * *")
    task_text = payload.get("task", "")
    user_id = payload.get("user_id", "system")

    if not task_text:
        raise HTTPException(status_code=400, detail="task is required")

    task_id = str(uuid.uuid4())[:12]
    now = _dt.utcnow().isoformat()

    conn = _hb_conn()
    conn.execute(
        "INSERT INTO heartbeat_tasks (id, label, cron, task, user_id, enabled, created_at) VALUES (?, ?, ?, ?, ?, 1, ?)",
        (task_id, label, cron, task_text, user_id, now),
    )
    conn.commit()
    conn.close()

    return {"id": task_id, "label": label, "cron": cron, "task": task_text, "created_at": now}


@router.post("/api/heartbeat/{task_id}/toggle")
async def toggle_heartbeat(task_id: str, payload: Dict[str, Any]):
    """Enable or disable a heartbeat task."""
    enabled = 1 if payload.get("enabled", True) else 0
    conn = _hb_conn()
    conn.execute("UPDATE heartbeat_tasks SET enabled = ? WHERE id = ?", (enabled, task_id))
    conn.commit()
    conn.close()
    return {"id": task_id, "enabled": bool(enabled)}


@router.delete("/api/heartbeat/{task_id}")
async def delete_heartbeat(task_id: str):
    """Delete a heartbeat task."""
    conn = _hb_conn()
    conn.execute("DELETE FROM heartbeat_tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return {"deleted": task_id}

@router.get("/api/models/available")
async def get_available_models():
    """Fetch locally running Ollama models, and inject standard Cloud models."""
    import aiohttp
    models = [
        {"id": "anthropic/claude-3-5-sonnet-20241022", "name": "Anthropic (Claude 3.5 Sonnet)", "group": "Cloud"},
        {"id": "anthropic/claude-3-haiku-20240307", "name": "Anthropic (Claude 3 Haiku)", "group": "Cloud"},
        {"id": "openai/gpt-4o", "name": "OpenAI (GPT-4o)", "group": "Cloud"},
        {"id": "openai/gpt-4o-mini", "name": "OpenAI (GPT-4o Mini)", "group": "Cloud"},
        {"id": "google/gemini-2.5-pro", "name": "Google (Gemini 2.5 Pro)", "group": "Cloud"},
        {"id": "google/gemini-2.5-flash", "name": "Google (Gemini 2.5 Flash)", "group": "Cloud"}
    ]
    try:
        from project_kernel_runtime.services.fastapi_server import orchestrator
        base = getattr(getattr(orchestrator, "llm", None), "ollama_base_url", "http://127.0.0.1:11434")
        if base:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{base}/api/tags", timeout=2) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for m in data.get("models", []):
                            models.insert(0, {"id": f"ollama/{m['name']}", "name": m['name'], "group": "Local (Ollama)"})
    except Exception:
        pass
    return models
