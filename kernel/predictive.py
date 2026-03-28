"""
Predictive Engine v2 — Task & Tool Prediction

Real implementation:
- Use task history + context to predict next useful actions
- Suggest tools based on file context
- Frequency-based ranking
"""

import logging
from collections import Counter, defaultdict
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class PredictiveEngine:
    """Predicts next useful actions based on task history."""

    def __init__(self):
        self.action_history: List[Dict] = []
        self.tool_transitions: Dict[str, Counter] = defaultdict(Counter)
        self.context_tools: Dict[str, Counter] = defaultdict(Counter)
        logger.info("[PredictiveEngine] Initialized")

    def record_action(self, tool_name: str, context: str = "",
                      file_ext: str = ""):
        """Record a tool action for pattern learning."""
        self.action_history.append({
            "tool": tool_name, "context": context, "file_ext": file_ext,
        })
        
        if file_ext:
            self.context_tools[file_ext][tool_name] += 1
        
        if len(self.action_history) >= 2:
            prev_tool = self.action_history[-2]["tool"]
            self.tool_transitions[prev_tool][tool_name] += 1

    def predict_next_tool(self, current_tool: str = "",
                          file_ext: str = "") -> List[Dict[str, Any]]:
        """Predict next useful tools."""
        suggestions = []
        
        if current_tool and current_tool in self.tool_transitions:
            transitions = self.tool_transitions[current_tool].most_common(3)
            for tool, count in transitions:
                suggestions.append({
                    "tool": tool, "confidence": min(count / 10, 1.0),
                    "reason": f"Often follows {current_tool}",
                })
        
        if file_ext and file_ext in self.context_tools:
            ext_tools = self.context_tools[file_ext].most_common(3)
            for tool, count in ext_tools:
                if not any(s["tool"] == tool for s in suggestions):
                    suggestions.append({
                        "tool": tool, "confidence": min(count / 10, 0.8),
                        "reason": f"Common for .{file_ext} files",
                    })
        
        return sorted(suggestions, key=lambda s: s["confidence"], reverse=True)[:5]

    def get_stats(self) -> Dict:
        return {
            "actions_recorded": len(self.action_history),
            "unique_transitions": len(self.tool_transitions),
            "file_contexts": len(self.context_tools),
        }
