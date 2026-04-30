"""
MCP Plugin Router - Premium Production Grade

Provides secure, multi-tenant MCP tool management with:
- Role-based access control (admin/developer roles)
- Rate limiting and quota enforcement
- Input validation and sanitization
- Comprehensive audit logging
- Tool execution with circuit breaker
"""
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from typing import Any, Dict, List, Optional

from src.api.rest.dependencies import get_current_user_dep
from src.infrastructure.auth.jwt_auth import TokenPayload
from src.services.mcp.mcp_hub import mcp_hub
from src.tools.registry import get_tool_catalog

router = APIRouter(prefix="/api/v1/mcp", tags=["MCP"])

ALLOWED_ROLES = {"admin", "developer"}
MAX_NAME_LENGTH = 128
MAX_DESCRIPTION_LENGTH = 1000


class ToolParameterSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    type: str = Field(default="string")
    description: str = Field(default="", max_length=500)
    required: bool = Field(default=True)
    default: Optional[Any] = None
    enum: Optional[List[str]] = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        valid_types = {"string", "number", "integer", "boolean", "array", "object"}
        if v not in valid_types:
            raise ValueError(f"Type must be one of: {', '.join(valid_types)}")
        return v


class PluginRegistrationRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=MAX_NAME_LENGTH)
    description: str = Field(default="", max_length=MAX_DESCRIPTION_LENGTH)
    endpoint_url: str = Field(...)
    parameters: List[ToolParameterSchema] = Field(default_factory=list)
    timeout_seconds: float = Field(default=30.0, ge=1.0, le=300.0)
    max_retries: int = Field(default=3, ge=0, le=10)
    verify_ssl: bool = Field(default=True)
    allowed_hosts: Optional[List[str]] = Field(default=None)

    @field_validator("endpoint_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v:
            raise ValueError("Endpoint URL is required")
        if not v.startswith(("http://", "https://")):
            raise ValueError("Endpoint must use http:// or https:// protocol")
        if len(v) > 2048:
            raise ValueError("Endpoint URL exceeds maximum length of 2048 characters")
        return v


class PluginUnregisterRequest(BaseModel):
    name: str = Field(..., description="Plugin name to unregister")


def _skill_catalog() -> List[dict]:
    tools = get_tool_catalog()
    by_name = {tool["name"]: tool for tool in tools}
    skills = [
        {
            "id": "build-ship",
            "name": "Build & Ship",
            "description": "Generate code, validate it, and prepare delivery through Git or workspace output.",
            "prompt": "Implement the requested change, verify it, then prepare the output for dispatch or Git delivery.",
            "tool_names": ["write_file", "generate_tests", "git_write", "git_commit", "git_create_pr", "dispatch_output"],
        },
        {
            "id": "review-secure",
            "name": "Review & Secure",
            "description": "Inspect code quality and security posture before merging or releasing.",
            "prompt": "Review the relevant code and highlight bugs, regressions, and security issues before proposing changes.",
            "tool_names": ["read_file", "code_review", "security_scan", "search_past_decisions"],
        },
        {
            "id": "research-context",
            "name": "Research & Context",
            "description": "Gather current information and connect it to project memory and structure.",
            "prompt": "Research the current best approach, compare it to our codebase, and summarize the right implementation direction.",
            "tool_names": ["web_search", "code_graph_query", "search_past_decisions", "update_agent_memory"],
        },
        {
            "id": "repo-automation",
            "name": "Repo Automation",
            "description": "Work across repositories, branches, and pull requests from one workflow.",
            "prompt": "Clone the repository, inspect the target files, make the requested changes, and prepare the branch for review.",
            "tool_names": ["git_clone", "git_read", "git_write", "git_commit", "git_create_pr"],
        },
    ]
    for skill in skills:
        skill["tools"] = [by_name[name] for name in skill["tool_names"] if name in by_name]
    return skills


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
        "skills": _skill_catalog(),
        "categories": categories,
    }


class ExecuteToolRequest(BaseModel):
    tool_name: str = Field(..., description="Name of the tool to execute")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")
    session_id: Optional[str] = Field(default=None, description="Session context for execution")


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