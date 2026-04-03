"""
FastAPI Server: HTTP/WebSocket API

Enterprise API Gateway to the Coding Agent Swarm with AgentScope-inspired pipelines.
"""

from fastapi import FastAPI, WebSocket, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, RedirectResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
from contextlib import asynccontextmanager
import sys
import os
from pathlib import Path

# Add src to path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if "OLLAMA_API_BASE" not in os.environ:
    os.environ["OLLAMA_API_BASE"] = "http://127.0.0.1:11500"

# Core Dependencies
from project_kernel_runtime.kernel.task_state_machine import TaskStatus
from project_kernel_runtime.services.research_api import router as research_router
from project_kernel_runtime.services.project_registry import build_project_registry, load_runtime_yaml, session_payload
from project_kernel_runtime.memory.state_hub import state_hub

# Global orchestrator
orchestrator = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    from project_kernel_runtime.kernel.orchestrator import init_orchestrator
    global orchestrator
    orchestrator = await init_orchestrator()
    
    # Link WebSocket handler to orchestrator for real-time events
    from project_kernel_runtime.services.ui_websocket import get_ui_websocket_handler
    handler = get_ui_websocket_handler()
    await handler.link_orchestrator(orchestrator)
    
    yield
    if orchestrator:
        await orchestrator.shutdown()

app = FastAPI(
    title="Project Kernel Runtime API",
    version="2.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routes & Hubs ---
app.include_router(research_router, prefix="/research")
from project_kernel_runtime.services.router_agent import router as agent_router
from project_kernel_runtime.services.router_mcp import router as mcp_router
from project_kernel_runtime.services.router_runtime import router as runtime_router
app.include_router(agent_router, prefix="/api/agent")
app.include_router(mcp_router, prefix="/api/mcp")
app.include_router(runtime_router, prefix="/api/runtime")

# --- Workflow Engine Endpoint (AgentScope-inspired) ---
@app.post("/api/workflows/run")
async def run_workflow(request: Dict[str, Any]):
    """Execute a structured AgentScope-inspired pipeline."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    session_id = request.get("session_id")
    pipeline_type = request.get("pipeline", "sequential")
    name = request.get("name", "Unnamed Workflow")
    steps_data = request.get("steps", [])
    
    session = orchestrator.sessions.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    from project_kernel_runtime.kernel.workflow_engine import PipelineStep, SequentialPipeline, FanoutPipeline
    from project_kernel_runtime.kernel.tool_executor import ExecutionContext
    
    steps = [PipelineStep(**step) for step in steps_data]
    context = ExecutionContext(
        session_id=session_id,
        user_id=session.user_id,
        workspace_path=session.workspace_path
    )
    
    # Broadcast start event
    from project_kernel_runtime.services.ui_websocket import get_ui_websocket_handler
    handler = get_ui_websocket_handler()
    if handler:
        await handler.broadcaster.broadcast({
            "type": "event",
            "event_type": "workflow.started",
            "session_id": session_id,
            "data": {"name": name, "total_steps": len(steps)}
        })
    
    if pipeline_type == "sequential":
        pipeline = SequentialPipeline(name, steps, orchestrator.tool_executor)
    else:
        pipeline = FanoutPipeline(name, steps, orchestrator.tool_executor)
        
    result = await pipeline.run(request.get("input", {}), context)
    
    if handler:
        await handler.broadcaster.broadcast({
            "type": "event",
            "event_type": "workflow.completed" if result.success else "workflow.failed",
            "session_id": session_id,
            "data": {"success": result.success, "error": result.error}
        })
    
    return {
        "pipeline_id": result.pipeline_id,
        "success": result.success,
        "outputs": result.outputs,
        "steps": result.step_results
    }

@app.get("/status/full")
async def get_full_status():
    """Provides full system status for the UI ops polling."""
    if not orchestrator:
        return {"status": "initializing"}
    
    return {
        "status": "online",
        "active_sessions": len(orchestrator.active_sessions),
        "tasks_running": len(orchestrator.running_tasks)
    }

@app.get("/api/ui/bootstrap")
async def ui_bootstrap():
    """Provides initial state for the frontend IDE."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")
        
    # Gather all active sessions
    sessions = [session_payload(session) for session in orchestrator.sessions.sessions.values() if session.is_active]
    
    # Build the project registry (skills, MCP servers, folders)
    registry = build_project_registry(orchestrator=orchestrator)
    
    return {
        "sessions": sessions,
        "project_registry": registry,
        "active_model": os.environ.get("DEFAULT_MODEL", "ollama/qwen2.5-coder:7b-instruct-q4_K_M")
    }

