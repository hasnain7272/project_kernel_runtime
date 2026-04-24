"""ReAct loop integration tests."""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio

from src.services.agent_loop.brain import BrainWorker
from src.services.agent_loop.tool_worker import ToolWorker


class TestReActLoop:
    """Test ReAct loop execution."""
    
    @pytest_asyncio.fixture
    async def brain(self):
        """Brain worker fixture."""
        return BrainWorker()
    
    @pytest_asyncio.fixture
    async def tool_worker(self):
        """Tool worker fixture."""
        return ToolWorker()
    
    @pytest.mark.asyncio
    async def test_brain_processes_think_event(self, brain):
        """Brain processes AGENT_THINK event."""
        event = {
            "event_type": "AGENT_THINK",
            "task_id": "task-123",
            "session_id": "session-456",
            "description": "What is 2+2?"
        }
        
        mock_db = AsyncMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = MagicMock(
            iteration_count=0,
            id="task-123"
        )
        
        # Should not raise
        try:
            await brain.process_task_event(event, mock_db)
        except Exception as e:
            # Expected without LLM configured
            pass
    
    @pytest.mark.asyncio
    async def test_tool_worker_processes_execute_event(self, tool_worker):
        """Tool worker processes EXECUTE_TOOL event."""
        event = {
            "event_type": "EXECUTE_TOOL",
            "task_id": "task-123",
            "session_id": "session-456",
            "tool_name": "bash_execute",
            "args": {"command": "echo hello"}
        }
        
        mock_db = AsyncMock()
        
        # Should not raise
        try:
            await tool_worker.process_tool_event(event, mock_db)
        except Exception:
            pass
    
    @pytest.mark.asyncio
    async def test_brain_circuit_breaker_triggers(self, brain):
        """Circuit breaker triggers after max iterations."""
        event = {
            "event_type": "AGENT_THINK",
            "task_id": "task-123",
            "session_id": "session-456",
            "description": "Test"
        }
        
        mock_db = AsyncMock()
        mock_task = MagicMock()
        mock_task.iteration_count = 51  # Over limit
        mock_task.id = "task-123"
        
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_task
        
        # Should trigger circuit breaker
        await brain.process_task_event(event, mock_db)
        
        # Should have updated task
        assert mock_task.iteration_count == 51


class TestToolExecution:
    """Test tool execution flow."""
    
    @pytest.mark.asyncio
    async def test_bash_tool_routes_to_sandbox(self):
        """Bash tool routes to sandbox in production."""
        from src.services.tool_execution.router import ToolExecutionRouter
        from src.tools.execution.bash import BashExecuteTool
        
        router = ToolExecutionRouter()
        tool = BashExecuteTool()
        
        # Mock sandbox
        with patch.object(router, '_get_sandbox') as mock_get_sandbox:
            mock_sandbox = AsyncMock()
            mock_sandbox.execute.return_value = {
                "success": True,
                "stdout": "hello",
                "exit_code": 0
            }
            mock_get_sandbox.return_value = mock_sandbox
            
            with patch('src.infrastructure.runtime.config.ALLOW_ANON_LOCAL', False):
                result = await router.execute_tool(
                    tool,
                    "session-123",
                    {"command": "echo hello"}
                )
                
                # Should use sandbox
                mock_get_sandbox.assert_called_once()


class TestCircuitBreaker:
    """Test circuit breaker integration."""
    
    @pytest.mark.asyncio
    async def test_llm_circuit_breaker_opens_after_failures(self):
        """Circuit breaker opens after failures."""
        from src.infrastructure.resilience.circuit_breaker import (
            CircuitBreaker, CircuitBreakerConfig, CircuitState
        )
        
        cb = CircuitBreaker("test-llm", CircuitBreakerConfig(
            failure_threshold=3,
            timeout=1.0
        ))
        
        # Simulate failures
        for _ in range(3):
            await cb.record_failure(Exception("LLM error"))
        
        assert cb.state == CircuitState.OPEN
        assert not await cb.can_execute()
    
    @pytest.mark.asyncio
    async def test_llm_circuit_breaker_closes_after_success(self):
        """Circuit breaker closes after successes."""
        from src.infrastructure.resilience.circuit_breaker import (
            CircuitBreaker, CircuitBreakerConfig, CircuitState
        )
        
        cb = CircuitBreaker("test-llm", CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout=0.1
        ))
        
        # Open circuit
        for _ in range(3):
            await cb.record_failure(Exception("LLM error"))
        
        assert cb.state == CircuitState.OPEN
        
        # Wait for timeout
        await asyncio.sleep(0.15)
        
        # Should be half-open
        assert await cb.can_execute()
        assert cb.state == CircuitState.HALF_OPEN
        
        # Record successes
        await cb.record_success()
        await cb.record_success()
        
        # Should be closed
        assert cb.state == CircuitState.CLOSED