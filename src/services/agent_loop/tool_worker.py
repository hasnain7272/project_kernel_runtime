"""
Tool Execution Worker

Subscribes to `execution_queue`. When it receives an EXECUTE_TOOL
event, it runs the tool through the governance + sandbox pipeline,
persists the result, and re-publishes AGENT_THINK so the brain can
continue reasoning. This is the ReAct loop's second half.
"""
import json
import logging
from typing import Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.queue.redis_broker import get_broker
from src.services.memory.context_builder import persist_message
from src.services.governance.policy_engine import PolicyEngine
from src.services.tool_execution.router import ToolExecutionRouter

logger = logging.getLogger(__name__)

# Tool class registry — maps LLM function names to tool instances
_tool_registry = None


def _get_tool_registry():
    global _tool_registry
    if _tool_registry is None:
        from src.tools.filesystem.read import ReadFileTool
        from src.tools.filesystem.write import WriteFileTool
        from src.tools.execution.bash import BashExecuteTool
        _tool_registry = {
            "read_file": ReadFileTool(),
            "write_file": WriteFileTool(),
            "bash_execute": BashExecuteTool(),
        }
    return _tool_registry


class ToolWorker:
    def __init__(self):
        self.router = ToolExecutionRouter()

    async def process_tool_event(
        self, event: Dict[str, Any], db: AsyncSession
    ):
        task_id = event.get("task_id")
        session_id = event.get("session_id")
        tool_spec = event.get("tool", {})
        tool_name = tool_spec.get("name", "")
        tool_args = tool_spec.get("args", {})
        broker = get_broker()

        logger.info(f"[ToolWorker] Executing: {tool_name}")

        # 1. Governance check
        try:
            from src.infrastructure.db.models.session_model import SessionModel
            from sqlalchemy import select
            result = await db.execute(
                select(SessionModel).where(SessionModel.id == session_id)
            )
            session = result.scalar_one_or_none()
            if session:
                PolicyEngine.assert_action_allowed(
                    session, tool_name, tool_args
                )
        except Exception as gov_err:
            logger.warning(f"[Governance] Denied: {gov_err}")
            await persist_message(
                db, session_id, "tool",
                f"GOVERNANCE DENIED: {gov_err}",
                task_id=task_id,
            )
            await db.commit()
            await _re_trigger_brain(broker, task_id, session_id)
            return

        # 2. Execute through the sandboxed router
        registry = _get_tool_registry()
        tool_instance = registry.get(tool_name)

        if not tool_instance:
            output = f"Unknown tool: {tool_name}"
            logger.error(output)
        else:
            try:
                result = await self.router.execute_tool(
                    tool_instance, session_id, tool_args
                )
                output = json.dumps(result, default=str)[:8000]
            except Exception as exec_err:
                output = f"TOOL ERROR: {exec_err}"
                logger.error(f"[ToolWorker] {output}")

        # 3. Persist tool result as a message
        await persist_message(
            db, session_id, "tool", output, task_id=task_id,
        )
        await db.commit()

        logger.info(f"[ToolWorker] Result persisted. Re-triggering brain.")

        # 4. Re-trigger brain → this closes the ReAct loop
        await _re_trigger_brain(broker, task_id, session_id)


async def _re_trigger_brain(broker, task_id: str, session_id: str):
    """Emit a new AGENT_THINK so the brain re-evaluates with tool results."""
    await broker.publish("task_queue", {
        "event_type": "AGENT_THINK",
        "task_id": task_id,
        "session_id": session_id,
        "description": "",  # Empty — context comes from DB now
    })
