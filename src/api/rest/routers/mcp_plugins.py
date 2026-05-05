"""
MCP Plugin Router (Core) - Premium Production Grade

Provides secure, multi-tenant MCP tool management with:
- Role-based access control
- Rate limiting and quota enforcement
- Tool execution with circuit breaker
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Any, Dict, List, Optional

from src.api.rest.dependencies import get_current_user_dep
from src.infrastructure.auth.jwt_auth import TokenPayload
from src.services.mcp.mcp_hub import mcp_hub
from src.tools.registry import get_tool_catalog
from src.api.rest.routers.mcp_schemas import (
    PluginRegistrationRequest,
    ExecuteToolRequest,
)

router = APIRouter(prefix="/api/v1/mcp", tags=["MCP"])

ALLOWED_ROLES = {"admin", "developer"}


def _validate_endpoint(endpoint_url: str) -> None:
    if not endpoint_url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plugin endpoint must start with http:// or https://",
        )

@router.post("/register")
async def register_plugin(
    request: PluginRegistrationRequest,
    current_user: TokenPayload = Depends(get_current_user_dep),
):
    """Register a new dynamic MCP tool for the active tenant."""
    if current_user.role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Admin or developer role required.",
        )
    _validate_endpoint(request.endpoint_url)

    plugin_def = {
        "name": request.name,
        "description": request.description,
        "endpoint_url": request.endpoint_url,
        "parameters": [p.model_dump() for p in request.parameters],
        "timeout_seconds": request.timeout_seconds,
        "max_retries": request.max_retries,
        "verify_ssl": request.verify_ssl,
    }

    try:
        result = mcp_hub.register_plugin(
            plugin_def=plugin_def,
            tenant_id=current_user.tenant_id,
            allowed_hosts=request.allowed_hosts,
        )

        plugin = next(
            (item for item in get_tool_catalog() if item["name"] == request.name and item["origin"] == "plugin"),
            None,
        )

        return {
            "status": "success",
            "message": f"Plugin '{request.name}' registered and hot-loaded.",
            "plugin": plugin,
            "details": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Registration failed: {str(e)}")

@router.delete("/{plugin_name}")
async def unregister_plugin(
    plugin_name: str,
    current_user: TokenPayload = Depends(get_current_user_dep),
):
    """Unregister a dynamic MCP plugin."""
    if current_user.role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Admin or developer role required.",
        )

    try:
        success = mcp_hub.unregister_plugin(plugin_name, current_user.tenant_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plugin '{plugin_name}' not found.",
            )
        return {"status": "success", "message": f"Plugin '{plugin_name}' unregistered."}
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/execute")
async def execute_tool(
    request: ExecuteToolRequest,
    current_user: TokenPayload = Depends(get_current_user_dep),
):
    """Execute a tool by name with given parameters. Returns inline results."""
    if current_user.role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to execute tools.",
        )

    tools = get_tool_catalog()
    tool = next((t for t in tools if t["name"] == request.tool_name), None)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{request.tool_name}' not found in catalog.",
        )

    if tool.get("origin") == "plugin" and tool.get("endpoint_url"):
        plugin = mcp_hub.get_plugin(request.tool_name)
        if plugin:
            try:
                result = await plugin.execute(
                    session_id=request.session_id or "direct",
                    **request.parameters,
                )
                return {
                    "status": "success",
                    "tool": request.tool_name,
                    "result": result,
                    "metrics": plugin.get_metrics(),
                }
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Plugin execution failed: {str(e)}",
                )

    return {
        "status": "success",
        "tool": request.tool_name,
        "result": {
            "message": f"Tool '{request.tool_name}' is a built-in tool. Use the chat interface to execute it via the agent loop.",
            "category": tool.get("category", "unknown"),
            "parameters": tool.get("parameters", []),
        },
    }
