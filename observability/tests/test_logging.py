"""
Tests for logging components.
"""

import json
import logging
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from project_kernel_runtime.observability.logging import (
    setup_logging,
    get_logger,
    JSONFormatter,
    StructuredLogger,
    log_api_request,
    log_task_execution,
    log_mcp_interaction,
    log_llm_call,
    log_error
)


class TestJSONFormatter:
    """Test cases for JSON formatter."""
    
    def test_format_basic_log(self):
        """Test basic log formatting."""
        formatter = JSONFormatter()
        
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        parsed = json.loads(formatted)
        
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test.logger"
        assert parsed["message"] == "Test message"
        assert parsed["module"] == "test"
        assert parsed["function"] == "<module>"
        assert parsed["line"] == 42
    
    def test_format_with_exception(self):
        """Test log formatting with exception."""
        formatter = JSONFormatter()
        
        try:
            raise ValueError("Test exception")
        except Exception:
            record = logging.LogRecord(
                name="test.logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=42,
                msg="Error message",
                args=(),
                exc_info=sys.exc_info()
            )
        
        formatted = formatter.format(record)
        parsed = json.loads(formatted)
        
        assert parsed["level"] == "ERROR"
        assert parsed["message"] == "Error message"
        assert "exception" in parsed
        assert parsed["exception"]["type"] == "ValueError"
        assert parsed["exception"]["message"] == "Test exception"
    
    def test_format_with_extra_fields(self):
        """Test log formatting with extra fields."""
        formatter = JSONFormatter()
        
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.extra = {"user_id": "123", "request_id": "abc"}
        
        formatted = formatter.format(record)
        parsed = json.loads(formatted)
        
        assert parsed["user_id"] == "123"
        assert parsed["request_id"] == "abc"


class TestStructuredLogger:
    """Test cases for structured logger."""
    
    def test_logger_initialization(self):
        """Test logger initialization."""
        logger = StructuredLogger("test.logger")
        
        assert logger.logger.name == "test.logger"
        assert len(logger.logger.handlers) > 0
    
    def test_log_methods(self):
        """Test all logging methods."""
        logger = StructuredLogger("test.logger")
        
        # Test each log level
        logger.info("Info message", extra={"key": "value"})
        logger.warning("Warning message", extra={"key": "value"})
        logger.error("Error message", extra={"key": "value"})
        logger.debug("Debug message", extra={"key": "value"})
        logger.critical("Critical message", extra={"key": "value"})
        logger.exception("Exception message", extra={"key": "value"})


class TestLoggingSetup:
    """Test cases for logging setup."""
    
    def test_setup_logging_basic(self):
        """Test basic logging setup."""
        with patch('project_kernel_runtime.observability.logging.Path') as mock_path:
            mock_path.return_value.mkdir = Mock()
            
            logger = setup_logging(level="INFO")
            
            assert logger is not None
            assert isinstance(logger, StructuredLogger)
    
    def test_setup_logging_with_log_dir(self):
        """Test logging setup with custom log directory."""
        with patch('project_kernel_runtime.observability.logging.Path') as mock_path:
            mock_path.return_value.mkdir = Mock()
            
            logger = setup_logging(level="DEBUG", log_dir="/custom/logs")
            
            assert logger is not None
    
    def test_get_logger(self):
        """Test getting logger instance."""
        logger = get_logger("test.logger")
        
        assert logger is not None
        assert isinstance(logger, StructuredLogger)
        assert logger.logger.name == "test.logger"


class TestLoggingFunctions:
    """Test cases for logging functions."""
    
    def test_log_api_request(self):
        """Test API request logging."""
        with patch('project_kernel_runtime.observability.logging.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            log_api_request(
                method="GET",
                path="/api/test",
                status_code=200,
                duration_ms=150.5,
                user_id="123",
                trace_id="abc123"
            )
            
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert call_args[0][0] == "API request processed"
            
            extra = call_args[1]['extra']
            assert extra["event"] == "api_request"
            assert extra["method"] == "GET"
            assert extra["path"] == "/api/test"
            assert extra["status_code"] == 200
            assert extra["duration_ms"] == 150.5
            assert extra["user_id"] == "123"
            assert extra["trace_id"] == "abc123"
    
    def test_log_task_execution(self):
        """Test task execution logging."""
        with patch('project_kernel_runtime.observability.logging.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            log_task_execution(
                task_id="task-123",
                task_type="research",
                status="completed",
                duration_ms=250.0,
                user_id="456",
                trace_id="def456"
            )
            
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert call_args[0][0] == "Task executed"
            
            extra = call_args[1]['extra']
            assert extra["event"] == "task_execution"
            assert extra["task_id"] == "task-123"
            assert extra["task_type"] == "research"
            assert extra["status"] == "completed"
            assert extra["duration_ms"] == 250.0
            assert extra["user_id"] == "456"
            assert extra["trace_id"] == "def456"
    
    def test_log_mcp_interaction(self):
        """Test MCP interaction logging."""
        with patch('project_kernel_runtime.observability.logging.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            log_mcp_interaction(
                method="call",
                tool_name="file_read",
                status="success",
                duration_ms=50.0,
                user_id="789",
                trace_id="ghi789"
            )
            
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert call_args[0][0] == "MCP interaction"
            
            extra = call_args[1]['extra']
            assert extra["event"] == "mcp_interaction"
            assert extra["method"] == "call"
            assert extra["tool_name"] == "file_read"
            assert extra["status"] == "success"
            assert extra["duration_ms"] == 50.0
            assert extra["user_id"] == "789"
            assert extra["trace_id"] == "ghi789"
    
    def test_log_llm_call(self):
        """Test LLM call logging."""
        with patch('project_kernel_runtime.observability.logging.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            log_llm_call(
                provider="openai",
                model="gpt-4",
                prompt_tokens=100,
                completion_tokens=200,
                duration_ms=1000.0,
                user_id="999",
                trace_id="jkl999"
            )
            
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert call_args[0][0] == "LLM provider call"
            
            extra = call_args[1]['extra']
            assert extra["event"] == "llm_call"
            assert extra["provider"] == "openai"
            assert extra["model"] == "gpt-4"
            assert extra["prompt_tokens"] == 100
            assert extra["completion_tokens"] == 200
            assert extra["duration_ms"] == 1000.0
            assert extra["user_id"] == "999"
            assert extra["trace_id"] == "jkl999"
    
    def test_log_error(self):
        """Test error logging."""
        with patch('project_kernel_runtime.observability.logging.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            log_error(
                error_type="ValueError",
                error_message="Test error message",
                context={"key": "value"},
                user_id="111",
                trace_id="mno111"
            )
            
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert call_args[0][0] == "Test error message"
            
            extra = call_args[1]['extra']
            assert extra["event"] == "error"
            assert extra["error_type"] == "ValueError"
            assert extra["context"] == {"key": "value"}
            assert extra["user_id"] == "111"
            assert extra["trace_id"] == "mno111"