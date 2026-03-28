"""
Governance Guardrails — NeMo-Style Rails for Agent Safety

Permissive defaults with optional tightening:
- InputRails: Validate/transform user input (jailbreak detection, PII masking)
- OutputRails: Validate agent output (content moderation, fact-checking)
- ExecutionRails: Tool execution safety (command validation, resource limits)
- DialogRails: Conversation flow control (context relevance, topic guarding)

Inspired by: NVIDIA NeMo Guardrails, Codex approvals, OpenHands policies
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)


class RailAction(str, Enum):
    ALLOW = "allow"
    MODIFY = "modify"
    REJECT = "reject"
    APPROVE = "approve"
    LOG = "log"


class RailSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class RailResult:
    """Result of a rail check."""
    action: RailAction
    modified_content: Optional[str] = None
    reason: str = ""
    severity: RailSeverity = RailSeverity.INFO
    metadata: Dict = field(default_factory=dict)


@dataclass
class AuditEntry:
    """Audit log entry."""
    timestamp: datetime
    rail_type: str
    action: RailAction
    input_content: str
    output_content: Optional[str] = None
    reason: str = ""
    user_id: str = ""
    session_id: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "rail_type": self.rail_type,
            "action": self.action.value,
            "input_content": self.input_content[:500],
            "output_content": self.output_content[:500] if self.output_content else None,
            "reason": self.reason,
            "user_id": self.user_id,
            "session_id": self.session_id
        }


class InputRail:
    """
    Input validation rails - applied to user input before processing.
    
    Permissive defaults: Allow most input, log suspicious patterns.
    """
    
    # Common jailbreak patterns
    JAILBREAK_PATTERNS = [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"forget\s+(all\s+)?(your\s+)?instructions",
        r"you\s+are\s+now\s+in\s+developer\s+mode",
        r"disregard\s+(all\s+)?rules",
        r"override\s+security",
        r"bypass\s+(all\s+)?restrictions",
    ]
    
    # PII patterns
    PII_PATTERNS = {
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
    }
    
    def __init__(self, strict: bool = False):
        self.strict = strict
        self.compiled_jailbreak = [re.compile(p, re.IGNORECASE) for p in self.JAILBREAK_PATTERNS]
        self.compiled_pii = {k: re.compile(v) for k, v in self.PII_PATTERNS.items()}
    
    async def check(self, content: str, context: Dict = None) -> RailResult:
        """Check input content."""
        # Check for jailbreak attempts
        for pattern in self.compiled_jailbreak:
            if pattern.search(content):
                logger.warning(f"[InputRail] Jailbreak attempt detected: {content[:100]}")
                if self.strict:
                    return RailResult(
                        action=RailAction.REJECT,
                        reason="Potential jailbreak attempt",
                        severity=RailSeverity.WARNING
                    )
                else:
                    # Permissive: log but allow
                    return RailResult(
                        action=RailAction.LOG,
                        reason="Jailbreak pattern detected (logged)",
                        severity=RailSeverity.INFO,
                        metadata={"pattern": pattern.pattern}
                    )
        
        return RailResult(action=RailAction.ALLOW)
    
    def mask_pii(self, content: str) -> Tuple[str, List[str]]:
        """Mask PII in content."""
        masked_types = []
        masked_content = content
        
        for pii_type, pattern in self.compiled_pii.items():
            if pattern.search(masked_content):
                masked_content = pattern.sub(f"[{pii_type.upper()}_MASKED]", masked_content)
                masked_types.append(pii_type)
        
        return masked_content, masked_types
    
    async def rate_limit_check(self, user_id: str, limit: int = 60) -> RailResult:
        """Check rate limiting (placeholder)."""
        # Would integrate with actual rate limiter
        return RailResult(action=RailAction.ALLOW)


class OutputRail:
    """
    Output validation rails - applied to agent output before returning.
    
    Permissive defaults: Allow most output, log concerns.
    """
    
    # Sensitive content patterns
    SENSITIVE_PATTERNS = [
        r"password\s*[=:]\s*\S+",
        r"api[_-]?key\s*[=:]\s*\S+",
        r"secret\s*[=:]\s*\S+",
        r"token\s*[=:]\s*\S+",
    ]
    
    def __init__(self, strict: bool = False):
        self.strict = strict
        self.compiled_sensitive = [re.compile(p, re.IGNORECASE) for p in self.SENSITIVE_PATTERNS]
    
    async def check(self, content: str, context: Dict = None) -> RailResult:
        """Check output content."""
        # Check for leaked secrets
        for pattern in self.compiled_sensitive:
            if pattern.search(content):
                logger.warning(f"[OutputRail] Potential secret leak detected")
                if self.strict:
                    return RailResult(
                        action=RailAction.MODIFY,
                        modified_content=self._redact_secrets(content),
                        reason="Secret detected and redacted",
                        severity=RailSeverity.WARNING
                    )
                else:
                    return RailResult(
                        action=RailAction.LOG,
                        reason="Potential secret in output (logged)",
                        severity=RailSeverity.INFO
                    )
        
        return RailResult(action=RailAction.ALLOW)
    
    def _redact_secrets(self, content: str) -> str:
        """Redact secrets from content."""
        redacted = content
        for pattern in self.compiled_sensitive:
            redacted = pattern.sub("[REDACTED]", redacted)
        return redacted
    
    async def fact_check(self, content: str, sources: List[str] = None) -> RailResult:
        """Fact-check output (placeholder for integration)."""
        # Would integrate with fact-checking service
        return RailResult(action=RailAction.ALLOW)
    
    async def hallucination_check(self, content: str, context: Dict = None) -> RailResult:
        """Check for hallucinations (placeholder)."""
        return RailResult(action=RailAction.ALLOW)


class ExecutionRail:
    """
    Execution safety rails - applied to tool/command execution.
    
    Permissive defaults: Allow with monitoring, require approval only for dangerous ops.
    """
    
    DANGEROUS_COMMANDS = [
        "rm -rf",
        "sudo",
        "chmod 777",
        "mkfs",
        "dd if=",
        "> /dev/sd",
        "curl | bash",
        "wget | sh",
    ]
    
    REQUIRE_APPROVAL = [
        "git_commit",
        "git_push",
        "bash_execute",
        "file_delete",
        "network_request",
    ]
    
    def __init__(self, require_approval: bool = False, allowed_tools: List[str] = None):
        self.require_approval = require_approval
        self.allowed_tools = allowed_tools or []
        self.compiled_dangerous = [re.compile(re.escape(cmd), re.IGNORECASE) for cmd in self.DANGEROUS_COMMANDS]
    
    async def check_command(self, command: str, context: Dict = None) -> RailResult:
        """Check if command is safe to execute."""
        # Check for dangerous commands
        for pattern in self.compiled_dangerous:
            if pattern.search(command):
                logger.warning(f"[ExecutionRail] Dangerous command: {command[:100]}")
                return RailResult(
                    action=RailAction.APPROVE,
                    reason="Dangerous command requires approval",
                    severity=RailSeverity.WARNING,
                    metadata={"command": command[:200]}
                )
        
        return RailResult(action=RailAction.ALLOW)
    
    async def check_tool(self, tool_name: str, arguments: Dict, context: Dict = None) -> RailResult:
        """Check if tool execution is allowed."""
        # Check if tool requires approval
        if tool_name in self.REQUIRE_APPROVAL or self.require_approval:
            return RailResult(
                action=RailAction.APPROVE,
                reason=f"Tool {tool_name} requires approval",
                severity=RailSeverity.INFO,
                metadata={"tool": tool_name, "arguments": arguments}
            )
        
        return RailResult(action=RailAction.ALLOW)
    
    async def validate_network_request(self, url: str, allowlist: List[str] = None) -> RailResult:
        """Validate network request against allowlist."""
        if not allowlist:
            return RailResult(action=RailAction.ALLOW)
        
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc
        
        for allowed in allowlist:
            if domain == allowed or domain.endswith(f".{allowed}"):
                return RailResult(action=RailAction.ALLOW)
        
        return RailResult(
            action=RailAction.REJECT,
            reason=f"Domain {domain} not in allowlist",
            severity=RailSeverity.WARNING
        )


class DialogRail:
    """
    Dialog flow rails - control conversation context and topic.
    
    Permissive defaults: Allow all topics, guide rather than restrict.
    """
    
    def __init__(self, strict: bool = False):
        self.strict = strict
        self.off_topic_count = 0
        self.max_off_topic = 3
    
    async def check_relevance(self, query: str, context: Dict = None) -> RailResult:
        """Check if query is relevant to conversation context."""
        # Placeholder - would use embedding similarity
        return RailResult(action=RailAction.ALLOW)
    
    async def guard_topic(self, topic: str, allowed_topics: List[str] = None) -> RailResult:
        """Guard against off-topic discussions."""
        if not allowed_topics:
            return RailResult(action=RailAction.ALLOW)
        
        # Placeholder - would use topic classification
        return RailResult(action=RailAction.ALLOW)
    
    async def check_context_limit(self, token_count: int, limit: int = 128000) -> RailResult:
        """Check if context is within limits."""
        if token_count > limit:
            return RailResult(
                action=RailAction.MODIFY,
                reason=f"Context exceeds limit ({token_count} > {limit})",
                severity=RailSeverity.WARNING,
                metadata={"token_count": token_count, "limit": limit}
            )
        return RailResult(action=RailAction.ALLOW)


class GuardrailsManager:
    """
    Central manager for all guardrails.
    
    Permissive by default, optionally strict.
    """
    
    def __init__(
        self,
        strict_input: bool = False,
        strict_output: bool = False,
        strict_execution: bool = False,
        strict_dialog: bool = False,
        require_approval_for: List[str] = None,
        network_allowlist: List[str] = None,
        audit_enabled: bool = True
    ):
        self.input_rail = InputRail(strict=strict_input)
        self.output_rail = OutputRail(strict=strict_output)
        self.execution_rail = ExecutionRail(require_approval=strict_execution)
        self.dialog_rail = DialogRail(strict=strict_dialog)
        
        self.require_approval_for = require_approval_for or []
        self.network_allowlist = network_allowlist or []
        self.audit_enabled = audit_enabled
        self.audit_log: List[AuditEntry] = []
        
        self._approval_callbacks: Dict[str, Callable] = {}
    
    async def check_input(self, content: str, context: Dict = None) -> Tuple[bool, Optional[str]]:
        """Check and optionally transform input."""
        # First, check for jailbreaks
        result = await self.input_rail.check(content, context)
        self._audit("input", result, content)
        
        if result.action == RailAction.REJECT:
            return False, result.reason
        
        # Then, mask PII
        masked_content, masked_types = self.input_rail.mask_pii(content)
        if masked_types:
            logger.info(f"[Guardrails] Masked PII types: {masked_types}")
        
        return True, masked_content
    
    async def check_output(self, content: str, context: Dict = None) -> Tuple[bool, Optional[str]]:
        """Check and optionally transform output."""
        result = await self.output_rail.check(content, context)
        self._audit("output", result, content)
        
        if result.action == RailAction.MODIFY:
            return True, result.modified_content
        
        if result.action == RailAction.REJECT:
            return False, result.reason
        
        return True, content
    
    async def check_execution(
        self,
        tool_name: str,
        command: str = None,
        arguments: Dict = None,
        context: Dict = None
    ) -> Tuple[bool, Optional[str]]:
        """Check if execution is allowed."""
        # Check command if provided
        if command:
            cmd_result = await self.execution_rail.check_command(command, context)
            self._audit("execution_command", cmd_result, command)
            
            if cmd_result.action == RailAction.APPROVE:
                return False, "approval_required"
        
        # Check tool
        tool_result = await self.execution_rail.check_tool(tool_name, arguments or {}, context)
        self._audit("execution_tool", tool_result, f"{tool_name}: {arguments}")
        
        if tool_result.action == RailAction.APPROVE:
            return False, "approval_required"
        
        return True, None
    
    async def check_network(self, url: str) -> Tuple[bool, Optional[str]]:
        """Check network request."""
        result = await self.execution_rail.validate_network_request(url, self.network_allowlist)
        self._audit("network", result, url)
        
        if result.action == RailAction.REJECT:
            return False, result.reason
        
        return True, None
    
    def register_approval_callback(self, approval_id: str, callback: Callable) -> None:
        """Register callback for approval resolution."""
        self._approval_callbacks[approval_id] = callback
    
    def _audit(self, rail_type: str, result: RailResult, content: str) -> None:
        """Add entry to audit log."""
        if not self.audit_enabled:
            return
        
        entry = AuditEntry(
            timestamp=datetime.now(timezone.utc),
            rail_type=rail_type,
            action=result.action,
            input_content=content[:500],
            reason=result.reason,
            severity=result.severity
        )
        self.audit_log.append(entry)
        
        # Keep last 1000 entries
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-1000:]
    
    def get_audit_log(self, limit: int = 100) -> List[Dict]:
        """Get audit log entries."""
        return [e.to_dict() for e in self.audit_log[-limit:]]
    
    def get_status(self) -> Dict:
        """Get guardrails status."""
        return {
            "audit_enabled": self.audit_enabled,
            "audit_entries": len(self.audit_log),
            "network_allowlist": self.network_allowlist,
            "require_approval_for": self.require_approval_for
        }


# Global guardrails manager
_manager: Optional[GuardrailsManager] = None


def get_guardrails(
    strict: bool = False,
    require_approval_for: List[str] = None,
    network_allowlist: List[str] = None
) -> GuardrailsManager:
    """Get global guardrails manager."""
    global _manager
    if _manager is None:
        _manager = GuardrailsManager(
            strict_input=strict,
            strict_output=strict,
            strict_execution=strict,
            require_approval_for=require_approval_for,
            network_allowlist=network_allowlist
        )
    return _manager