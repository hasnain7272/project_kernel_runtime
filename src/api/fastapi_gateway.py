"""
Kernel API Gateway — Stateless Control Plane Entrypoint

Bootstraps the DB, mounts routers, and in local mode
registers both BrainWorker and ToolWorker as asyncio subscribers.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.infrastructure.db.session import init_db, AsyncSessionLocal
from src.infrastructure.queue.redis_broker import get_broker
from src.services.agent_loop.brain import BrainWorker
from src.services.agent_loop.tool_worker import ToolWorker
from src.api.rest.routers import tasks, sessions, chat, workspace

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gateway")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    broker = get_broker()
    brain = BrainWorker()
    tool_worker = ToolWorker()

    if hasattr(broker, "subscribe_sync"):
        # Local venv mode — both workers run as async callbacks

        async def on_task_event(event):
            async with AsyncSessionLocal() as db:
                await brain.process_task_event(event, db)

        async def on_tool_event(event):
            async with AsyncSessionLocal() as db:
                await tool_worker.process_tool_event(event, db)

        broker.subscribe_sync("task_queue", on_task_event)
        broker.subscribe_sync("execution_queue", on_tool_event)
        logger.info("Local worker topology: brain + tool_worker ✓")

    yield
    logger.info("Gateway shutting down.")


app = FastAPI(
    title="Antigravity Runtime",
    version="3.0.0",
    docs_url="/api/docs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks.router)
app.include_router(sessions.router)
app.include_router(chat.router)
app.include_router(workspace.router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "3.0.0"}

# --- Static File Serving (Unity Deployment) ---
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import Request

STATIC_DIR = os.path.join(os.path.dirname(__file__), "../..", "ui", "vite-app", "dist")

if os.path.exists(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    # Catch-all for SPA routing (must be last!)
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        if full_path.startswith("api/"):
            return {"detail": "Not Found"}
        index_path = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"detail": "Dashboard not built. Run npm run build in ui/vite-app"}
else:
    logger.warning("Vite dist folder not found. Frontend will not be hosted.")
