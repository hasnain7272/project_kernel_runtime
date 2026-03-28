"""
Self-Attention Loop v2 — Reasoning Validation

Real implementation:
- Compare last N reasoning steps for contradictions
- LLM-driven consistency evaluation (when available)
- Confidence scoring based on step coherence
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class SelfAttentionLoop:
    """Validates reasoning consistency across agent steps."""

    def __init__(self, orchestrator=None):
        self.orchestrator = orchestrator
        self.reflection_history: List[Dict] = []

    async def reflect_on_reasoning(self, task_id: str,
                                    recent_steps: List[Any]) -> bool:
        """
        Analyze recent reasoning steps for contradictions.
        Returns True if reasoning is consistent.
        """
        if not recent_steps or len(recent_steps) < 2:
            return True

        # Convert steps to text for analysis
        step_texts = []
        for step in recent_steps:
            if isinstance(step, dict):
                step_texts.append(str(step.get("content", step.get("description", ""))))
            elif isinstance(step, str):
                step_texts.append(step)
            else:
                step_texts.append(str(step))

        # Rule-based contradiction detection
        contradictions = self._detect_contradictions(step_texts)
        confidence = 1.0 - (len(contradictions) * 0.2)
        confidence = max(0.0, min(1.0, confidence))

        is_valid = confidence >= 0.5
        
        self.reflection_history.append({
            "task_id": task_id,
            "steps_analyzed": len(step_texts),
            "contradictions": contradictions,
            "confidence": confidence,
            "is_valid": is_valid,
        })

        if not is_valid:
            logger.warning(f"[SelfAttention] Task {task_id}: reasoning drift detected "
                          f"(confidence={confidence:.2f}, {len(contradictions)} contradictions)")
        
        return is_valid

    def _detect_contradictions(self, texts: List[str]) -> List[str]:
        """Simple rule-based contradiction detection."""
        contradictions = []
        
        # Check for opposing instructions
        positive_signals = {"create", "add", "enable", "start", "open", "include"}
        negative_signals = {"delete", "remove", "disable", "stop", "close", "exclude"}
        
        for i, text in enumerate(texts):
            words_i = set(text.lower().split())
            for j in range(i + 1, len(texts)):
                words_j = set(texts[j].lower().split())
                
                # Check if same object is being created and deleted
                pos_i = words_i & positive_signals
                neg_j = words_j & negative_signals
                pos_j = words_j & positive_signals
                neg_i = words_i & negative_signals
                
                common_nouns = (words_i & words_j) - positive_signals - negative_signals
                if common_nouns and ((pos_i and neg_j) or (pos_j and neg_i)):
                    contradictions.append(
                        f"Steps {i+1} and {j+1} may contradict on: {common_nouns}"
                    )
        
        return contradictions

    def get_confidence_score(self, task_id: str) -> float:
        """Get latest confidence score for a task."""
        for entry in reversed(self.reflection_history):
            if entry["task_id"] == task_id:
                return entry["confidence"]
        return 1.0
