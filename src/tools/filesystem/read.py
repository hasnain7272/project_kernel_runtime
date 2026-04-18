"""
Read File Tool
"""
import os
import aiofiles
from typing import Any, Dict

from src.tools.core.base import BaseTool, ToolParameter
from src.domain.exceptions import ToolExecutionError

class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Read the contents of a file on the local filesystem. Always returns strings."
    parameters = [
        ToolParameter(name="filepath", type="string", description="Absolute or relative path to the file"),
    ]
    requires_sandbox = False

    async def execute(self, session_id: str, filepath: str, **kwargs) -> Dict[str, Any]:
        """Reads file asynchronously without blocking the event loop."""
        try:
            # Note: Path traversal checks should be managed by the Governance Engine 
            # injected above this layer, keeping this tool purely focused on execution.
            if not os.path.exists(filepath):
                 return {"success": False, "error": f"File not found: {filepath}"}
                 
            async with aiofiles.open(filepath, mode='r', encoding='utf-8') as f:
                content = await f.read()
                
            return {
                "success": True,
                "content": content,
                "lines": len(content.splitlines()),
                "filepath": os.path.abspath(filepath)
            }
        except UnicodeDecodeError:
            return {"success": False, "error": f"File provides binary data or non-UTF-8 content: {filepath}"}
        except Exception as e:
            raise ToolExecutionError(str(e), self.name)
