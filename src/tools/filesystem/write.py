"""
Write file tool.
"""
import os
from typing import Any, Dict

import aiofiles

from src.domain.exceptions import ToolExecutionError
from src.infrastructure.runtime.paths import resolve_workspace_path
from src.tools.core.base import BaseTool, ToolParameter


class WriteFileTool(BaseTool):
    name = "write_file"
    description = "Write entire string content to a file, overwriting it if it exists."
    parameters = [
        ToolParameter(name="filepath", type="string", description="Absolute or relative path to the file"),
        ToolParameter(name="content", type="string", description="The string content to write"),
    ]
    requires_sandbox = False

    async def execute(self, session_id: str, filepath: str, content: str, **kwargs) -> Dict[str, Any]:
        try:
            resolved_path = str(resolve_workspace_path(filepath))
            os.makedirs(os.path.dirname(resolved_path), exist_ok=True)
            async with aiofiles.open(resolved_path, mode="w", encoding="utf-8") as f:
                await f.write(content)

            return {
                "success": True,
                "filepath": resolved_path,
                "bytes_written": len(content.encode("utf-8")),
            }
        except Exception as exc:
            raise ToolExecutionError(str(exc), self.name) from exc
