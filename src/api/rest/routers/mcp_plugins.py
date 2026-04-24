"""
MCP Plugin Router
Allows admins to hot-reload new tools dynamically.
"""
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Any

from src.api.rest.dependencies import get_current_user_dep
from src.infrastructure.auth.jwt_auth import TokenPayload
from src.services.mcp.mcp_hub import mcp_hub
from src.tools.registry import get_tool_catalog

router = APIRouter(prefix="/mcp", tags=["mcp"])

class ToolParameterSchema(BaseModel):
    name: str
    type: str = "string"
    description: str = ""
    required: bool = True
    default: Any = None

class PluginRegistrationRequest(BaseModel):
    name: str = Field(..., description="Unique tool name")
    description: str = Field(..., description="Prompt description for the agent")
    endpoint_url: str = Field(..., description="REST endpoint to proxy the execution to")
    parameters: List[ToolParameterSchema] = Field(default_factory=list)


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
    if current_user.role not in {"admin", "developer"}:
        raise HTTPException(status_code=403, detail="You are not allowed to register MCP plugins.")
    if not request.endpoint_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Plugin endpoint must be http:// or https://")
    try:
        mcp_hub.register_plugin(request.model_dump())
        plugin = next(
            (item for item in get_tool_catalog() if item["name"] == request.name and item["origin"] == "plugin"),
            None,
        )
        return {
            "status": "success",
            "message": f"Plugin {request.name} registered and hot-loaded.",
            "plugin": plugin,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/plugins")
async def list_plugins(current_user: TokenPayload = Depends(get_current_user_dep)):
    """List all dynamically loaded MCP plugins."""
    plugins = [tool for tool in get_tool_catalog() if tool["origin"] == "plugin"]
    return {"status": "success", "plugins": plugins}


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
