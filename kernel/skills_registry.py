"""
Skills Registry: Core Capabilities

Inspired by OpenHands skills + Aider capabilities
"""

from enum import Enum
from typing import List, Dict, Optional

class SkillLevel(str, Enum):
    READ_ONLY = "read_only"
    WRITE = "write"
    EXECUTE = "execute"
    NETWORK = "network"
    AUTONOMOUS = "autonomous"

class Skill:
    """Represents a skill with tools and permission level"""
    def __init__(
        self,
        name: str,
        description: str,
        tools: List[str],
        level: SkillLevel,
        pack: str = "core"
    ):
        self.name = name
        self.description = description
        self.tools = tools
        self.level = level
        self.pack = pack

# 7 Core Skills - Matched to universal_tools.py
CORE_SKILLS = [
    Skill(
        name="file_operations",
        description="Read, write, edit, and search files",
        tools=["read_file", "write_file", "edit_file", "search_files", "list_directory"],
        level=SkillLevel.WRITE,
        pack="core"
    ),
    Skill(
        name="terminal_execution",
        description="Execute shell commands with error capture",
        tools=["bash_execute"],
        level=SkillLevel.EXECUTE,
        pack="core"
    ),
    Skill(
        name="git_operations",
        description="Git status, diff, commit, and log operations",
        tools=["git_status", "git_diff", "git_commit", "git_log"],
        level=SkillLevel.WRITE,
        pack="core"
    ),
    Skill(
        name="web_operations",
        description="Web search and content fetching",
        tools=["web_search", "web_fetch"],
        level=SkillLevel.NETWORK,
        pack="core"
    ),
    Skill(
        name="browser_automation",
        description="Screenshot, navigation, visual bug fixes",
        tools=["screenshot", "navigate_url", "click_element"],
        level=SkillLevel.AUTONOMOUS,
        pack="core"
    ),
    Skill(
        name="lsp_integration",
        description="Symbol search via Language Server",
        tools=["goto_definition", "find_references", "rename_symbol"],
        level=SkillLevel.READ_ONLY,
        pack="core"
    ),
    Skill(
        name="custom_tools",
        description="Extensible via MCP resources",
        tools=["register_tool", "invoke_custom_tool"],
        level=SkillLevel.AUTONOMOUS,
        pack="core"
    ),
]

# Domain Packs (placeholder - tools not yet implemented)

CODING_PACK_SKILLS = [
    Skill(
        name="testing",
        description="Unit tests, integration tests (placeholder)",
        tools=["bash_execute"],  # Can use bash_execute to run pytest
        level=SkillLevel.EXECUTE,
        pack="coding"
    ),
    Skill(
        name="debugging",
        description="Breakpoints, memory profiling (placeholder)",
        tools=["read_file", "search_files"],  # Can inspect code
        level=SkillLevel.READ_ONLY,
        pack="coding"
    ),
]

class SkillRegistry:
    """Registry of all available skills"""

    def __init__(self):
        self.skills: Dict[str, Skill] = {}
        self.load_defaults()

    def load_defaults(self):
        """Load core 7 skills + optional packs"""
        for skill in CORE_SKILLS + CODING_PACK_SKILLS:
            self.skills[skill.name] = skill

    def get_skill(self, name: str) -> Skill:
        """Get skill by name"""
        return self.skills.get(name)

    def list_skills(self, pack: str = "core") -> List[Skill]:
        """List skills in a pack"""
        return [s for s in self.skills.values() if s.pack == pack]

    def get_tools_for_skill(self, skill_name: str) -> List[str]:
        """Get MCP tool names for a skill"""
        skill = self.get_skill(skill_name)
        return skill.tools if skill else []

    def get_skill_by_tool(self, tool_name: str) -> Optional[Skill]:
        """Get skill that contains a specific tool"""
        for skill in self.skills.values():
            if tool_name in skill.tools:
                return skill
        return None

    def to_mcp_tools(self, pack: str = "core") -> List[str]:
        """Convert skills to MCP tool names"""
        skills = self.list_skills(pack)
        tools = []
        for skill in skills:
            tools.extend(skill.tools)
        return tools
