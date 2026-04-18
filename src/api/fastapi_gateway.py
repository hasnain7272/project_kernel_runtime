"""
Kernel API gateway.
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi import HTTPException, status

from src.api.rest.routers import chat, sessions, tasks, workspace
from src.infrastructure.db.session import AsyncSessionLocal, init_db
from src.infrastructure.runtime.config import APP_VERSION, ALLOW_ANON_LOCAL
from src.services.agent_loop.brain import BrainWorker
from src.services.agent_loop.tool_worker import ToolWorker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gateway")

_rate_limit_storage = {}
_rate_limit_config = {
    "requests_per_minute": 60,
    "requests_per_hour": 500,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB (Alembic should replace this eventually)
    await init_db()
    
    # Initialize Otel tracing
    from src.infrastructure.observability.tracing import instrument_fastapi
    instrument_fastapi(app)
    
    # Hybrid Mode: Launch the worker as a background task in the same process
    # for easy local development, while maintaining the distributed stream architecture.
    hybrid_mode = os.environ.get("HYBRID_MODE", "true").lower() == "true"
    worker_task = None
    
    if hybrid_mode:
        from src.services.agent_loop.worker_main import start_worker
        logger.info("🚀 Gateway starting in HYBRID MODE (API + Worker)")
        worker_task = asyncio.create_task(start_worker(init_database=False))
    else:
        logger.info("📡 Gateway starting in STATELESS MODE (API only)")
    
    yield
    
    if worker_task:
        logger.info("Shutting down background worker...")
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
            
    logger.info("Gateway shutting down.")


app = FastAPI(
    title="Antigravity Runtime",
    version=APP_VERSION,
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
    return {"status": "ok", "version": APP_VERSION}


STATIC_DIR = os.path.join(os.path.dirname(__file__), "../..", "ui", "vite-app", "dist")
if os.path.exists(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

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
