"""
MCP REST API Schemas - Premium Production Grade

Shared Pydantic models for MCP dynamic plugins and stdio server routes.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Any, Dict, List, Optional

MAX_NAME_LENGTH = 128
MAX_DESCRIPTION_LENGTH = 1000

class ToolParameterSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    type: str = Field(default="string")
    description: str = Field(default="", max_length=500)
    required: bool = Field(default=True)
    default: Optional[Any] = None
    enum: Optional[List[str]] = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        valid_types = {"string", "number", "integer", "boolean", "array", "object"}
        if v not in valid_types:
            raise ValueError(f"Type must be one of: {', '.join(valid_types)}")
        return v

class PluginRegistrationRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=MAX_NAME_LENGTH)
    description: str = Field(default="", max_length=MAX_DESCRIPTION_LENGTH)
    endpoint_url: str = Field(...)
    parameters: List[ToolParameterSchema] = Field(default_factory=list)
    timeout_seconds: float = Field(default=30.0, ge=1.0, le=300.0)
    max_retries: int = Field(default=3, ge=0, le=10)
    verify_ssl: bool = Field(default=True)
    allowed_hosts: Optional[List[str]] = Field(default=None)

    @field_validator("endpoint_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v:
            raise ValueError("Endpoint URL is required")
        if not v.startswith(("http://", "https://")):
            raise ValueError("Endpoint must use http:// or https:// protocol")
        if len(v) > 2048:
            raise ValueError("Endpoint URL exceeds maximum length of 2048 characters")
        return v

class PluginUnregisterRequest(BaseModel):
    name: str = Field(..., description="Plugin name to unregister")

class ExecuteToolRequest(BaseModel):
    tool_name: str = Field(..., description="Name of the tool to execute")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")
    session_id: Optional[str] = Field(default=None, description="Session context for execution")

class StdioServerRegistration(BaseModel):
    name: str = Field(..., min_length=1, max_length=MAX_NAME_LENGTH)
    command: str = Field(..., min_length=1, max_length=256, description="Command to execute (e.g., 'npx')")
    args: List[str] = Field(default_factory=list, description="Command arguments")
    description: str = Field(default="", max_length=MAX_DESCRIPTION_LENGTH)
    working_dir: Optional[str] = Field(default=None, max_length=512)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Name must contain only alphanumeric, underscore, or hyphen characters")
        return v

    @field_validator("command")
    @classmethod
    def validate_command(cls, v: str) -> str:
        dangerous = ["rm", "del", "format", "mkfs", "dd", ">", "|", ";"]
        cmd_name = v.split()[0] if v else ""
        if cmd_name.lower() in dangerous:
            raise ValueError(f"Command '{cmd_name}' is not allowed for security reasons")
        return v

class ToolExecutionRequest(BaseModel):
    tool_name: str = Field(..., description="Name of the tool to execute")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
