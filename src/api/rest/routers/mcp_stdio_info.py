"""
Stdio MCP Router (Info) - REST API endpoints for stdio MCP server information.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Any, Dict

from src.api.rest.dependencies import get_current_user_dep
from src.infrastructure.auth.jwt_auth import TokenPayload
from src.services.mcp.stdio_manager import stdio_mcp_manager, ServerStatus

router = APIRouter(prefix="/api/v1/mcp/stdio", tags=["Stdio MCP Info"])

@router.get("/servers")
async def list_stdio_servers(current_user: TokenPayload = Depends(get_current_user_dep)):
    """List all stdio MCP servers for the current tenant."""
    servers = stdio_mcp_manager.list_servers(current_user.tenant_id)
    return {
        "status": "success",
        "servers": servers,
        "count": len(servers),
    }

@router.get("/{server_name}/tools")
async def get_server_tools(
    server_name: str,
    current_user: TokenPayload = Depends(get_current_user_dep),
):
    """Get tools available from a specific stdio MCP server."""
    try:
        tools = await stdio_mcp_manager.get_tools(
            tenant_id=current_user.tenant_id,
            name=server_name,
        )
        return {
            "status": "success",
            "server": server_name,
            "tools": tools,
            "count": len(tools),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/dashboard")
async def get_stdio_dashboard(current_user: TokenPayload = Depends(get_current_user_dep)):
    """Get dashboard data for all stdio MCP servers."""
    servers = stdio_mcp_manager.list_servers(current_user.tenant_id)

    running = sum(1 for s in servers if s["status"] == ServerStatus.RUNNING.value)
    error = sum(1 for s in servers if s["status"] == ServerStatus.ERROR.value)
    starting = sum(1 for s in servers if s["status"] == ServerStatus.STARTING.value)

    return {
        "status": "success",
        "servers": servers,
        "total_count": len(servers),
        "running_count": running,
        "error_count": error,
        "starting_count": starting,
        "metrics": stdio_mcp_manager.get_all_metrics(),
    }

@router.get("/metrics")
async def get_stdio_metrics(current_user: TokenPayload = Depends(get_current_user_dep)):
    """Get aggregated metrics for all stdio MCP servers."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required for metrics access.",
        )
    return {
        "status": "success",
        "metrics": stdio_mcp_manager.get_all_metrics(),
    }
