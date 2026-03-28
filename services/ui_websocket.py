"""
UI WebSocket Server — Real-time UI-Backend Communication

Provides bidirectional WebSocket communication for dynamic UI:
- Commands: GET_SCHEMA, GET_PARAM, SET_PARAM, SUBSCRIBE_EVENT
- Events: param_changed, system_status, task_update
- Auto-reconnect support
- Event buffering for late-connecting clients
"""

import asyncio
import json
import logging
import uuid
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from fastapi import WebSocket, WebSocketDisconnect, Query

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    COMMAND = "command"
    RESPONSE = "response"
    EVENT = "event"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"


@dataclass
class WebSocketClient:
    """Connected UI client."""
    id: str
    websocket: WebSocket
    subscriptions: Set[str] = field(default_factory=set)
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ConfigManager:
    """Standalone config manager without kernel dependencies."""
    
    def __init__(self):
        self.config_path = Path(__file__).parent.parent / "runtime.yaml"
        self.config = {}
        self.load()
    
    def load(self):
        if self.config_path.exists():
            with open(self.config_path) as f:
                self.config = yaml.safe_load(f) or {}
    
    def get(self, param_id: str, default=None):
        parts = param_id.split(".")
        value = self.config
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        return value
    
    def set(self, param_id: str, value: Any) -> tuple[bool, Optional[str]]:
        parts = param_id.split(".")
        target = self.config
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        target[parts[-1]] = value
        
        try:
            with open(self.config_path, "w") as f:
                yaml.dump(self.config, f, default_flow_style=False)
            return True, None
        except Exception as e:
            return False, str(e)
    
    def get_all(self) -> Dict:
        def flatten(d, prefix=""):
            result = {}
            for k, v in d.items():
                param_id = f"{prefix}{k}" if prefix else k
                if isinstance(v, dict):
                    result.update(flatten(v, f"{param_id}."))
                else:
                    result[param_id] = v
            return result
        return flatten(self.config)
    
    def get_schema(self) -> Dict:
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
        
        flatten(self.config)
        
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
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "categories": categories,
            "total_parameters": len(params)
        }


class UIEventBroadcaster:
    """Broadcasts events to connected UI clients."""
    
    def __init__(self, max_buffer_size: int = 100):
        self._clients: Dict[str, WebSocketClient] = {}
        self._event_buffer: List[Dict] = []
        self._max_buffer_size = max_buffer_size
    
    async def connect(self, client_id: str, websocket: WebSocket) -> WebSocketClient:
        client = WebSocketClient(id=client_id, websocket=websocket)
        self._clients[client_id] = client
        logger.info(f"[WS] Client connected: {client_id}")
        return client
    
    async def disconnect(self, client_id: str) -> None:
        if client_id in self._clients:
            del self._clients[client_id]
            logger.info(f"[WS] Client disconnected: {client_id}")
    
    async def send_to(self, client_id: str, message: Dict) -> bool:
        if client_id not in self._clients:
            return False
        client = self._clients[client_id]
        try:
            await client.websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"[WS] Send error: {e}")
            await self.disconnect(client_id)
        return False
    
    async def broadcast(self, message: Dict, event_type: Optional[str] = None) -> int:
        self._event_buffer.append(message)
        if len(self._event_buffer) > self._max_buffer_size:
            self._event_buffer = self._event_buffer[-self._max_buffer_size:]
        
        sent = 0
        for client in list(self._clients.values()):
            if event_type is None or event_type in client.subscriptions:
                if await self.send_to(client.id, message):
                    sent += 1
        return sent
    
    async def get_buffered_events(self, limit: int = 100) -> List[Dict]:
        return self._event_buffer[-limit:]
    
    @property
    def client_count(self) -> int:
        return len(self._clients)


