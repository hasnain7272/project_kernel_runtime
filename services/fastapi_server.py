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

# 2. UI WebSocket for Dynamic Control Panel
@app.websocket("/ws/ui")
async def websocket_ui(websocket: WebSocket):
    """WebSocket endpoint for real-time UI control panel."""
    from project_kernel_runtime.services.ui_websocket import get_ui_websocket_handler
    import uuid
    await websocket.accept()
    client_id = str(uuid.uuid4())
    handler = get_ui_websocket_handler()
    await handler.handle_connection(websocket, client_id)

# 3. API endpoint to get UI schema (standalone, no kernel deps)
@app.get("/api/ui-schema")
async def get_ui_schema():
    """Get UI schema for dynamic control panel."""
    import yaml
    from pathlib import Path
    
    config_path = Path(__file__).parent.parent / "runtime.yaml"
    if not config_path.exists():
        return {"error": "runtime.yaml not found", "categories": [], "total_parameters": 0}
    
    with open(config_path) as f:
        config = yaml.safe_load(f) or {}
    
    # Flatten nested config to parameters
    params = []
    categories_set = set()
    
    def flatten(d, prefix=""):
        for k, v in d.items():
            param_id = f"{prefix}{k}" if prefix else k
            if isinstance(v, dict):
                flatten(v, f"{param_id}.")
            elif v is not None:
                param_type = "boolean" if isinstance(v, bool) else "slider" if isinstance(v, (int, float)) else "text"
                categories_set.add(prefix.rstrip(".").split(".")[0] if prefix else "general")
                params.append({
                    "id": param_id,
                    "type": param_type,
                    "label": k.replace("_", " ").title(),
                    "description": f"Configuration: {param_id}",
                    "category": prefix.rstrip(".").split(".")[0] if prefix else "general",
                    "default": v,
                    "value": v
                })
    
    flatten(config)
    
    # Build categories
    category_info = {
        "llm": {"label": "LLM & Models", "icon": "brain"},
        "sandbox": {"label": "Sandbox & Execution", "icon": "box"},
        "governance": {"label": "Governance & Security", "icon": "shield"},
        "mcp": {"label": "MCP Protocol", "icon": "link"},
        "a2a": {"label": "A2A Mesh", "icon": "share"},
        "observability": {"label": "Observability", "icon": "activity"},
        "server": {"label": "Server", "icon": "server"},
        "features": {"label": "Feature Flags", "icon": "toggle"},
        "vector_db": {"label": "Memory & RAG", "icon": "database"},
    }
    
    categories = []
    for cat_id in categories_set:
        cat_params = [p for p in params if p["category"] == cat_id]
        info = category_info.get(cat_id, {"label": cat_id.title(), "icon": "settings"})
        categories.append({
            "id": cat_id,
            "label": info["label"],
            "description": f"{info['label']} settings",
            "icon": info["icon"],
            "order": len(categories),
            "parameters": cat_params
        })
    
    return {
        "version": "1.0.0",
        "generated_at": "2026-01-01T00:00:00Z",
        "categories": categories,
        "total_parameters": len(params)
    }

# 4. API endpoint to get/set parameters (standalone)
@app.get("/api/params")
async def get_all_params():
    """Get all parameters."""
    import yaml
    from pathlib import Path
    
    config_path = Path(__file__).parent.parent / "runtime.yaml"
    if not config_path.exists():
        return {}
    
    with open(config_path) as f:
        config = yaml.safe_load(f) or {}
    
    def flatten(d, prefix=""):
        result = {}
        for k, v in d.items():
            param_id = f"{prefix}{k}" if prefix else k
            if isinstance(v, dict):
                result.update(flatten(v, f"{param_id}."))
            else:
                result[param_id] = v
        return result
    
    return flatten(config)

@app.get("/api/params/{param_id}")
async def get_param(param_id: str):
    """Get a single parameter."""
    import yaml
    from pathlib import Path
    
    config_path = Path(__file__).parent.parent / "runtime.yaml"
    if not config_path.exists():
        raise HTTPException(status_code=404, detail="Config not found")
    
    with open(config_path) as f:
        config = yaml.safe_load(f) or {}
    
    parts = param_id.split(".")
    value = config
    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            raise HTTPException(status_code=404, detail="Parameter not found")
    
    return {"param_id": param_id, "value": value}

@app.put("/api/params/{param_id}")
async def set_param(param_id: str, value: Any):
    """Set a parameter value."""
    import yaml
    from pathlib import Path
    
    config_path = Path(__file__).parent.parent / "runtime.yaml"
    if not config_path.exists():
        raise HTTPException(status_code=500, detail="Config not found")
    
    with open(config_path) as f:
        config = yaml.safe_load(f) or {}
    
    parts = param_id.split(".")
    target = config
    for part in parts[:-1]:
        if part not in target:
            target[part] = {}
        target = target[part]
    target[parts[-1]] = value
    
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    
    return {"success": True, "param_id": param_id, "value": value}

# 2. Static Dashboard
ui_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "ui", "web"))
if os.path.exists(ui_dir):
    app.mount("/ui", StaticFiles(directory=ui_dir), name="ui")
    print(f"UI Static Hub: {os.path.join(ui_dir, 'spatial_ui.html')} is READY")
else:
    print(f"ERROR: UI dir missing at {ui_dir}")

@app.get("/")
@app.get("/ui")
@app.get("/ui/")
async def root_redirect():
    return RedirectResponse(url="/ui/index.html")

@app.get("/ui/index.html")
async def serve_index():
    """Serve the main Mission Control UI."""
    from fastapi.responses import FileResponse
    ui_index = os.path.join(ui_dir, "index.html")
    return FileResponse(ui_index)

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