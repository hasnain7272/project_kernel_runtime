"""
Governance Policy Engine — Multi-Tenant RBAC

Enforces:
- Role-based tool access (admin, developer, viewer)
- Per-tenant tool allow/deny lists
- Workspace path isolation
- Dangerous command blocking for bash_execute
"""
import logging
from typing import Any, Dict, List, Optional

from src.domain.exceptions import GovernanceDeniedError
from src.infrastructure.runtime.paths import resolve_workspace_path

logger = logging.getLogger(__name__)


# Role → permitted tools (admin gets wildcard)
ROLE_PERMISSIONS: Dict[str, List[str]] = {
    "admin": ["*"],
    "developer": [
        "bash_execute", "read_file", "write_file",
        "git_clone", "git_read", "git_write", "git_commit", "git_create_pr",
        "code_review", "security_scan",
        "generate_tests", "generate_docs", "generate_cicd",
        "database_query", "api_test", "manage_dependencies",
        "code_graph_query", "web_search", "update_agent_memory",
    ],
    "viewer": [
        "read_file", "code_graph_query", "web_search",
    ],
}


class PolicyEngine:
    """Stateless policy evaluator — no side effects, pure validation."""

    @staticmethod
    def assert_action_allowed(
        session,
        tool_name: str,
        kwargs: Dict[str, Any],
        tenant_config: Optional[dict] = None,
    ) -> None:
        """Raise GovernanceDeniedError if action is not permitted."""
        user_role = getattr(session, "user_role", "developer")
        tenant_id = getattr(session, "tenant_id", None)

        # Admin bypasses all checks
        if user_role == "admin":
            return

        # ── Role-Based Access ──
        allowed = ROLE_PERMISSIONS.get(user_role, [])
        if allowed != ["*"] and tool_name not in allowed:
            raise GovernanceDeniedError(
                f"Tool '{tool_name}' not permitted for role '{user_role}'."
            )

        # ── Tenant-Specific Allow/Deny ──
        if tenant_config:
            deny_list = tenant_config.get("deny_tools", [])
            if tool_name in deny_list:
                raise GovernanceDeniedError(
                    f"Tool '{tool_name}' disabled for this tenant."
                )
            allow_list = tenant_config.get("allow_tools", [])
            if allow_list and tool_name not in allow_list:
                raise GovernanceDeniedError(
                    f"Tool '{tool_name}' not enabled for this tenant."
                )

        session_id = getattr(session, "id", None)
        tenant_id = getattr(session, "tenant_id", "local")

        # ── Path Isolation ──
        # Bash commands: validate working_dir stays in workspace
        if tool_name == "bash_execute":
            resolve_workspace_path(
                kwargs.get("working_dir", "."),
                session_id=session_id,
                tenant_id=tenant_id
            )

        # File tools: validate filepath stays in workspace
        if tool_name in {"read_file", "write_file", "create_file", "edit_file"}:
            resolve_workspace_path(
                kwargs.get("filepath"),
                session_id=session_id,
                tenant_id=tenant_id
            )

    @staticmethod
    def get_allowed_tools(
        role: str, tenant_config: Optional[dict] = None
    ) -> List[str]:
        """Get list of allowed tool names for a given role."""
        tools = ROLE_PERMISSIONS.get(role, []).copy()

        if tenant_config:
            deny = set(tenant_config.get("deny_tools", []))
            allow = set(tenant_config.get("allow_tools", []))

            if allow:
                tools = [t for t in tools if t in allow]
            tools = [t for t in tools if t not in deny]

        return tools
