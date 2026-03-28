"""
Structured logging implementation for Project Kernel Runtime.
"""

import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional, Union
from pathlib import Path

# Configure JSON formatter for structured logging
class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add extra fields if present
        if hasattr(record, 'extra'):
            log_entry.update(record.extra)
        
        # Add trace context if present
        if hasattr(record, 'trace_id'):
            log_entry["trace_id"] = record.trace_id
        if hasattr(record, 'span_id'):
            log_entry["span_id"] = record.span_id
        
        return json.dumps(log_entry, default=self._json_serializer)
    
    def _json_serializer(self, obj: Any) -> Any:
        """JSON serializer for non-serializable objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Path):
            return str(obj)
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)


class StructuredLogger:
    """Structured logger with JSON formatting and context support."""
    
    def __init__(self, name: str, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Avoid duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup logging handlers."""
        # Console handler with JSON formatting
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(console_handler)
        
        # File handler for logs directory
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "project_kernel_runtime.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(file_handler)
    
    def info(self, message: str, **kwargs):
        """Log info message with extra context."""
        extra = kwargs.get('extra', {})
        extra.update(kwargs)
        self.logger.info(message, extra={'extra': extra})
    
    def warning(self, message: str, **kwargs):
        """Log warning message with extra context."""
        extra = kwargs.get('extra', {})
        extra.update(kwargs)
        self.logger.warning(message, extra={'extra': extra})
    
    def error(self, message: str, **kwargs):
        """Log error message with extra context."""
        extra = kwargs.get('extra', {})
        extra.update(kwargs)
        self.logger.error(message, extra={'extra': extra})
    
    def debug(self, message: str, **kwargs):
        """Log debug message with extra context."""
        extra = kwargs.get('extra', {})
        extra.update(kwargs)
        self.logger.debug(message, extra={'extra': extra})
    
    def critical(self, message: str, **kwargs):
        """Log critical message with extra context."""
        extra = kwargs.get('extra', {})
        extra.update(kwargs)
        self.logger.critical(message, extra={'extra': extra})
    
    def exception(self, message: str, **kwargs):
        """Log exception message with extra context."""
        extra = kwargs.get('extra', {})
        extra.update(kwargs)
        self.logger.exception(message, extra={'extra': extra})


# Global logger instance
_root_logger: Optional[StructuredLogger] = None


def setup_logging(
    level: str = "INFO",
    log_dir: Optional[str] = None,
    json_format: bool = True
) -> StructuredLogger:
    """
    Setup structured logging for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files (default: ./logs)
        json_format: Whether to use JSON formatting
    
    Returns:
        Configured logger instance
    """
    global _root_logger
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create root logger
    _root_logger = StructuredLogger("project_kernel_runtime", numeric_level)
    
    # Set up environment-based logging
    if os.getenv("PROJECT_KERNEL_LOG_LEVEL"):
        env_level = os.getenv("PROJECT_KERNEL_LOG_LEVEL").upper()
        numeric_level = getattr(logging, env_level, logging.INFO)
        _root_logger.logger.setLevel(numeric_level)
    
    # Configure specific loggers
    _configure_loggers()
    
    _root_logger.info(
        "Logging initialized",
        extra={
            "level": level,
            "json_format": json_format,
            "log_dir": log_dir or "./logs"
        }
    )
    
    return _root_logger


def get_logger(name: str = "project_kernel_runtime") -> StructuredLogger:
    """Get a logger instance for the specified name."""
    if _root_logger is None:
        setup_logging()
    
    # Create child logger
    child_logger = StructuredLogger(name)
    return child_logger


def _configure_loggers():
    """Configure specific loggers for different components."""
    # Configure FastAPI logger
    fastapi_logger = logging.getLogger("fastapi")
    fastapi_logger.setLevel(logging.WARNING)
    
    # Configure uvicorn logger
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.setLevel(logging.INFO)
    
    # Configure OpenTelemetry logger
    otel_logger = logging.getLogger("opentelemetry")
    otel_logger.setLevel(logging.WARNING)


def log_api_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    user_id: Optional[str] = None,
    trace_id: Optional[str] = None
):
    """Log API request with structured data."""
    logger = get_logger("api")
    
    logger.info(
        "API request processed",
        extra={
            "event": "api_request",
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "user_id": user_id,
            "trace_id": trace_id
        }
    )


def log_task_execution(
    task_id: str,
    task_type: str,
    status: str,
    duration_ms: float,
    user_id: Optional[str] = None,
    trace_id: Optional[str] = None
):
    """Log task execution with structured data."""
    logger = get_logger("tasks")
    
    logger.info(
        "Task executed",
        extra={
            "event": "task_execution",
            "task_id": task_id,
            "task_type": task_type,
            "status": status,
            "duration_ms": duration_ms,
            "user_id": user_id,
            "trace_id": trace_id
        }
    )


def log_mcp_interaction(
    method: str,
    tool_name: str,
    status: str,
    duration_ms: float,
    user_id: Optional[str] = None,
    trace_id: Optional[str] = None
):
    """Log MCP interaction with structured data."""
    logger = get_logger("mcp")
    
    logger.info(
        "MCP interaction",
        extra={
            "event": "mcp_interaction",
            "method": method,
            "tool_name": tool_name,
            "status": status,
            "duration_ms": duration_ms,
            "user_id": user_id,
            "trace_id": trace_id
        }
    )


def log_llm_call(
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    duration_ms: float,
    user_id: Optional[str] = None,
    trace_id: Optional[str] = None
):
    """Log LLM provider call with structured data."""
    logger = get_logger("llm")
    
    logger.info(
        "LLM provider call",
        extra={
            "event": "llm_call",
            "provider": provider,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "duration_ms": duration_ms,
            "user_id": user_id,
            "trace_id": trace_id
        }
    )


def log_error(
    error_type: str,
    error_message: str,
    context: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    trace_id: Optional[str] = None
):
    """Log error with structured data."""
    logger = get_logger("errors")
    
    logger.error(
        error_message,
        extra={
            "event": "error",
            "error_type": error_type,
            "context": context or {},
            "user_id": user_id,
            "trace_id": trace_id
        }
    )