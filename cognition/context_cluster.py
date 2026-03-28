"""
Context-Aware Swarm Clusters (Month 15-16).
Dynamically self-organizes the federated mesh into specialized groups based on the active task.
"""

from typing import Dict, List, Any
from collections import defaultdict
from ..integrations.a2a_protocol import AgentCard

class ClusterState:
    IDLE = "idle"
    RESEARCHING = "researching"
    CODING = "coding"
    REVIEWING = "reviewing"

class SwarmCluster:
    """A dynamic, self-organizing cluster of specialized agents."""
    
    def __init__(self, name: str, focus: str):
        self.name = name
        self.focus = focus
        self.members: Dict[str, AgentCard] = {}
        self.state = ClusterState.IDLE
        self.efficiency_rating = 1.0

    def add_member(self, agent: AgentCard):
        self.members[agent.id] = agent
        
    def to_dict(self):
        return {
            "name": self.name,
            "focus": self.focus,
            "member_count": len(self.members),
            "state": self.state,
            "efficiency": self.efficiency_rating
        }

class ClusterManager:
    """Manages the lifecycle and distribution of agents into Context Clusters."""
    
    def __init__(self):
        self.clusters: Dict[str, SwarmCluster] = {
            "Research Ops": SwarmCluster("Research Ops", "data_aggregation"),
            "Core Eng": SwarmCluster("Core Eng", "code_generation"),
            "Security/QA": SwarmCluster("Security/QA", "code_review")
        }
        
    def organize_mesh(self, available_peers: List[AgentCard], active_context: str):
        """Dynamically assign peers to clusters based on the current context."""
        # Simple clustering heuristic for implementation
        for peer in available_peers:
            role = peer.role.lower()
            if "research" in role or "data" in role:
                self.clusters["Research Ops"].add_member(peer)
            elif "dev" in role or "code" in role:
                self.clusters["Core Eng"].add_member(peer)
            else:
                self.clusters["Security/QA"].add_member(peer)
                
        # Update cluster state based on global context
        if "research" in active_context.lower():
            self.clusters["Research Ops"].state = ClusterState.RESEARCHING
            self.clusters["Core Eng"].state = ClusterState.IDLE
        elif "build" in active_context.lower() or "code" in active_context.lower():
            self.clusters["Core Eng"].state = ClusterState.CODING
            self.clusters["Research Ops"].state = ClusterState.IDLE

    def get_cluster_topology(self) -> List[Dict[str, Any]]:
        return [c.to_dict() for c in self.clusters.values()]
