"""
Write File Tool
"""
import os
import aiofiles
from typing import Any, Dict

from src.tools.core.base import BaseTool, ToolParameter
from src.domain.exceptions import ToolExecutionError

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
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            
            async with aiofiles.open(filepath, mode='w', encoding='utf-8') as f:
                await f.write(content)
                
            return {
                "success": True,
                "filepath": os.path.abspath(filepath),
                "bytes_written": len(content.encode('utf-8'))
            }
        except Exception as e:
            raise ToolExecutionError(str(e), self.name)
