"""
MCP Plugin Router (Info) - Premium Production Grade

Provides catalog and metric endpoints for MCP dynamic tools.
"""
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Any, Dict

from src.api.rest.dependencies import get_current_user_dep
from src.infrastructure.auth.jwt_auth import TokenPayload
from src.services.mcp.mcp_hub import mcp_hub
from src.tools.registry import get_tool_catalog
from src.services.mcp.mcp_skills import _skill_catalog
from src.services.mcp.stdio_manager import ServerStatus, stdio_mcp_manager

router = APIRouter(prefix="/api/v1/mcp", tags=["MCP Info"])

@router.get("/plugins")
async def list_plugins(current_user: TokenPayload = Depends(get_current_user_dep)):
    """List all dynamically loaded MCP plugins for the current tenant."""
    plugins = mcp_hub.list_plugins(tenant_id=current_user.tenant_id)
    return {
        "status": "success",
        "plugins": plugins,
        "count": len(plugins),
    }

@router.get("/plugins/catalog")
async def list_all_plugins(current_user: TokenPayload = Depends(get_current_user_dep)):
    """List all MCP plugins from the tool catalog."""
    plugins = [tool for tool in get_tool_catalog() if tool["origin"] == "plugin"]
    return {"status": "success", "plugins": plugins, "count": len(plugins)}

@router.get("/plugins/{plugin_name}/metrics")
async def get_plugin_metrics(
    plugin_name: str,
    current_user: TokenPayload = Depends(get_current_user_dep),
):
    """Get performance metrics for a specific MCP plugin."""
    metrics = mcp_hub.get_plugin_metrics(plugin_name)
    if not metrics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin '{plugin_name}' not found.",
        )
    return {"status": "success", "metrics": metrics}

@router.get("/metrics")
async def get_all_metrics(current_user: TokenPayload = Depends(get_current_user_dep)):
    """Get aggregated metrics for all MCP plugins."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required for metrics access.",
        )
    return {"status": "success", "metrics": mcp_hub.get_all_metrics()}

@router.get("/skills")
async def list_skills(current_user: TokenPayload = Depends(get_current_user_dep)):
    """List curated studio skills backed by the current tool registry."""
    return {"status": "success", "skills": _skill_catalog()}

@router.get("/catalog")
async def get_capability_catalog(current_user: TokenPayload = Depends(get_current_user_dep)):
    """Return the complete UI catalog for built-in tools, skills, and plugins."""
    tools = get_tool_catalog()
    plugins = [tool for tool in tools if tool["origin"] == "plugin"]
    skills = _skill_catalog()
    stdio_servers = stdio_mcp_manager.list_servers(current_user.tenant_id)
    grouped = defaultdict(list)
    for tool in tools:
        grouped[tool["category"]].append(tool)
    categories = [
        {"id": category, "count": len(items), "label": category.replace("_", " ").title()}
        for category, items in sorted(grouped.items())
    ]
    return {
        "status": "success",
        "tools": tools,
        "plugins": plugins,
        "skills": skills,
        "categories": categories,
        "summary": {
            "tools": len(tools),
            "skills": len(skills),
            "plugins": len(plugins),
            "categories": len(categories),
            "ready_skills": sum(1 for skill in skills if skill.get("ready")),
            "missing_skill_tools": sum(len(skill.get("missing_tools", [])) for skill in skills),
            "stdio_servers": len(stdio_servers),
            "stdio_running": sum(1 for server in stdio_servers if server.get("status") == ServerStatus.RUNNING.value),
        },
    }

@router.get("/dashboard")
async def get_mcp_dashboard(current_user: TokenPayload = Depends(get_current_user_dep)):
    """Get MCP dashboard data with plugin status, metrics, and management options."""
    tools = get_tool_catalog()
    plugins = [tool for tool in tools if tool["origin"] == "plugin"]

    plugin_names = mcp_hub.list_plugins(tenant_id=current_user.tenant_id)
    all_metrics = mcp_hub.get_all_metrics()

    plugin_details = []
    for plugin_name in plugin_names:
        metrics = all_metrics.get(plugin_name, {})
        plugin = mcp_hub.get_plugin(plugin_name)

        status_val = "unknown"
        if plugin:
            status_val = plugin.status.value if hasattr(plugin.status, 'value') else str(plugin.status)

        plugin_info = next((p for p in plugins if p["name"] == plugin_name), {})
        plugin_details.append({
            "name": plugin_name,
            "description": plugin_info.get("description", ""),
            "endpoint_url": plugin_info.get("endpoint_url", ""),
            "status": status_val,
            "total_calls": metrics.get("total_calls", 0),
            "failed_calls": metrics.get("failed_calls", 0),
            "success_rate": metrics.get("success_rate", 1.0),
            "avg_latency_ms": metrics.get("avg_latency_ms", 0),
            "last_called": metrics.get("last_called"),
        })

    return {
        "status": "success",
        "plugins": plugin_details,
        "total_count": len(plugin_details),
        "healthy_count": sum(1 for p in plugin_details if p["status"] == "active"),
        "circuit_open_count": sum(1 for p in plugin_details if p["status"] == "error"),
    }
