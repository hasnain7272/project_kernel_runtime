# integrations Architecture Documentation

*Generated on: 2026-03-28T15:12:48.055187*

---

#### __init__.py *(1 lines)*

---

#### a2a_handshake.py *(44 lines)*

> **Imports**: `import json`, `import asyncio`, `from typing import Dict`, `from typing import Any`, `from typing import List`, `from typing import Optional`, `from a2a_protocol import A2AHandler`, `from a2a_protocol import A2AMessage`, `from a2a_protocol import A2AMessageType`, `from a2a_protocol import AgentCard`

> **Classes**:
  - **A2AHandshakeManager** – *Manages the broadcast and reception of A2A handshakes.* (lines 12-44)
    - `__init__(self, handler)` (lines 15-18)
    - `stop(self)` (lines 37-38)

---

#### a2a_protocol.py *(349 lines)*

> **Imports**: `import json`, `import logging`, `from enum import Enum`, `from datetime import datetime`, `from datetime import timezone`, `from typing import Any`, `from typing import Dict`, `from typing import List`, `from typing import Optional`, `from uuid import uuid4`

> **Constants**: `logger`=logging.getLogger(__name__)

> **Classes**:
  - **A2ATaskState** – *A2A v0.3 task lifecycle states.* (lines 29-36)
  - **AgentSkill** – *Capability advertised by an agent.* (lines 39-54)
    - `__init__(self, id, name, description, tags, examples)` (lines 41-47)
    - `to_dict(self)` (lines 49-54)
  - **AgentCapabilities** – *What the agent supports.* (lines 57-70)
    - `__init__(self, streaming, push_notifications, state_transition_history)` (lines 59-63)
    - `to_dict(self)` (lines 65-70)
  - **AgentCard** – *A2A v0.3 Agent Card — identity and capability descriptor.* (lines 73-107)
    - `__init__(self, id, name, description, url, version, capabilities, skills, default_input_modes, default_output_modes)` (lines 75-95)
    - `to_dict(self)` (lines 97-107)
  - **A2APart** – *Content part in an A2A message.* (lines 110-129)
    - `__init__(self, type, text, mime_type, data, metadata)` (lines 112-118)
    - `to_dict(self)` (lines 120-129)
  - **A2AMessage** – *A2A v0.3 message with typed parts.* (lines 132-145)
    - `__init__(self, role, parts, metadata)` (lines 134-138)
    - `to_dict(self)` (lines 140-145)
  - **A2AArtifact** – *An artifact produced by a task.* (lines 148-162)
    - `__init__(self, id, name, parts, metadata)` (lines 150-155)
    - `to_dict(self)` (lines 157-162)
  - **A2ATask** – *A2A v0.3 task with full lifecycle.* (lines 165-197)
    - `__init__(self, id, session_id)` (lines 167-176)
    - `transition(self, new_state)` – *Transition task state with history tracking.* (lines 178-186)
    - `to_dict(self)` (lines 188-197)
  - **A2AHandler** – *Google A2A v0.3 protocol handler.

Supports:
- Agent Card discovery (.well-known/agent.json)
- Task lifecycle (send, get, cancel)
- Message streaming via SSE
- Peer registry* (lines 204-332)
    - `__init__(self, owner_card)` (lines 215-219)
    - `get_agent_card(self)` – *Return agent card for /.well-known/agent.json.* (lines 223-225)
    - `register_peer(self, card)` (lines 294-296)
    - `handle_incoming(self, raw_message)` – *Legacy incoming message handler (backward compat).* (lines 298-318)
    - `list_peers(self)` (lines 320-321)
    - `create_handshake(self)` – *Generate handshake message.* (lines 323-332)
  - **GA2AMeshV2** – *Merged from a2a_protocol_v2 — mesh networking for A2A.* (lines 339-349)
    - `__init__(self, owner_card)` (lines 342-343)
    - `handle_message(self, raw)` (lines 348-349)

---

#### a2a_protocol_v2.py *(22 lines)*

> **Imports**: `from a2a_protocol import AgentCard`, `from a2a_protocol import A2AHandler`, `from a2a_protocol import A2ATask`, `from a2a_protocol import A2ATaskState`, `from a2a_protocol import A2AMessage`, `from a2a_protocol import A2APart`, `from a2a_protocol import A2AArtifact`, `from a2a_protocol import GA2AMeshV2`

> **Constants**: `__all__`=['AgentCard', 'A2AHandler', 'A2ATask', 'A2ATaskState', 'A2AMessage', 'A2APart', 'A2AArtifact', 'GA2AMeshV2']

---

#### browser_mcp.py *(41 lines)*

> **Imports**: `from mcp.server.fastmcp import FastMCP`, `import asyncio`, `import httpx`, `from typing import Dict`, `from typing import Any`

> **Constants**: `mcp`=FastMCP('ChromeMCP')

---

#### universal_mcp.py *(155 lines)*

> **Imports**: `import asyncio`, `import httpx`, `import os`, `import yaml`, `from typing import Dict`, `from typing import Any`, `from typing import List`, `from typing import Optional`, `from project_kernel_runtime.memory.state_hub import state_hub`

> **Constants**: `mcp_bridge`=UniversalMCP()

> **Classes**:
  - **UniversalMCP** (lines 8-152)
    - `__init__(self, registry_path)` (lines 9-14)
    - `_load_registry(self)` – *Load discovered MCPs from persistent storage.* (lines 16-21)
    - `_save_registry(self)` – *Save discovered MCPs to persistent storage.* (lines 23-26)
    - `_rebuild_tool_map(self)` – *Rebuild tool_map from discovered_servers.* (lines 28-32)

---

