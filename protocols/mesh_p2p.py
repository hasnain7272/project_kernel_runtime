"""
Mesh P2P v2 — Peer Discovery with Heartbeat Tracking

Upgraded from 20-line print statement to real peer registry:
- Peer registration with health status and last-seen timestamps
- Heartbeat tracking with configurable timeout
- Peer discovery and cleanup
"""

import logging
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class PeerInfo:
    """Information about a peer in the mesh."""
    def __init__(self, peer_id: str, address: str, port: int = 8000,
                 capabilities: List[str] = None, metadata: Dict = None):
        self.peer_id = peer_id
        self.address = address
        self.port = port
        self.capabilities = capabilities or []
        self.metadata = metadata or {}
        self.status = "healthy"
        self.registered_at = time.time()
        self.last_seen = time.time()
        self.heartbeat_count = 0

    def to_dict(self) -> Dict:
        return {
            "peer_id": self.peer_id, "address": self.address, "port": self.port,
            "capabilities": self.capabilities, "status": self.status,
            "last_seen": self.last_seen, "heartbeat_count": self.heartbeat_count,
        }


class GlobalMeshP2P:
    """Peer-to-peer mesh network for agent discovery and coordination."""

    def __init__(self, heartbeat_timeout: int = 60):
        self.peers: Dict[str, PeerInfo] = {}
        self.self_id = f"node_{uuid4().hex[:8]}"
        self.heartbeat_timeout = heartbeat_timeout
        logger.info(f"[MeshP2P] Node {self.self_id} initialized")

    def register_self(self, address: str = "localhost", port: int = 8000,
                      capabilities: List[str] = None) -> PeerInfo:
        """Register this node in the mesh."""
        peer = PeerInfo(self.self_id, address, port, capabilities or ["agent", "mcp"])
        self.peers[self.self_id] = peer
        return peer

    def register_peer(self, peer_id: str, address: str, port: int = 8000,
                      capabilities: List[str] = None) -> PeerInfo:
        peer = PeerInfo(peer_id, address, port, capabilities)
        self.peers[peer_id] = peer
        logger.info(f"[MeshP2P] Peer registered: {peer_id}@{address}:{port}")
        return peer

    def heartbeat(self, peer_id: str) -> bool:
        """Record heartbeat from peer."""
        peer = self.peers.get(peer_id)
        if peer:
            peer.last_seen = time.time()
            peer.heartbeat_count += 1
            peer.status = "healthy"
            return True
        return False

    def health_check(self) -> Dict[str, str]:
        """Check health of all peers, mark stale ones."""
        now = time.time()
        results = {}
        for pid, peer in self.peers.items():
            if (now - peer.last_seen) > self.heartbeat_timeout:
                peer.status = "stale"
            results[pid] = peer.status
        return results

    def discover_peers(self, capability: str = None) -> List[PeerInfo]:
        """Find peers, optionally filtered by capability."""
        peers = [p for p in self.peers.values() if p.status == "healthy"]
        if capability:
            peers = [p for p in peers if capability in p.capabilities]
        return peers

    def remove_stale_peers(self) -> int:
        """Remove peers that haven't sent heartbeats."""
        stale = [pid for pid, p in self.peers.items()
                 if p.status == "stale" and pid != self.self_id]
        for pid in stale:
            del self.peers[pid]
        return len(stale)

    def federated_sync(self, metrics: Dict[str, Any]):
        """Sync metrics with mesh (called by orchestrator)."""
        # Store metrics for peer sharing
        self_peer = self.peers.get(self.self_id)
        if self_peer:
            self_peer.metadata["last_metrics"] = metrics
            self_peer.metadata["sync_time"] = time.time()

    def get_mesh_status(self) -> Dict:
        return {
            "self_id": self.self_id,
            "total_peers": len(self.peers),
            "healthy": sum(1 for p in self.peers.values() if p.status == "healthy"),
            "stale": sum(1 for p in self.peers.values() if p.status == "stale"),
        }
