import asyncio
import logging
import os
import sys

# Ensure project root is in path for all execution modes
root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if root not in sys.path:
    sys.path.insert(0, root)

from src.infrastructure.db.session import AsyncSessionLocal, init_db
from src.infrastructure.queue.redis_streams_broker import get_streams_broker
from src.services.agent_loop.brain import BrainWorker
from src.services.agent_loop.tool_worker import ToolWorker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker")


async def _run_task_worker(brain: BrainWorker):
    broker = await get_streams_broker()

    async def handle(message):
        async with AsyncSessionLocal() as db:
            await brain.process_task_event(message.data, db)

    # Use a consumer group named "brain-workers"
    await broker.subscribe("task_queue", "brain-workers", handle)


async def _run_tool_worker(tool_worker: ToolWorker):
    broker = await get_streams_broker()

    async def handle(message):
        async with AsyncSessionLocal() as db:
            await tool_worker.process_tool_event(message.data, db)

    # Use a consumer group named "tool-workers"
    await broker.subscribe("execution_queue", "tool-workers", handle)


async def start_worker(init_database: bool = True):
    """Entrypoint for both standalone and hybrid modes."""
    if init_database:
        await init_db()
    
    # Initialize Tracing if not already done
    from src.infrastructure.observability.tracing import instrument_sqlalchemy
    from src.infrastructure.db.session import engine
    try:
        instrument_sqlalchemy(engine)
    except Exception:
        pass # Already instrumented
    
    brain = BrainWorker()
    tool_worker = ToolWorker()

    logger.info("Worker runtime started (Process: %s)", os.getpid())
    await asyncio.gather(
        _run_task_worker(brain),
        _run_tool_worker(tool_worker),
    )


if __name__ == "__main__":
    asyncio.run(start_worker())
