from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any
import json

router = APIRouter()

@router.post("/mcp")
async def mcp_streamable_http_post(request: Dict[str, Any]):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """MCP 2026 Streamable HTTP — POST for JSON-RPC requests."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    from project_kernel_runtime.protocols.mcp_server import MCPServer
    mcp = MCPServer()
    mcp.register_tools_from_executor()
    
    # Process JSON-RPC
    result = await mcp.handle_streamable_http_post(
        json.dumps(request).encode(),
        headers={},
    )
    return result


@router.get("/mcp")
async def mcp_streamable_http_get():
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """MCP 2026 Streamable HTTP — GET for SSE stream."""
    from fastapi.responses import StreamingResponse
    
    async def sse_stream():
        from project_kernel_runtime.services.fastapi_server import orchestrator
        yield "event: ping\ndata: {}\n\n"
    
    return StreamingResponse(sse_stream(), media_type="text/event-stream")


# ============================================================================
# A2A v0.3 Protocol Endpoints
# ============================================================================

@router.post("/a2a")
async def a2a_jsonrpc(request: Dict[str, Any]):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """A2A v0.3 JSON-RPC handler for tasks/send, tasks/get, tasks/cancel."""
    from project_kernel_runtime.integrations.a2a_protocol import A2AHandler
    handler = A2AHandler()
    
    method = request.get("method", "")
    params = request.get("params", {})
    msg_id = request.get("id")
    
    result = await handler.handle_jsonrpc(method, params)
    
    if "error" in result:
        return {"jsonrpc": "2.0", "id": msg_id, "error": result["error"]}
    return {"jsonrpc": "2.0", "id": msg_id, "result": result.get("result", result)}


# ============================================================================
# Agentic Loop Endpoint
# ============================================================================

