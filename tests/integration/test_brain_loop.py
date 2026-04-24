import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.agent_loop.brain import BrainWorker
from src.services.agent_loop.tool_worker import ToolWorker
from src.infrastructure.queue.redis_streams_broker import LocalDurableBroker
from src.infrastructure.db.models.session_model import SessionModel
from src.infrastructure.db.models.task_model import TaskModel
from src.infrastructure.db.models.message_model import MessageModel

@pytest.mark.asyncio
async def test_react_loop_end_to_end(db_session: AsyncSession):
    # 1. Setup session and task
    session = SessionModel(id="test-session", tenant_id="test-tenant", mounted_folders=["test-folder"])
    db_session.add(session)
    
    task = TaskModel(id="test-task", session_id="test-session", tenant_id="test-tenant", description="Verify files")
    db_session.add(task)
    await db_session.commit()

    brain = BrainWorker()
    tool_worker = ToolWorker()
    broker = LocalDurableBroker()

    # 2. Mock LiteLLM to return a tool call
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                role="assistant",
                content="I will check the files.",
                tool_calls=[
                    MagicMock(
                        id="call_123",
                        function=MagicMock(
                            name="read_file",
                            arguments='{"path": "hello.txt"}'
                        )
                    )
                ]
            )
        )
    ]
    
    # Second call returns a final answer
    mock_final_response = MagicMock()
    mock_final_response.choices = [
        MagicMock(
            message=MagicMock(
                role="assistant",
                content="The file contains: hello world",
                tool_calls=None
            )
        )
    ]

    with patch("litellm.acompletion", side_effect=[mock_response, mock_final_response]):
        # 3. Simulate UI sending AGENT_THINK
        event = {
            "event_type": "AGENT_THINK",
            "task_id": "test-task",
            "session_id": "test-session",
            "description": "Verify files"
        }
        
        # This will trigger brain -> publish to execution_queue
        await brain.process_task_event(event, db_session)
        
        # 4. Verify brain published to execution_queue
        # In this test we manually trigger the tool worker to simulate the broker consumer
        # But first check if tool_call was persisted
        from sqlalchemy import select
        res = await db_session.execute(select(MessageModel).where(MessageModel.task_id == "test-task"))
        messages = res.scalars().all()
        assert any(m.role == "assistant" for m in messages)
        
        # 5. Execute tool worker
        # Normally this would be a separate process listening to the queue
        exec_event = {
            "event_type": "EXECUTE_TOOL",
            "task_id": "test-task",
            "session_id": "test-session",
            "tool_call_id": "call_123",
            "tool_name": "read_file",
            "arguments": {"path": "hello.txt"}
        }
        
        with patch("src.services.tool_execution.router.ToolExecutionRouter.execute_tool", return_value="hello world"):
            await tool_worker.process_tool_event(exec_event, db_session)

        # 6. Verify tool result persisted and brain re-triggered
        res = await db_session.execute(select(MessageModel).where(MessageModel.task_id == "test-task", MessageModel.role == "tool"))
        tool_msg = res.scalar_one_or_none()
        assert tool_msg.content == "hello world"

        # 7. Run brain again to process tool result
        await brain.process_task_event({"task_id": "test-task", "session_id": "test-session"}, db_session)
        
        # 8. Verify final answer
        res = await db_session.execute(select(MessageModel).where(MessageModel.task_id == "test-task"))
        final_messages = res.scalars().all()
        assert any("hello world" in m.content and m.role == "assistant" for m in final_messages)
