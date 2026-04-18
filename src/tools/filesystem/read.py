"""
Read file tool.
"""
import os
from typing import Any, Dict

import aiofiles

from src.domain.exceptions import ToolExecutionError
from src.infrastructure.runtime.paths import resolve_workspace_path
from src.tools.core.base import BaseTool, ToolParameter


class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Read the contents of a file on the local filesystem. Always returns strings."
    parameters = [
        ToolParameter(name="filepath", type="string", description="Absolute or relative path to the file"),
    ]
    requires_sandbox = False

    async def execute(self, session_id: str, filepath: str, **kwargs) -> Dict[str, Any]:
        try:
            resolved_path = str(resolve_workspace_path(filepath))
            if not os.path.exists(resolved_path):
                return {"success": False, "error": f"File not found: {resolved_path}"}

            async with aiofiles.open(resolved_path, mode="r", encoding="utf-8") as f:
                content = await f.read()

            return {
                "success": True,
                "content": content,
                "lines": len(content.splitlines()),
                "filepath": resolved_path,
            }
        except UnicodeDecodeError:
            return {"success": False, "error": f"File provides binary data or non-UTF-8 content: {filepath}"}
        except Exception as exc:
            raise ToolExecutionError(str(exc), self.name) from exc
