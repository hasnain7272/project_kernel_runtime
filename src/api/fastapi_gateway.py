"""Kernel API gateway — Ultra-premium production gateway."""
import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.rest.config.cors import setup_cors
from src.api.rest.routes import include_routers
from src.infrastructure.db.session import init_db
from src.infrastructure.runtime.config import APP_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gateway")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    await init_db()

    # Initialize tracing
    from src.infrastructure.observability.tracing import instrument_fastapi
    instrument_fastapi(app)

    # Hybrid mode: Start worker in same process
    hybrid_mode = os.environ.get("HYBRID_MODE", "true").lower() == "true"
    worker_task = None

    if hybrid_mode:
        from src.services.agent_loop.worker_main import start_worker
        logger.info("🚀 Gateway in HYBRID MODE")
        worker_task = asyncio.create_task(start_worker(init_database=False))
    else:
        logger.info("📡 Gateway in STATELESS MODE")

    yield

    if worker_task:
        logger.info("Shutting down worker...")
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

    logger.info("Gateway shutdown.")


# Create FastAPI app
is_prod = os.environ.get("ENVIRONMENT") == "production"
app = FastAPI(
    title="Project Kernel Runtime",
    version=APP_VERSION,
    docs_url=None if is_prod else "/api/docs",
    redoc_url=None if is_prod else "/api/redoc",
    lifespan=lifespan,
)

# Setup CORS and routes
setup_cors(app)
include_routers(app)


from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler to ensure JSON response."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal Server Error",
            "detail": str(exc) if not is_prod else "Contact support"
        }
    )


@app.get("/health")
async def health():
    """Health check endpoint."""
    from src.infrastructure.queue.redis_streams_broker import get_streams_broker
    broker = await get_streams_broker()
    return {
        "status": "ok",
        "version": APP_VERSION,
        "broker": type(broker).__name__,
    }


@app.get("/api/v1/health/workers")
async def workers_health():
    """Worker health status."""
    from src.infrastructure.queue.redis_streams_broker import get_streams_broker
    broker = await get_streams_broker()
    return {
        "broker_type": type(broker).__name__,
        "stream_count": len(getattr(broker, "_streams", {})),
    }


@app.get("/api/v1/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    from src.infrastructure.observability.metrics import metrics
    return {"metrics": metrics.get_metrics()}


# Static files (SPA)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "../..", "ui", "vite-app", "dist")
if os.path.exists(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")


@app.get("/{full_path:path}")
async def serve_spa(request: Request, full_path: str):
    """Serve SPA frontend."""
    if full_path.startswith("api/"):
        return {"detail": "Not Found"}

    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"detail": "Dashboard not built"}
