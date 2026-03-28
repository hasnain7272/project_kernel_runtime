"""
Antigravity Prime: Centralized Global State Hub (Month 25-26)
Architectural Pillar: Single Source of Truth (SSOT).
"""

from typing import Dict, Any, List
import time

class GlobalStateHub:
    """
    The Single Source of Truth (SSOT) for the entire Antigravity Kernel.
    Every agent step, sandbox state, and mesh heartbeat is tracked here.
    """
    def __init__(self):
        self.start_time = time.time()
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.sandboxes: Dict[str, Dict[str, Any]] = {}
        self.mesh_nodes: List[str] = []
        self.thought_stream: List[Dict[str, Any]] = []

    def update_task_state(self, task_id: str, status: str, result: Any = None):
        if task_id not in self.tasks:
            self.tasks[task_id] = {"started_at": time.time()}
        self.tasks[task_id].update({
            "status": status,
            "last_updated": time.time(),
            "result": result
        })

    def record_thought(self, agent_id: str, agent_type: str, thought: str):
        """Streams a 'Reasoning Frame' for total observability."""
        frame = {
            "timestamp": time.timestamp() if hasattr(time, 'timestamp') else time.time(),
            "agent_id": agent_id,
            "agent_type": agent_type,
            "thought": thought
        }
        self.thought_stream.append(frame)
        
        # Mirror to console for kernel log auditability
        print(f"[{agent_id.upper()}] ({agent_type}) {thought}")
        
        # Keep buffer small for performance - SaaS readiness
        if len(self.thought_stream) > 1000:
            self.thought_stream.pop(0)

    def get_snapshot(self) -> Dict[str, Any]:
        """Provides a complete system state for UI/API synchronization."""
        return {
            "uptime": time.time() - self.start_time,
            "active_tasks": len([t for t in self.tasks.values() if t["status"] == "running"]),
            "pending_remediations": 0, # Future SRE link
            "mesh_status": {
                "nodes": len(self.mesh_nodes),
                "is_healthy": True
            },
            "recent_thoughts": list(self.thought_stream[-10:])
        }

    def inject_thought_delta(self, agent_id: str, new_logic: str):
        """Hot Reloads 'Self-Attention' logic for a running agent."""
        self.record_thought("Hot_Reload_Emitter", "System", f"🔄 Injecting Hot Logic Delta into {agent_id}: {new_logic}")
        # In a real scenario, this would update the prompt or strategy of the living agent.
        if agent_id in self.tasks:
             self.tasks[agent_id]["hot_logic"] = new_logic

# Global Instance
state_hub = GlobalStateHub()