class UIWebSocketHandler:
    """Handles UI WebSocket connections."""
    
    def __init__(self):
        self.broadcaster = UIEventBroadcaster()
        self.config = ConfigManager()
    
    async def handle_connection(self, websocket: WebSocket, client_id: str) -> None:
        client = await self.broadcaster.connect(client_id, websocket)
        
        try:
            buffered = await self.broadcaster.get_buffered_events()
            if buffered:
                await websocket.send_json({
                    "type": "event",
                    "event_type": "buffered_events",
                    "data": buffered
                })
            
            while True:
                try:
                    data = await websocket.receive_text()
                    await self._handle_message(client, data)
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    logger.error(f"[WS] Message error: {e}")
        
        finally:
            await self.broadcaster.disconnect(client_id)
    
    async def _handle_message(self, client: WebSocketClient, data: str) -> None:
        try:
            message = json.loads(data)
        except json.JSONDecodeError:
            await client.websocket.send_json({"type": "error", "error": "Invalid JSON"})
            return
        
        msg_type = message.get("type", "command")
        method = message.get("method", "")
        params = message.get("params", {})
        msg_id = message.get("id", str(uuid4()))
        
        if msg_type == "ping":
            await client.websocket.send_json({"type": "pong", "id": msg_id})
            return
        
        handlers = {
            "GET_SCHEMA": self._handle_get_schema,
            "GET_PARAM": self._handle_get_param,
            "GET_ALL_PARAMS": self._handle_get_all_params,
            "SET_PARAM": self._handle_set_param,
            "SUBSCRIBE": self._handle_subscribe,
            "UNSUBSCRIBE": self._handle_unsubscribe,
            "GET_STATUS": self._handle_get_status,
        }
        
        handler = handlers.get(method)
        if not handler:
            await client.websocket.send_json({"type": "error", "id": msg_id, "error": f"Unknown: {method}"})
            return
        
        try:
            result = await handler(client, params)
            await client.websocket.send_json({"type": "response", "id": msg_id, "method": method, "result": result})
        except Exception as e:
            await client.websocket.send_json({"type": "error", "id": msg_id, "error": str(e)})
    
    async def _handle_get_schema(self, client, params):
        return self.config.get_schema()
    
    async def _handle_get_param(self, client, params):
        param_id = params.get("param_id")
        if not param_id:
            raise ValueError("param_id required")
        value = self.config.get(param_id)
        return {"param_id": param_id, "value": value}
    
    async def _handle_get_all_params(self, client, params):
        return self.config.get_all()
    
    async def _handle_set_param(self, client, params):
        param_id = params.get("param_id")
        value = params.get("value")
        if not param_id:
            raise ValueError("param_id required")
        
        success, error = self.config.set(param_id, value)
        
        if success:
            await self.broadcaster.broadcast({
                "type": "event",
                "event_type": "param_changed",
                "data": {"param_id": param_id, "new_value": value, "timestamp": datetime.now(timezone.utc).isoformat()}
            }, "param_changed")
        
        return {"success": success, "error": error}
    
    async def _handle_subscribe(self, client, params):
        events = params.get("events", [])
        for e in events:
            client.subscriptions.add(e)
        return {"subscribed": list(client.subscriptions)}
    
    async def _handle_unsubscribe(self, client, params):
        events = params.get("events", [])
        for e in events:
            client.subscriptions.discard(e)
        return {"subscribed": list(client.subscriptions)}
    
    async def _handle_get_status(self, client, params):
        return {
            "connected_clients": self.broadcaster.client_count,
            "uptime": "running",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


_handler: Optional[UIWebSocketHandler] = None

def get_ui_websocket_handler() -> UIWebSocketHandler:
    global _handler
    if _handler is None:
        _handler = UIWebSocketHandler()
    return _handler


async def ui_websocket_endpoint(websocket: WebSocket, client_id: str = Query(default=None)):
    await websocket.accept()
    if not client_id:
        client_id = str(uuid.uuid4())
    handler = get_ui_websocket_handler()
    await handler.handle_connection(websocket, client_id)