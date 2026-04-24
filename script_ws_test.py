import asyncio
import logging
logging.basicConfig(level=logging.DEBUG)
from src.infrastructure.db.session import AsyncSessionLocal
from src.services.agent_loop.brain import BrainWorker

async def test():
    async with AsyncSessionLocal() as db:
        b = BrainWorker()
        await b.process_task_event({
            'task_id': 'task_9e0402316a58',
            'session_id': 'add2062f-0542-4d4a-9497-cb5731491545'
        }, db)

asyncio.run(test())
