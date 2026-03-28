# protocols Architecture Documentation

*Generated on: 2026-03-28T15:12:48.125582*

---

#### federated_hub.py *(79 lines)*

> **Imports**: `import logging`, `import time`, `from typing import Any`, `from typing import Dict`, `from typing import List`

> **Constants**: `logger`=logging.getLogger(__name__)

> **Classes**:
  - **FederatedHub** – *Federated knowledge sharing hub between agent instances.* (lines 17-79)
    - `__init__(self)` (lines 20-24)
    - `share_pattern(self, pattern_type, data, anonymize)` – *Share a task pattern with the federation.* (lines 34-44)
    - `query_patterns(self, pattern_type, limit)` – *Query shared patterns.* (lines 46-52)
    - `sync_metrics(self, peer_id, metrics)` – *Receive metrics from a peer for aggregation.* (lines 54-60)
    - `get_aggregated_metrics(self)` – *Get aggregated metrics across peers.* (lines 62-73)
    - `_anonymize(data)` – *Remove PII from shared data.* (lines 76-79)

---

#### mcp_client.py *(282 lines)*

> **Imports**: `import asyncio`, `import json`, `from typing import Dict`, `from typing import List`, `from typing import Optional`, `from typing import Any`, `from typing import Callable`, `from dataclasses import dataclass`, `import websockets`, `from websockets.exceptions import ConnectionClosedError`

> **Classes**:
  - **MCPTool** – *MCP Tool definition* (lines 15-19)
  - **MCPResource** – *MCP Resource definition* (lines 22-27)
  - **MCPPrompt** – *MCP Prompt definition* (lines 30-34)
  - **MCPClient** – *Client for MCP server communication* (lines 36-281)
    - `__init__(self, server_url)` (lines 39-46)
    - `_next_id(self)` – *Get next message ID* (lines 225-228)

---

#### mcp_server.py *(464 lines)*

> **Imports**: `import asyncio`, `import json`, `import logging`, `import uuid`, `from dataclasses import dataclass`, `from dataclasses import field`, `from datetime import datetime`, `from datetime import timezone`, `from typing import Any`, `from typing import Callable`, `from typing import Dict`, `from typing import List`, `from typing import Optional`, `from universal_tools import get_all_tools`, `import websockets`

> **Constants**: `logger`=logging.getLogger(__name__), `SUPPORTED_PROTOCOL_VERSIONS`=['2024-11-05', '2025-03-26'], `LATEST_PROTOCOL_VERSION`='2025-03-26'

> **Classes**:
  - **MCPTool** – *MCP Tool definition.* (lines 34-39)
  - **MCPResource** – *MCP Resource definition.* (lines 43-49)
  - **MCPPrompt** – *MCP Prompt definition.* (lines 53-58)
  - **MCPSession** – *MCP session for Streamable HTTP.* (lines 62-70)
  - **MCPServer** – *MCP Server with dual transport: Streamable HTTP + WebSocket.

MCP 2026 Spec features:
- POST: JSON-RPC request → direct JSON or SSE stream response
- GET: SSE stream for server-initiated notifications
- Mcp-Session-Id header for session management
- Last-Event-ID for resumability
- Protocol version negotiation* (lines 77-464)
    - `__init__(self, host, port)` (lines 89-107)
    - `_setup_handlers(self)` – *Setup JSON-RPC method handlers.* (lines 109-122)
    - `register_tool(self, tool)` – *Register a tool with the server.* (lines 126-130)
    - `register_resource(self, resource)` (lines 132-133)
    - `register_prompt(self, prompt)` (lines 135-136)
    - `register_tools_from_executor(self, tool_executor)` – *Auto-register tools from the ToolExecutor's tool registry.* (lines 138-150)
    - `_error_response(msg_id, code, message)` (lines 459-464)

---

#### mesh_p2p.py *(112 lines)*

> **Imports**: `import logging`, `import time`, `from typing import Any`, `from typing import Dict`, `from typing import List`, `from typing import Optional`, `from uuid import uuid4`

> **Constants**: `logger`=logging.getLogger(__name__)

> **Classes**:
  - **PeerInfo** – *Information about a peer in the mesh.* (lines 18-37)
    - `__init__(self, peer_id, address, port, capabilities, metadata)` (lines 20-30)
    - `to_dict(self)` (lines 32-37)
  - **GlobalMeshP2P** – *Peer-to-peer mesh network for agent discovery and coordination.* (lines 40-112)
    - `__init__(self, heartbeat_timeout)` (lines 43-47)
    - `register_self(self, address, port, capabilities)` – *Register this node in the mesh.* (lines 49-54)
    - `register_peer(self, peer_id, address, port, capabilities)` (lines 56-61)
    - `heartbeat(self, peer_id)` – *Record heartbeat from peer.* (lines 63-71)
    - `health_check(self)` – *Check health of all peers, mark stale ones.* (lines 73-81)
    - `discover_peers(self, capability)` – *Find peers, optionally filtered by capability.* (lines 83-88)
    - `remove_stale_peers(self)` – *Remove peers that haven't sent heartbeats.* (lines 90-96)
    - `federated_sync(self, metrics)` – *Sync metrics with mesh (called by orchestrator).* (lines 98-104)
    - `get_mesh_status(self)` (lines 106-112)

---

