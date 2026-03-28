"""
FastAPI Server: HTTP/WebSocket API

Inspired by OpenHands REST API + Cursor web interface
"""

from fastapi import FastAPI, WebSocket, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
from contextlib import asynccontextmanager
import sys
import os

# Add src to path so project_kernel_runtime is found even if run directly
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Set Ollama base URL early (before LLM provider init reads it)
if "OLLAMA_API_BASE" not in os.environ:
    os.environ["OLLAMA_API_BASE"] = "http://127.0.0.1:11500"

# --- Core Dependencies ---
from project_kernel_runtime.kernel.task_state_machine import TaskStatus
from project_kernel_runtime.services.research_api import router as research_router
from project_kernel_runtime.memory.state_hub import state_hub

# Global orchestrator instance
orchestrator = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler for the FastAPI app."""
    from project_kernel_runtime.kernel.orchestrator import init_orchestrator
    global orchestrator
    orchestrator = await init_orchestrator()
    yield
    # Shutdown logic
    if orchestrator:
        await orchestrator.shutdown()

app = FastAPI(
    title="Project Kernel Runtime API",
    description="Enterprise API Gateway to the Coding Agent Swarm",
    version="2.0.0",
    lifespan=lifespan
)

# --- Middleware & CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routes & Static Hub ---
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
import os

# 1. API Hubs
app.include_router(research_router, prefix="/research")
from project_kernel_runtime.services.router_agent import router as agent_router
from project_kernel_runtime.services.router_mcp import router as mcp_router
app.include_router(agent_router)
app.include_router(mcp_router)

# 2. Static Dashboard
ui_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "ui", "web"))
if os.path.exists(ui_dir):
    app.mount("/ui", StaticFiles(directory=ui_dir), name="ui")
    print(f"UI Static Hub: {os.path.join(ui_dir, 'spatial_ui.html')} is READY")
else:
    print(f"ERROR: UI dir missing at {ui_dir}")

@app.get("/")

@app.get("/ui")

async def root_redirect():

    return RedirectResponse(url="/ui/spatial_ui.html")

# WebSocket connections

active_connections: Dict[str, WebSocket] = {}

@app.get("/health")

async def health_check():

    """Health check endpoint"""

    if not orchestrator:

        return {

            "status": "initializing",

            "timestamp": datetime.now().isoformat()

        }

    status = await orchestrator.get_system_status()

    return {

        "status": "healthy",

        "timestamp": datetime.now().isoformat(),

        "system": status

    }

@app.websocket("/ws/{user_id}")

async def websocket_endpoint(websocket: WebSocket, user_id: str):

    """WebSocket endpoint for real-time communication"""

    await websocket.accept()

    active_connections[user_id] = websocket

    try:

        while True:

            data = await websocket.receive_text()

            try:

                message = json.loads(data)

                response = await handle_websocket_message(user_id, message)

                await websocket.send_json(response)

            except json.JSONDecodeError:

                await websocket.send_json({

                    "error": "Invalid JSON",

                    "timestamp": datetime.now().isoformat()

                })

            except Exception as e:

                await websocket.send_json({

                    "error": str(e),

                    "timestamp": datetime.now().isoformat()

                })

    except Exception:

        pass

    finally:

        active_connections.pop(user_id, None)

async def handle_websocket_message(user_id: str, message: Dict[str, Any]) -> Dict[str, Any]:

    """Handle WebSocket message"""

    if not orchestrator:

        return {

            "action": "error",

            "message": "Service not initialized",

            "status": "error"

        }

    action = message.get("action")

    if action == "create_task":

        from project_kernel_runtime.kernel.task_state_machine import TaskType

        task_type = message.get("task_type")

        description = message.get("description")

        steps = message.get("steps", [])

        try:

            task_type_enum = TaskType(task_type)

            task = await orchestrator.create_task(

                user_id, task_type_enum, description, steps

            )

            return {

                "action": "task_created",

                "task_id": task.id,

                "status": "success"

            }

        except Exception as e:

            return {

                "action": "error",

                "message": str(e),

                "status": "error"

            }

    elif action == "execute_task":

        task_id = message.get("task_id")

        try:

            success = await orchestrator.execute_task(user_id, task_id)

            return {

                "action": "task_started",

                "task_id": task_id,

                "status": "success"

            }

        except Exception as e:

            return {

                "action": "error",

                "message": str(e),

                "status": "error"

            }

    elif action == "get_task_status":

        task_id = message.get("task_id")

        try:

            task = await orchestrator.get_task_status(user_id, task_id)

            if task:

                return {

                    "action": "task_status",

                    "task": {

                        "id": task.id,

                        "status": task.status.value,

                        "current_step": task.get_current_step().id if task.get_current_step() else None

                    },

                    "status": "success"

                }

            else:

                return {

                    "action": "error",

                    "message": "Task not found",

                    "status": "error"

                }

        except Exception as e:

            return {

                "action": "error",

                "message": str(e),

                "status": "error"

            }

    else:

        return {

            "action": "error",

            "message": f"Unknown action: {action}",

            "status": "error"

        }

# ============================================================================

# MCP 2026 Streamable HTTP Transport

# ============================================================================

@app.get("/metrics")

async def prometheus_metrics():

    """Prometheus-compatible metrics endpoint."""

    from project_kernel_runtime.kernel.observability import metrics

    from fastapi.responses import PlainTextResponse

    return PlainTextResponse(metrics.export_prometheus(), media_type="text/plain")

@app.get("/status/full")

async def full_system_status():

    """Comprehensive system status including all subsystems."""

    if not orchestrator:

        return {"status": "initializing"}

    

    status = await orchestrator.get_system_status()

    status["sre"] = orchestrator.sre.get_status()

    status["watchdog"] = orchestrator.watchdog.get_status()

    status["mesh"] = orchestrator.mesh_p2p.get_mesh_status()

    

    # Federated Hub UI requirements

    status["federated"] = {

        "status": "Active (Hub V2)",

        "patterns_shared": len(orchestrator.federated.shared_patterns) if hasattr(orchestrator, 'federated') else 0

    }

    return status

@app.exception_handler(Exception)

async def global_exception_handler(request, exc):

    """Global exception handler"""

    return JSONResponse(

        status_code=500,

        content={

            "error": "Internal server error",

            "detail": str(exc),

            "timestamp": datetime.now().isoformat()

        }

    )

def run_server(host: str = "0.0.0.0", port: int = 8089):

    """Run the FastAPI server"""

    uvicorn.run(

        "project_kernel_runtime.services.fastapi_server:app",

        host=host,

        port=port,

        reload=True

    )

if __name__ == "__main__":

    run_server()