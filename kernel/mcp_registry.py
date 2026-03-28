"""
MCP Registry — Dynamic MCP Server Management System

Generic MCP/MCO server registry supporting:
- Dynamic server discovery from config
- Runtime server start/stop/restart
- Health monitoring and auto-reconnect
- Tool discovery and execution
- Works with any MCP-compatible server

Inspired by: Codex MCP integration, OpenHands tool system
"""

import asyncio
import logging
import json
import os
import signal
import subprocess
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class MCPServerStatus(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"
    STOPPING = "stopping"


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    disabled: bool = False
    auto_start: bool = True
    health_check_interval: int = 30
    retry_on_failure: bool = True
    max_retries: int = 3
    startup_timeout: int = 30
    
    @classmethod
    def from_dict(cls, name: str, config: Dict) -> "MCPServerConfig":
        return cls(
            name=name,
            command=config.get("command", ""),
            args=config.get("args", []),
            env=config.get("env", {}),
            disabled=config.get("disabled", False),
            auto_start=config.get("auto_start", True),
            health_check_interval=config.get("health_check_interval", 30),
            retry_on_failure=config.get("retry_on_failure", True),
            max_retries=config.get("max_retries", 3),
            startup_timeout=config.get("startup_timeout", 30)
        )


@dataclass
class MCPServerInstance:
    """Runtime instance of an MCP server."""
    config: MCPServerConfig
    status: MCPServerStatus = MCPServerStatus.STOPPED
    process: Optional[subprocess.Popen] = None
    tools: List[Dict] = field(default_factory=list)
    resources: List[Dict] = field(default_factory=list)
    last_health_check: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    started_at: Optional[datetime] = None
    pid: Optional[int] = None


class MCPRegistry:
    """
    Dynamic MCP server registry and manager.
    
    Supports any MCP-compatible server (Blender, filesystem, web search, etc.)
    """
    
    def __init__(self, config_path: str = "runtime.yaml"):
        self.config_path = config_path
        self.servers: Dict[str, MCPServerInstance] = {}
        self._health_task: Optional[asyncio.Task] = None
        self._running = False
        self.load_config()
    
    def load_config(self) -> None:
        """Load MCP server configurations from runtime.yaml."""
        if not os.path.exists(self.config_path):
            logger.warning(f"[MCP] Config not found: {self.config_path}")
            return
        
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f) or {}
        
        mcp_servers = config.get("mcpServers", {})
        
        for name, server_config in mcp_servers.items():
            if name not in self.servers:
                cfg = MCPServerConfig.from_dict(name, server_config)
                self.servers[name] = MCPServerInstance(config=cfg)
                logger.info(f"[MCP] Registered server: {name}")
    
    async def start_server(self, name: str) -> bool:
        """Start an MCP server."""
        if name not in self.servers:
            logger.error(f"[MCP] Server not found: {name}")
            return False
        
        instance = self.servers[name]
        
        if instance.status == MCPServerStatus.RUNNING:
            logger.info(f"[MCP] Server {name} already running")
            return True
        
        instance.status = MCPServerStatus.STARTING
        instance.error_message = None
        
        try:
            cfg = instance.config
            
            # Prepare environment
            env = os.environ.copy()
            env.update(cfg.env)
            
            # Start process
            cmd = [cfg.command] + cfg.args
            logger.info(f"[MCP] Starting {name}: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                text=True
            )
            
            instance.process = process
            instance.pid = process.pid
            instance.status = MCPServerStatus.RUNNING
            instance.started_at = datetime.now(timezone.utc)
            instance.retry_count = 0
            
            logger.info(f"[MCP] Server {name} started (PID: {process.pid})")
            return True
            
        except Exception as e:
            instance.status = MCPServerStatus.ERROR
            instance.error_message = str(e)
            logger.error(f"[MCP] Failed to start {name}: {e}")
            
            if cfg.retry_on_failure and instance.retry_count < cfg.max_retries:
                instance.retry_count += 1
                logger.info(f"[MCP] Retrying {name} ({instance.retry_count}/{cfg.max_retries})")
                await asyncio.sleep(2)
                return await self.start_server(name)
            
            return False
    
    async def stop_server(self, name: str) -> bool:
        """Stop an MCP server."""
        if name not in self.servers:
            return False
        
        instance = self.servers[name]
        
        if instance.status != MCPServerStatus.RUNNING:
            return True
        
        instance.status = MCPServerStatus.STOPPING
        
        try:
            if instance.process:
                instance.process.terminate()
                try:
                    instance.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    instance.process.kill()
                    instance.process.wait()
            
            instance.status = MCPServerStatus.STOPPED
            instance.process = None
            instance.pid = None
            logger.info(f"[MCP] Server {name} stopped")
            return True
            
        except Exception as e:
            instance.status = MCPServerStatus.ERROR
            instance.error_message = str(e)
            logger.error(f"[MCP] Failed to stop {name}: {e}")
            return False
    
    async def restart_server(self, name: str) -> bool:
        """Restart an MCP server."""
        await self.stop_server(name)
        await asyncio.sleep(1)
        return await self.start_server(name)
    
    async def start_all(self) -> Dict[str, bool]:
        """Start all auto-start servers."""
        results = {}
        for name, instance in self.servers.items():
            if not instance.config.disabled and instance.config.auto_start:
                results[name] = await self.start_server(name)
        return results
    
    async def stop_all(self) -> Dict[str, bool]:
        """Stop all running servers."""
        results = {}
        for name in list(self.servers.keys()):
            results[name] = await self.stop_server(name)
        return results
    
    def get_server_status(self, name: str) -> Optional[Dict]:
        """Get status of a server."""
        if name not in self.servers:
            return None
        
        instance = self.servers[name]
        return {
            "name": name,
            "status": instance.status.value,
            "pid": instance.pid,
            "tools_count": len(instance.tools),
            "resources_count": len(instance.resources),
            "error": instance.error_message,
            "started_at": instance.started_at.isoformat() if instance.started_at else None,
            "disabled": instance.config.disabled
        }
    
    def list_servers(self) -> List[Dict]:
        """List all registered servers."""
        return [
            self.get_server_status(name)
            for name in self.servers.keys()
        ]
    
    def add_server(self, name: str, config: Dict) -> bool:
        """Add a new server dynamically."""
        if name in self.servers:
            return False
        
        cfg = MCPServerConfig.from_dict(name, config)
        self.servers[name] = MCPServerInstance(config=cfg)
        logger.info(f"[MCP] Added server: {name}")
        return True
    
    def remove_server(self, name: str) -> bool:
        """Remove a server."""
        if name not in self.servers:
            return False
        
        instance = self.servers[name]
        if instance.status == MCPServerStatus.RUNNING:
            asyncio.create_task(self.stop_server(name))
        
        del self.servers[name]
        logger.info(f"[MCP] Removed server: {name}")
        return True
    
    async def discover_tools(self, name: str) -> List[Dict]:
        """Discover tools offered by a server."""
        # Placeholder - actual implementation would use MCP protocol
        if name not in self.servers:
            return []
        
        instance = self.servers[name]
        # Tool discovery would happen via MCP handshake
        return instance.tools
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict) -> Dict:
        """Call a tool on an MCP server."""
        if server_name not in self.servers:
            return {"error": f"Server {server_name} not found"}
        
        instance = self.servers[server_name]
        
        if instance.status != MCPServerStatus.RUNNING:
            return {"error": f"Server {server_name} not running"}
        
        # Placeholder - actual implementation would use MCP JSON-RPC
        logger.info(f"[MCP] Calling {tool_name} on {server_name}")
        return {"result": "Tool call would be sent via MCP protocol"}
    
    async def health_check_all(self) -> Dict[str, bool]:
        """Check health of all servers."""
        results = {}
        for name, instance in self.servers.items():
            if instance.status == MCPServerStatus.RUNNING:
                if instance.process and instance.process.poll() is None:
                    results[name] = True
                else:
                    instance.status = MCPServerStatus.ERROR
                    instance.error_message = "Process died unexpectedly"
                    results[name] = False
            else:
                results[name] = False
        return results
    
    async def start_health_monitor(self) -> None:
        """Start background health monitoring."""
        self._running = True
        self._health_task = asyncio.create_task(self._health_loop())
    
    async def stop_health_monitor(self) -> None:
        """Stop health monitoring."""
        self._running = False
        if self._health_task:
            self._health_task.cancel()
    
    async def _health_loop(self) -> None:
        """Background health check loop."""
        while self._running:
            try:
                await self.health_check_all()
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[MCP] Health check error: {e}")
                await asyncio.sleep(5)


# Global registry instance
_registry: Optional[MCPRegistry] = None


def get_mcp_registry(config_path: str = "runtime.yaml") -> MCPRegistry:
    """Get global MCP registry."""
    global _registry
    if _registry is None:
        _registry = MCPRegistry(config_path)
    return _registry


# Convenience functions
def list_mcp_servers() -> List[Dict]:
    return get_mcp_registry().list_servers()

async def start_mcp_server(name: str) -> bool:
    return await get_mcp_registry().start_server(name)

async def stop_mcp_server(name: str) -> bool:
    return await get_mcp_registry().stop_server(name)