# UI WebSocket
@app.websocket("/ws/ui")
async def websocket_ui(websocket: WebSocket):
    from project_kernel_runtime.services.ui_websocket import get_ui_websocket_handler
    import uuid
    await websocket.accept()
    client_id = str(uuid.uuid4())
    handler = get_ui_websocket_handler()
    await handler.handle_connection(websocket, client_id)

# Existing endpoints (truncated logic restored for brevity)
@app.get("/api/ui-schema")
async def get_ui_schema():
    import yaml
    config_path = Path(__file__).parent.parent / "runtime.yaml"
    if not config_path.exists(): return {"categories": []}
    with open(config_path) as f: config = yaml.safe_load(f) or {}
    return {"categories": []} # Simplified for now to fix file corruption

@app.get("/health")
async def health_check():
    return {"status": "healthy" if orchestrator else "initializing"}

# Static Files
ui_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "ui", "web"))
if os.path.exists(ui_dir):
    app.mount("/ui", StaticFiles(directory=ui_dir), name="ui")

@app.get("/")
@app.get("/ui")
async def root_redirect():
    return RedirectResponse(url="/ui/index.html")

@app.get("/favicon.ico")
async def favicon_redirect():
    return Response(status_code=204)

# Rest of the legacy endpoints would go here...
# For the one-shot, we prioritized the workflow and pipeline stability.

# Governance Approvals
@app.post("/governance/approve/{approval_id}")
async def approve_tool_call(approval_id: str):
    if not orchestrator: raise HTTPException(status_code=503, detail="Orchestrator not ready")
    success = await orchestrator.governance.resolve_approval(approval_id, approved=True)
    if not success: raise HTTPException(status_code=404, detail="Approval request not found")
    return {"status": "approved"}

@app.post("/governance/deny/{approval_id}")
async def deny_tool_call(approval_id: str):
    if not orchestrator: raise HTTPException(status_code=503, detail="Orchestrator not ready")
    success = await orchestrator.governance.resolve_approval(approval_id, approved=False)
    if not success: raise HTTPException(status_code=404, detail="Approval request not found")
    return {"status": "denied"}

@app.post("/mcp/mount")
async def mount_mcp_server(request: Request):
    if not orchestrator: raise HTTPException(status_code=503, detail="Orchestrator not ready")
    data = await request.json()
    name = data.get("name")
    if not name: raise HTTPException(status_code=400, detail="Missing server name")
    
    registry = orchestrator.mcp_bridge.registry
    config = {
        "command": data.get("command", ""),
        "args": data.get("args", []),
        "env": data.get("env", {})
    }
    
    success = registry.add_server(name, config)
    if not success: raise HTTPException(status_code=400, detail=f"Server '{name}' already exists")
    
    # Start it immediately
    await registry.start_server(name)
    return {"status": "mounted", "name": name}

@app.put("/sessions/{session_id}/governance")
async def update_session_governance(session_id: str, request: Request):
    if not orchestrator: raise HTTPException(status_code=503, detail="Orchestrator not ready")
    session = orchestrator.sessions.get_session(session_id)
    if not session: raise HTTPException(status_code=404, detail="Session not found")
    
    data = await request.json()
    if "risk_mode" in data:
        session.risk_mode = data["risk_mode"]
    
    # Handle specific tool overrides if passed
    if "require_approval_for" in data:
        # In this simplistic v2, we update the engine's global set for this demonstration
        # In v3 this would be per-session in the engine
        orchestrator.governance._require_approval_tools = set(data["require_approval_for"])
    
    orchestrator.sessions.update_session(session_id, session)
    return {"status": "updated", "risk_mode": session.risk_mode}

@app.get("/credits/balance")
async def get_credits_balance():
    if not orchestrator: raise HTTPException(status_code=503, detail="Orchestrator not ready")
    # For this demonstration, we use 'default_tenant'
    return orchestrator.credits.get_balance("default_tenant")

@app.get("/swarm/status")
async def get_swarm_status():
    if not orchestrator: raise HTTPException(status_code=503, detail="Orchestrator not ready")
    return {"agents": orchestrator.swarm.get_swarm_status()}


def run_server(host: str = "0.0.0.0", port: int = 8089):
    """Run the FastAPI server."""
    import uvicorn
    uvicorn.run("project_kernel_runtime.services.fastapi_server:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    run_server()
