"""
Stdio MCP Router (Core) - REST API endpoints for stdio-based MCP server management.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from src.api.rest.dependencies import get_current_user_dep
from src.infrastructure.auth.jwt_auth import TokenPayload
from src.services.mcp.stdio_manager import stdio_mcp_manager
from src.services.mcp.stdio_protocol import MCPProtocolError
from src.api.rest.routers.mcp_schemas import (
    StdioServerRegistration,
    ToolExecutionRequest,
)

router = APIRouter(prefix="/api/v1/mcp/stdio", tags=["Stdio MCP"])

ALLOWED_ROLES = {"admin", "developer"}

def _deny_without_role(current_user: TokenPayload) -> None:
    if current_user.role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Admin or developer role required.",
        )

@router.post("/register")
async def register_stdio_server(
    request: StdioServerRegistration,
    current_user: TokenPayload = Depends(get_current_user_dep),
):
    """Register and start a new stdio MCP server."""
    _deny_without_role(current_user)

    try:
        server = await stdio_mcp_manager.register_server(
            tenant_id=current_user.tenant_id,
            name=request.name,
            command=request.command,
            args=request.args,
            working_dir=request.working_dir,
            description=request.description,
        )

        return {
            "status": "success",
            "message": f"Server '{request.name}' registered and started",
            "server": {
                "name": server.name,
                "description": server.description,
                "command": server.command,
                "args": server.args,
                "status": server.status.value,
                "tool_count": len(server.tools),
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except MCPProtocolError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register server: {str(e)}",
        )

@router.delete("/{server_name}")
async def unregister_stdio_server(
    server_name: str,
    current_user: TokenPayload = Depends(get_current_user_dep),
):
    """Unregister and stop an stdio MCP server."""
    _deny_without_role(current_user)

    try:
        success = await stdio_mcp_manager.unregister_server(
            tenant_id=current_user.tenant_id,
            name=server_name,
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Server '{server_name}' not found",
            )
        return {"status": "success", "message": f"Server '{server_name}' unregistered"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/{server_name}/execute")
async def execute_stdio_tool(
    server_name: str,
    request: ToolExecutionRequest,
    current_user: TokenPayload = Depends(get_current_user_dep),
):
    """Execute a tool from an stdio MCP server."""
    _deny_without_role(current_user)

    try:
        result = await stdio_mcp_manager.execute_tool(
            tenant_id=current_user.tenant_id,
            server_name=server_name,
            tool_name=request.tool_name,
            arguments=request.arguments,
        )
        return {
            "status": "success",
            "server": server_name,
            "tool": request.tool_name,
            "result": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except MCPProtocolError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))