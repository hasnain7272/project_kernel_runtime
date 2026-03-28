"""
Skill Compiler v2 — Task Pattern Learning

Real implementation:
- Analyze completed tasks to extract reusable tool sequences
- Store patterns for future task suggestions
- Auto-suggest learned patterns
"""

import logging
from collections import Counter
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class LearnedSkill:
    """A reusable pattern extracted from task history."""
    def __init__(self, name: str, tool_sequence: List[str],
                 domain: str = "general", success_count: int = 1):
        self.name = name
        self.tool_sequence = tool_sequence
        self.domain = domain
        self.success_count = success_count

    def to_dict(self) -> Dict:
        return {
            "name": self.name, "tool_sequence": self.tool_sequence,
            "domain": self.domain, "success_count": self.success_count,
        }


class SkillCompiler:
    """Extracts and stores reusable task patterns."""

    def __init__(self):
        self.learned_skills: Dict[str, LearnedSkill] = {}
        self.session_log: List[Dict] = []
        logger.info("[SkillCompiler] Initialized")

    def analyze_session(self, task_id: str, domain: str,
                        tool_sequence: List[str] = None):
        """Analyze a completed task for reusable patterns."""
        tool_sequence = tool_sequence or []
        self.session_log.append({
            "task_id": task_id, "domain": domain,
            "tools": tool_sequence,
        })

        if len(tool_sequence) >= 2:
            skill_name = f"{domain}_pattern_{len(self.learned_skills)}"
            if skill_name not in self.learned_skills:
                skill = LearnedSkill(skill_name, tool_sequence, domain)
                self.learned_skills[skill_name] = skill
                logger.info(f"[SkillCompiler] Learned: {skill_name}")
            else:
                self.learned_skills[skill_name].success_count += 1

    def suggest_tools(self, domain: str, context: str = "") -> List[str]:
        """Suggest tools based on learned patterns."""
        domain_skills = [s for s in self.learned_skills.values()
                        if s.domain == domain]
        if not domain_skills:
            return []
        
        best = max(domain_skills, key=lambda s: s.success_count)
        return best.tool_sequence

    def get_skills(self, domain: str = None) -> List[Dict]:
        skills = list(self.learned_skills.values())
        if domain:
            skills = [s for s in skills if s.domain == domain]
        return [s.to_dict() for s in skills]

    def get_stats(self) -> Dict:
        return {
            "total_skills": len(self.learned_skills),
            "sessions_analyzed": len(self.session_log),
            "top_domains": Counter(s["domain"] for s in self.session_log).most_common(5),
        }
