"""Git MCP tools - Clone, Read, Write operations."""
import subprocess
from pathlib import Path
from typing import Any, Dict

from src.tools.core.base import BaseTool, ToolParameter
from src.infrastructure.sandbox.kubernetes import get_sandbox_executor


class GitCloneTool(BaseTool):
    """Clone repositories into isolated sandbox."""
    name = "git_clone"
    description = "Clone a GitHub repository to workspace"
    parameters = [
        ToolParameter(name="repo_url", type="string", description="HTTPS or SSH URL"),
        ToolParameter(name="branch", type="string", description="Branch to clone", required=False, default="main"),
    ]
    requires_sandbox = True

    async def execute(self, session_id: str, **kwargs) -> Dict[str, Any]:
        repo_url = kwargs.get("repo_url")
        branch = kwargs.get("branch", "main")
        workspace = "/workspace/repos"

        executor = await get_sandbox_executor()
        command = f"mkdir -p {workspace} && cd {workspace} && git clone -b {branch} {repo_url} . 2>&1"

        result = await executor.execute(command=command)
        return {
            "success": result.exit_code == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "workspace": workspace,
            "branch": branch,
        }


class GitReadTool(BaseTool):
    """Read files from cloned repository."""
    name = "git_read"
    description = "Read file contents from repository"
    parameters = [
        ToolParameter(name="filepath", type="string", description="Relative file path"),
        ToolParameter(name="limit", type="integer", description="Max lines to read", required=False, default=500),
    ]
    requires_sandbox = True

    async def execute(self, session_id: str, **kwargs) -> Dict[str, Any]:
        filepath = kwargs.get("filepath")
        limit = kwargs.get("limit", 500)
        workspace = "/workspace/repos"
        full_path = f"{workspace}/{filepath}"

        from src.infrastructure.sandbox.kubernetes import execute_sandboxed
        # Use cat + head for isolated reading
        command = f"cat {full_path} | head -n {limit}"
        
        try:
            result = await execute_sandboxed(command=command)
            return {
                "success": result.exit_code == 0,
                "content": result.stdout,
                "filepath": filepath,
                "truncated": "Truncated by limit" if result.exit_code == 0 else "Error",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class GitWriteTool(BaseTool):
    """Write files to repository on feature branch."""
    name = "git_write"
    description = "Write file to repository (creates feature branch)"
    parameters = [
        ToolParameter(name="filepath", type="string", description="Relative file path"),
        ToolParameter(name="content", type="string", description="File content"),
        ToolParameter(name="branch", type="string", description="Feature branch name"),
    ]
    requires_sandbox = True

    async def execute(self, session_id: str, **kwargs) -> Dict[str, Any]:
        filepath = kwargs.get("filepath")
        content = kwargs.get("content", "")
        branch = kwargs.get("branch", f"agent/edit-{hash(filepath) % 10000}")
        workspace = "/workspace/repos"

        # Escape content for shell
        safe_content = content.replace("'", "'\"'\"'")

        executor = await get_sandbox_executor()
        command = f"""cd {workspace} && \
            git checkout -b {branch} 2>/dev/null || git checkout {branch} && \
            mkdir -p $(dirname {filepath}) && \
            echo '{safe_content}' > {filepath} && \
            git add {filepath}"""

        result = await executor.execute(command=command)
        return {
            "success": result.exit_code == 0,
            "filepath": filepath,
            "branch": branch,
            "bytes_written": len(content),
        }
