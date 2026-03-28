# services Architecture Documentation

*Generated on: 2026-03-28T15:12:48.132183*

---

#### __init__.py *(1 lines)*

---

#### fastapi_server.py *(468 lines)*

> **Imports**: `from fastapi import FastAPI`, `from fastapi import WebSocket`, `from fastapi import HTTPException`, `from fastapi import Depends`, `from fastapi.middleware.cors import CORSMiddleware`, `from fastapi.responses import JSONResponse`, `import uvicorn`, `import json`, `from typing import List`, `from typing import Dict`, `from typing import Any`, `from typing import Optional`, `from datetime import datetime`, `import asyncio`, `from contextlib import asynccontextmanager`, `import sys`, `import os`, `from project_kernel_runtime.kernel.task_state_machine import TaskStatus`, `from project_kernel_runtime.services.research_api import router`, `from project_kernel_runtime.memory.state_hub import state_hub`, `from fastapi.responses import RedirectResponse`, `from fastapi.staticfiles import StaticFiles`, `import os`, `from project_kernel_runtime.services.router_agent import router`, `from project_kernel_runtime.services.router_mcp import router`, `from project_kernel_runtime.kernel.orchestrator import init_orchestrator`, `from project_kernel_runtime.services.ui_websocket import get_ui_websocket_handler`, `import uuid`, `from project_kernel_runtime.kernel.parameter_registry import get_registry`, `from project_kernel_runtime.kernel.parameter_registry import get_registry`, `from project_kernel_runtime.kernel.parameter_registry import get_registry`, `from project_kernel_runtime.kernel.parameter_registry import get_registry`, `from project_kernel_runtime.kernel.observability import metrics`, `from fastapi.responses import PlainTextResponse`, `from project_kernel_runtime.kernel.task_state_machine import TaskType`

> **Constants**: `src_path`=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')), `orchestrator`=None, `app`=FastAPI(title='Project Kernel Runtime API', description='Enterprise API Gateway to the Coding Agent Swarm', version='2.0.0', lifespan=lifespan), `ui_dir`=os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'ui', 'web'))

> **Functions**:
  - `run_server(host, port)` – *Run the FastAPI server* (lines 450-464)

---

#### research_api.py *(164 lines)*

> **Imports**: `from fastapi import APIRouter`, `from fastapi import HTTPException`, `from typing import Dict`, `from typing import Any`, `from project_kernel_runtime.kernel.orchestrator import Orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`

> **Constants**: `router`=APIRouter()

---

#### router_agent.py *(1014 lines)*

> **Imports**: `from fastapi import APIRouter`, `from fastapi import HTTPException`, `from fastapi import Depends`, `from typing import Dict`, `from typing import Any`, `from typing import Optional`, `from datetime import datetime`, `from project_kernel_runtime.memory.state_hub import state_hub`, `from fastapi.responses import StreamingResponse`, `import asyncio`, `import json`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `import os`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.kernel.task_state_machine import TaskType`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.kernel.task_state_machine import TaskStatus`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.agents.vision_swarm import vision_swarm`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.agents.vision_swarm import vision_swarm`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.kernel.credits_engine import credits_engine`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.agents.vision_swarm import vision_swarm`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.agents.vision_swarm import vision_swarm`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.kernel.credits_engine import credits_engine`, `import json`, `import os`, `import json`, `import os`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.agents.vision_swarm import vision_swarm`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.agents.vision_swarm import vision_swarm`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.kernel.credits_engine import credits_engine`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.integrations.a2a_protocol import A2AHandler`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from datetime import datetime`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `import logging`, `from project_kernel_runtime.kernel.task_state_machine import TaskStatus`

> **Constants**: `router`=APIRouter()

---

#### router_mcp.py *(64 lines)*

> **Imports**: `from fastapi import APIRouter`, `from fastapi import HTTPException`, `from fastapi import Request`, `from typing import Dict`, `from typing import Any`, `import json`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.protocols.mcp_server import MCPServer`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from fastapi.responses import StreamingResponse`, `from project_kernel_runtime.services.fastapi_server import orchestrator`, `from project_kernel_runtime.integrations.a2a_protocol import A2AHandler`, `from project_kernel_runtime.services.fastapi_server import orchestrator`

> **Constants**: `router`=APIRouter()

---

#### ui_websocket.py *(410 lines)*

> **Imports**: `import asyncio`, `import json`, `import logging`, `import uuid`, `from datetime import datetime`, `from datetime import timezone`, `from typing import Any`, `from typing import Callable`, `from typing import Dict`, `from typing import List`, `from typing import Optional`, `from typing import Set`, `from dataclasses import dataclass`, `from dataclasses import field`, `from enum import Enum`, `from fastapi import APIRouter`, `from fastapi import WebSocket`, `from fastapi import WebSocketDisconnect`, `from fastapi import Query`, `from starlette.websockets import WebSocketState`, `import uvicorn`, `from fastapi import FastAPI`, `from kernel.parameter_registry import get_registry`, `from kernel.parameter_registry import get_registry`, `from kernel.parameter_registry import get_registry`, `from kernel.parameter_registry import get_registry`, `from kernel.parameter_registry import get_registry`, `from kernel.parameter_registry import get_registry`, `from kernel.parameter_registry import get_registry`, `from kernel.parameter_registry import get_registry`, `from kernel.parameter_registry import get_registry`

> **Constants**: `logger`=logging.getLogger(__name__)

> **Classes**:
  - **MessageType** – *Message types for UI-Backend communication.* (lines 28-35)
  - **UIWebSocketMessage** – *A message in the UI-WebSocket protocol.* (lines 39-47)
  - **WebSocketClient** – *Connected UI client.* (lines 51-58)
  - **UIEventBroadcaster** – *Broadcasts events to connected UI clients.* (lines 61-136)
    - `__init__(self, max_buffer_size)` (lines 64-68)
    - `_buffer_event(self, event)` – *Buffer event for late-connecting clients.* (lines 112-116)
    - `get_client_count(self)` – *Get number of connected clients.* (lines 122-124)
    - `get_clients(self)` – *Get list of connected clients.* (lines 126-136)
  - **UIWebSocketHandler** – *Handles UI WebSocket connections and command processing.

Supported commands:
- GET_SCHEMA: Get UI schema for dynamic rendering
- GET_PARAM: Get single parameter value
- GET_ALL_PARAMS: Get all parameters
- SET_PARAM: Set parameter value
- SUBSCRIBE: Subscribe to event types
- UNSUBSCRIBE: Unsubscribe from event types
- GET_STATUS: Get system status
- GET_HISTORY: Get parameter change history
- SEARCH_PARAMS: Search parameters* (lines 139-361)
    - `__init__(self)` (lines 155-159)
    - `_register_handlers(self)` – *Register command handlers.* (lines 161-177)

> **Functions**:
  - `get_ui_websocket_handler()` – *Get global UI WebSocket handler.* (lines 367-372)
  - `create_ui_websocket_router()` – *Create router with WebSocket endpoint.* (lines 396-400)

---

