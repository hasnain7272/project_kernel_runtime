"""
MCP Client: Model Context Protocol Implementation

Inspired by Anthropic MCP + OpenHands tool integration
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
import websockets
from websockets.exceptions import ConnectionClosedError

@dataclass
class MCPTool:
    """MCP Tool definition"""
    name: str
    description: str
    input_schema: Dict[str, Any]

@dataclass
class MCPResource:
    """MCP Resource definition"""
    uri: str
    name: str
    description: str
    mime_type: str

@dataclass
class MCPPrompt:
    """MCP Prompt definition"""
    name: str
    description: str
    arguments: List[Dict[str, Any]]

class MCPClient:
    """Client for MCP server communication"""

    def __init__(self, server_url: str = "ws://localhost:3000"):
        self.server_url = server_url
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.tools: Dict[str, MCPTool] = {}
        self.resources: Dict[str, MCPResource] = {}
        self.prompts: Dict[str, MCPPrompt] = {}
        self.message_id = 0
        self.pending_requests: Dict[int, asyncio.Future] = {}

    async def connect(self):
        """Connect to MCP server"""
        try:
            self.websocket = await websockets.connect(self.server_url)
            # Start message handler
            asyncio.create_task(self._message_handler())
            # Initialize connection
            await self._initialize()
        except Exception as e:
            raise ConnectionError(f"Failed to connect to MCP server: {e}")

    async def disconnect(self):
        """Disconnect from MCP server"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None

    async def _initialize(self):
        """Initialize MCP connection"""
        init_request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {},
                    "prompts": {}
                },
                "clientInfo": {
                    "name": "project_kernel_runtime",
                    "version": "1.0.0"
                }
            }
        }

        response = await self._send_request(init_request)
        if response.get("result"):
            # Store server capabilities
            server_capabilities = response["result"].get("capabilities", {})
            if "tools" in server_capabilities:
                await self._list_tools()
            if "resources" in server_capabilities:
                await self._list_resources()
            if "prompts" in server_capabilities:
                await self._list_prompts()

    async def _list_tools(self):
        """List available tools"""
        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/list",
            "params": {}
        }

        response = await self._send_request(request)
        if response.get("result"):
            for tool_data in response["result"].get("tools", []):
                tool = MCPTool(
                    name=tool_data["name"],
                    description=tool_data["description"],
                    input_schema=tool_data["inputSchema"]
                )
                self.tools[tool.name] = tool

    async def _list_resources(self):
        """List available resources"""
        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "resources/list",
            "params": {}
        }

        response = await self._send_request(request)
        if response.get("result"):
            for resource_data in response["result"].get("resources", []):
                resource = MCPResource(
                    uri=resource_data["uri"],
                    name=resource_data["name"],
                    description=resource_data.get("description", ""),
                    mime_type=resource_data.get("mimeType", "")
                )
                self.resources[resource.uri] = resource

    async def _list_prompts(self):
        """List available prompts"""
        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "prompts/list",
            "params": {}
        }

        response = await self._send_request(request)
        if response.get("result"):
            for prompt_data in response["result"].get("prompts", []):
                prompt = MCPPrompt(
                    name=prompt_data["name"],
                    description=prompt_data.get("description", ""),
                    arguments=prompt_data.get("arguments", [])
                )
                self.prompts[prompt.name] = prompt

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call an MCP tool"""
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not available")

        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        response = await self._send_request(request)
        if "error" in response:
            raise RuntimeError(f"Tool call failed: {response['error']}")

        return response.get("result")

    async def read_resource(self, uri: str) -> str:
        """Read an MCP resource"""
        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "resources/read",
            "params": {
                "uri": uri
            }
        }

        response = await self._send_request(request)
        if "error" in response:
            raise RuntimeError(f"Resource read failed: {response['error']}")

        contents = response.get("result", {}).get("contents", [])
        if contents:
            return contents[0].get("text", "")
        return ""

    async def get_prompt(self, prompt_name: str, arguments: Optional[Dict[str, Any]] = None) -> str:
        """Get an MCP prompt"""
        if prompt_name not in self.prompts:
            raise ValueError(f"Prompt {prompt_name} not available")

        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "prompts/get",
            "params": {
                "name": prompt_name,
                "arguments": arguments or {}
            }
        }

        response = await self._send_request(request)
        if "error" in response:
            raise RuntimeError(f"Prompt get failed: {response['error']}")

        messages = response.get("result", {}).get("messages", [])
        # Convert messages to text
        prompt_text = ""
        for message in messages:
            if message.get("role") == "user":
                prompt_text += f"User: {message.get('content', {}).get('text', '')}\n"
            elif message.get("role") == "assistant":
                prompt_text += f"Assistant: {message.get('content', {}).get('text', '')}\n"

        return prompt_text

    def _next_id(self) -> int:
        """Get next message ID"""
        self.message_id += 1
        return self.message_id

    async def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send JSON-RPC request and wait for response"""
        if not self.websocket:
            raise ConnectionError("Not connected to MCP server")

        request_id = request["id"]
        future = asyncio.Future()
        self.pending_requests[request_id] = future

        await self.websocket.send(json.dumps(request))

        try:
            response = await asyncio.wait_for(future, timeout=30.0)
            return response
        except asyncio.TimeoutError:
            raise TimeoutError(f"Request {request_id} timed out")
        finally:
            self.pending_requests.pop(request_id, None)

    async def _message_handler(self):
        """Handle incoming messages from MCP server"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    if "id" in data and data["id"] in self.pending_requests:
                        # This is a response to our request
                        future = self.pending_requests[data["id"]]
                        if not future.done():
                            future.set_result(data)
                    else:
                        # This is a notification or server-initiated message
                        await self._handle_notification(data)
                except json.JSONDecodeError:
                    print(f"Invalid JSON received: {message}")
        except ConnectionClosedError:
            print("MCP connection closed")
        except Exception as e:
            print(f"Message handler error: {e}")

    async def _handle_notification(self, notification: Dict[str, Any]):
        """Handle MCP notifications"""
        method = notification.get("method")
        if method == "tools/list_changed":
            # Tools list changed, refresh
            await self._list_tools()
        elif method == "resources/list_changed":
            # Resources list changed, refresh
            await self._list_resources()
        elif method == "prompts/list_changed":
            # Prompts list changed, refresh
            await self._list_prompts()
        # Add more notification handlers as needed