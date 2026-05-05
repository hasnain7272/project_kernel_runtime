"""
Stdio Writer - Wraps asyncio subprocess streams.
"""
import asyncio
from src.services.mcp.stdio_messages import MCPProtocolError

class StdinStdoutWriter:
    def __init__(self, process: asyncio.subprocess.Process):
        self._process = process

    async def write(self, message: str) -> None:
        if self._process.stdin is None:
            raise MCPProtocolError("Process stdin is None")
        self._process.stdin.write(message + "\n")
        await self._process.stdin.drain()

    async def read_line(self) -> str:
        if self._process.stdout is None:
            raise MCPProtocolError("Process stdout is None")
        line = await self._process.stdout.readline()
        if not line:
            raise MCPProtocolError("Process stdout closed")
        return line.decode("utf-8").strip()
