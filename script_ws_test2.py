import asyncio
import websockets

async def test():
    try:
        async with websockets.connect('ws://127.0.0.1:8089/api/v1/tasks/task_9e0402316a58/stream?tenant_id=usr_15tx89ous') as ws:
            print("Works!")
            await ws.close()
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test())
