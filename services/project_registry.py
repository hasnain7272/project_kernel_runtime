from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from project_kernel_runtime.kernel.skills_registry import SkillRegistry


def runtime_yaml_path() -> Path:
    return Path(__file__).resolve().parent.parent / "runtime.yaml"


def load_runtime_yaml() -> Dict[str, Any]:
    path = runtime_yaml_path()
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def save_runtime_yaml(data: Dict[str, Any]) -> None:
    with open(runtime_yaml_path(), "w", encoding="utf-8") as handle:
        yaml.dump(data, handle, default_flow_style=False, sort_keys=False)


def ensure_project_registry(config: Dict[str, Any]) -> Dict[str, Any]:
    registry = config.setdefault("project_registry", {})
    default_folder = config.get("sandbox", {}).get("working_dir", "./workspace")
    folders = registry.setdefault("folders", [default_folder])
    registry["folders"] = list(dict.fromkeys(folder for folder in folders if folder))
    return registry


def session_payload(session) -> Dict[str, Any]:
    return {
        "id": session.session_id,
        "session_id": session.session_id,
        "user_id": session.user_id,
        "workspace_path": session.workspace_path,
        "mode": session.mode,
        "risk_mode": getattr(session, "risk_mode", "auto"),
        "user_role": getattr(session, "user_role", "developer"),
        "skills": getattr(session, "skills", []),
        "mcp_servers": getattr(session, "mcp_servers", []),
        "folders": getattr(session, "folders", []),
        "a2a_enabled": getattr(session, "a2a_enabled", False),
        "a2a_peers": getattr(session, "a2a_peers", []),
        "active": session.is_active,
        "created_at": session.created_at.isoformat(),
        "last_active": session.last_active.isoformat(),
        "recent_files": session.get_recent_files(),
        "recent_tasks": session.get_recent_tasks(),
    }


def build_skill_catalog(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    skills_cfg = config.get("skills", {})
    enabled = set(skills_cfg.get("core", [])) | set(skills_cfg.get("domain", []))
    registry = SkillRegistry()
    items: List[Dict[str, Any]] = []
    seen = set()
    for skill in registry.skills.values():
        seen.add(skill.name)
        items.append({
            "name": skill.name,
            "description": skill.description,
            "tools": skill.tools,
            "level": skill.level.value,
            "pack": skill.pack,
            "enabled": skill.name in enabled,
        })
    for skill_name in sorted(enabled - seen):
        items.append({
            "name": skill_name,
            "description": "Configured in runtime.yaml",
            "tools": [],
            "level": "custom",
            "pack": "core",
            "enabled": True,
        })
    items.sort(key=lambda item: (item["pack"], item["name"]))
    return items


def build_mcp_catalog(config: Dict[str, Any], orchestrator=None) -> List[Dict[str, Any]]:
    registered = config.get("mcpServers", {}) or {}
    live_servers = {}
    if orchestrator:
        try:
            live_servers = orchestrator.mcp_bridge.get_status().get("servers", {})
        except Exception:
            live_servers = {}

    items: List[Dict[str, Any]] = []
    for name, server_cfg in registered.items():
        live = live_servers.get(name, {})
        items.append({
            "name": name,
            "command": server_cfg.get("command", ""),
            "args": server_cfg.get("args", []),
            "transport": server_cfg.get("type", server_cfg.get("transport", "stdio")),
            "disabled": bool(server_cfg.get("disabled", False)),
            "auto_start": bool(server_cfg.get("auto_start", False)),
            "status": live.get("status", "stopped"),
            "tool_count": live.get("tool_count", 0),
        })
    items.sort(key=lambda item: item["name"])
    return items


def build_folder_catalog(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    registry = ensure_project_registry(config)
    return [
        {"path": folder, "label": folder.split("/")[-1] or folder}
        for folder in registry.get("folders", [])
    ]


def build_a2a_catalog(config: Dict[str, Any], orchestrator=None) -> Dict[str, Any]:
    a2a_cfg = config.get("a2a", {})
    mesh = {}
    peers = []
    if orchestrator:
        try:
            mesh = orchestrator.mesh_p2p.get_mesh_status()
        except Exception:
            mesh = {}
        try:
            for peer in orchestrator.mesh_p2p.discover_peers():
                peer_data = peer.to_dict() if hasattr(peer, "to_dict") else dict(peer)
                peer_id = peer_data.get("peer_id", peer_data.get("id", peer_data.get("name", "peer")))
                peers.append({
                    "id": peer_id,
                    "name": peer_data.get("name", peer_id),
                    "status": peer_data.get("status", "unknown"),
                    "address": peer_data.get("address"),
                })
        except Exception:
            peers = []
    return {
        "enabled": bool(a2a_cfg.get("enabled", False)),
        "protocol_version": a2a_cfg.get("version", "0.3"),
        "agent_name": a2a_cfg.get("agent_name", "Antigravity Kernel"),
        "mesh": mesh,
        "peers": peers,
    }


def build_project_registry(orchestrator=None, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    config = config or load_runtime_yaml()
    return {
        "skills": build_skill_catalog(config),
        "mcp_servers": build_mcp_catalog(config, orchestrator=orchestrator),
        "folders": build_folder_catalog(config),
        "a2a": build_a2a_catalog(config, orchestrator=orchestrator),
        "governance_defaults": config.get("governance", {}),
    }
