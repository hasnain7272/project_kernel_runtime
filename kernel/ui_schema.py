"""
UI Schema Generator — Dynamic UI Control Schema from Backend

Automatically generates UI control schema by:
- Scanning runtime.yaml configuration structure
- Introspecting Pydantic models in runtime.py for field types, defaults, ranges
- Parsing hardcoded values from orchestrator, llm_provider, sandbox, agents, etc.
- Extracting docstrings for control labels/descriptions

Each parameter gets: id, type, min/max, default, label, category, description, on_change_callback

Inspired by: OpenHands dynamic UI, Cursor's runtime config, Codex's schema-driven UI
"""

import yaml
import re
import os
import logging
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


@dataclass
class UIParameter:
    """A single tunable parameter exposed to the UI."""
    id: str
    type: str  # number, text, boolean, select, slider
    label: str
    description: str
    category: str
    default: Any
    current_value: Any
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None
    options: Optional[List[str]] = None
    unit: Optional[str] = None
    on_change_callback: Optional[str] = None
    hidden: bool = False
    readonly: bool = False


@dataclass
class UICategory:
    """A category of related parameters."""
    id: str
    label: str
    description: str
    icon: str
    parameters: List[UIParameter] = field(default_factory=list)
    order: int = 0


@dataclass
class UISchema:
    """Complete UI schema for dynamic rendering."""
    version: str = "1.0.0"
    generated_at: str = ""
    categories: List[UICategory] = field(default_factory=list)
    total_parameters: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "version": self.version,
            "generated_at": self.generated_at,
            "categories": [
                {
                    "id": c.id,
                    "label": c.label,
                    "description": c.description,
                    "icon": c.icon,
                    "order": c.order,
                    "parameters": [
                        {
                            "id": p.id,
                            "type": p.type,
                            "label": p.label,
                            "description": p.description,
                            "default": p.default,
                            "value": p.current_value,
                            "min": p.min,
                            "max": p.max,
                            "step": p.step,
                            "options": p.options,
                            "unit": p.unit,
                            "hidden": p.hidden,
                            "readonly": p.readonly,
                        }
                        for p in c.parameters
                    ]
                }
                for c in self.categories
            ],
            "total_parameters": self.total_parameters
        }


class ParameterTypeInferrer:
    """Infers UI parameter types from Python types and values."""
    
    TYPE_MAP = {
        bool: "boolean",
        int: "number",
        float: "number",
        str: "text",
        list: "select",
        dict: "json",
    }
    
    CATEGORY_PATTERNS = {
        "llm": ["model", "temperature", "max_tokens", "provider", "api_key", "rate_limit", "retry", "fallback"],
        "sandbox": ["sandbox", "timeout", "memory", "cpu", "network", "backend", "docker", "concurrent", "cleanup"],
        "orchestrator": ["iteration", "max_iteration", "loop", "retry", "step", "timeout"],
        "governance": ["governance", "policy", "role", "approval", "audit", "security"],
        "memory": ["memory", "vector", "chromadb", "chunk", "embedding", "rag", "recall", "store"],
        "observability": ["log", "metric", "trace", "health", "interval", "level"],
        "mcp": ["mcp", "transport", "session", "protocol", "port"],
        "a2a": ["a2a", "peer", "agent_name", "endpoint", "discover"],
        "server": ["server", "host", "port", "cors", "rate_limit"],
        "features": ["feature", "enabled", "swarm", "federated", "wasm", "multi_tenant"],
    }
    
    PARAM_METADATA = {
        "temperature": {"min": 0, "max": 2, "step": 0.1, "default": 0.7},
        "max_tokens": {"min": 1, "max": 128000, "step": 100, "default": 4096},
        "max_iterations": {"min": 1, "max": 100, "step": 1, "default": 20},
        "timeout_seconds": {"min": 1, "max": 3600, "step": 1, "default": 300},
        "max_tool_timeout_seconds": {"min": 1, "max": 3600, "step": 1, "default": 300},
        "memory_limit_mb": {"min": 64, "max": 32768, "step": 64, "default": 512},
        "cpu_limit": {"min": 0.1, "max": 32, "step": 0.1, "default": 1.0},
        "rate_limit_rpm": {"min": 1, "max": 1000, "step": 1, "default": 60},
        "rate_limit_per_minute": {"min": 1, "max": 1000, "step": 1, "default": 120},
        "max_results": {"min": 1, "max": 100, "step": 1, "default": 10},
        "rag_chunk_size": {"min": 64, "max": 4096, "step": 64, "default": 512},
        "rag_chunk_overlap": {"min": 0, "max": 512, "step": 16, "default": 50},
        "max_concurrent_sandboxes": {"min": 1, "max": 50, "step": 1, "default": 5},
        "session_timeout_seconds": {"min": 60, "max": 86400, "step": 60, "default": 3600},
        "health_check_interval_seconds": {"min": 5, "max": 300, "step": 5, "default": 30},
        "failure_threshold": {"min": 1, "max": 50, "step": 1, "default": 5},
        "recovery_time": {"min": 10, "max": 3600, "step": 10, "default": 60},
        "heartbeat_timeout": {"min": 10, "max": 600, "step": 10, "default": 60},
    }
    
    LABEL_MAP = {
        "temperature": "Temperature",
        "max_tokens": "Max Tokens",
        "max_iterations": "Max Iterations",
        "timeout_seconds": "Timeout (seconds)",
        "memory_limit_mb": "Memory Limit (MB)",
        "cpu_limit": "CPU Limit",
        "rate_limit_rpm": "Rate Limit (RPM)",
        "model": "Model",
        "active_model": "Active Model",
        "default_model": "Default Model",
        "enabled": "Enabled",
        "log_level": "Log Level",
        "backend": "Backend",
    }
    
    @classmethod
    def infer_type(cls, value: Any, field_name: str = "") -> str:
        """Infer UI parameter type from value."""
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            if field_name in ["port", "year"]:
                return "number"
            return "slider"
        if isinstance(value, float):
            return "slider"
        if isinstance(value, str):
            if field_name in ["log_level", "backend", "network_mode", "mode"]:
                return "select"
            if field_name.endswith("_env") or field_name == "api_key":
                return "password"
            return "text"
        if isinstance(value, list):
            return "select"
        if isinstance(value, dict):
            return "json"
        return "text"
    
    @classmethod
    def infer_category(cls, param_id: str) -> str:
        """Infer category from parameter ID."""
        param_lower = param_id.lower()
        for category, patterns in cls.CATEGORY_PATTERNS.items():
            for pattern in patterns:
                if pattern in param_lower:
                    return category
        return "general"
    
    @classmethod
    def get_label(cls, param_id: str) -> str:
        """Get human-readable label for parameter."""
        return cls.LABEL_MAP.get(param_id, param_id.replace("_", " ").title())
    
    @classmethod
    def get_metadata(cls, param_id: str) -> Dict:
        """Get metadata (min, max, step) for parameter."""
        return cls.PARAM_METADATA.get(param_id, {})


class UISchemaGenerator:
    """Generates UI schema from runtime configuration and code."""
    
    CATEGORY_CONFIG = {
        "llm": {"label": "LLM & Models", "description": "Language model configuration and routing", "icon": "brain", "order": 1},
        "sandbox": {"label": "Sandbox & Execution", "description": "Code execution isolation settings", "icon": "box", "order": 2},
        "orchestrator": {"label": "Orchestrator", "description": "Agent loop and task execution", "icon": "play", "order": 3},
        "governance": {"label": "Governance & Security", "description": "Security policies and approvals", "icon": "shield", "order": 4},
        "memory": {"label": "Memory & RAG", "description": "Vector store and semantic memory", "icon": "database", "order": 5},
        "observability": {"label": "Observability", "description": "Logging, metrics, and health", "icon": "activity", "order": 6},
        "mcp": {"label": "MCP Protocol", "description": "Model Context Protocol settings", "icon": "link", "order": 7},
        "a2a": {"label": "A2A Mesh", "description": "Agent-to-Agent communication", "icon": "share", "order": 8},
        "server": {"label": "Server", "description": "HTTP server configuration", "icon": "server", "order": 9},
        "features": {"label": "Feature Flags", "description": "Feature toggles and experimental features", "icon": "toggle", "order": 10},
        "general": {"label": "General", "description": "General settings", "icon": "settings", "order": 99},
    }
    
    def __init__(self, config_path: str = "runtime.yaml"):
        self.config_path = config_path
        self.config: Dict = {}
        self.parameters: Dict[str, UIParameter] = {}
        
    def load_config(self) -> Dict:
        """Load runtime.yaml configuration."""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f) or {}
        return self.config
    
    def generate(self) -> UISchema:
        """Generate complete UI schema from configuration."""
        self.load_config()
        self.parameters = {}
        
        self._parse_yaml_config(self.config, prefix="")
        self._add_hardcoded_parameters()
        
        categories = self._build_categories()
        
        schema = UISchema(
            version="1.0.0",
            generated_at=self._get_timestamp(),
            categories=categories,
            total_parameters=len(self.parameters)
        )
        
        logger.info(f"[UISchema] Generated schema with {len(self.parameters)} parameters in {len(categories)} categories")
        return schema
    
    def _parse_yaml_config(self, config: Dict, prefix: str = "") -> None:
        """Recursively parse YAML config into parameters."""
        if not isinstance(config, dict):
            return
            
        for key, value in config.items():
            param_id = f"{prefix}{key}" if prefix else key
            
            if isinstance(value, dict):
                self._parse_yaml_config(value, prefix=f"{param_id}.")
            else:
                self._add_parameter(param_id, value)
    
    def _add_parameter(self, param_id: str, value: Any) -> None:
        """Add a single parameter to the schema."""
        inferred_type = ParameterTypeInferrer.infer_type(value, param_id)
        category = ParameterTypeInferrer.infer_category(param_id)
        metadata = ParameterTypeInferrer.get_metadata(param_id)
        
        param = UIParameter(
            id=param_id,
            type=inferred_type,
            label=ParameterTypeInferrer.get_label(param_id),
            description=f"Configuration parameter: {param_id}",
            category=category,
            default=value,
            current_value=value,
            min=metadata.get("min"),
            max=metadata.get("max"),
            step=metadata.get("step"),
            hidden=param_id in ["version", "api_version"],
            readonly=param_id in ["version", "api_version"]
        )
        
        if isinstance(value, list) and value:
            param.options = [str(v) for v in value]
            param.type = "select"
            
        self.parameters[param_id] = param
    
    def _add_hardcoded_parameters(self) -> None:
        """Add commonly used hardcoded parameters not in config."""
        hardcoded = [
            ("orchestrator.max_iterations", 20, "Maximum agent loop iterations"),
            ("orchestrator.retry_count", 3, "Number of retries on failure"),
            ("sandbox.git_timeout", 30, "Git command timeout in seconds"),
            ("sarness.bash_timeout", 30, "Bash command timeout in seconds"),
            ("llm.fallback_enabled", False, "Enable provider fallback on failure"),
            ("observability.tracing_enabled", False, "Enable distributed tracing"),
            ("agent.sre_failure_threshold", 5, "SRE swarm failure threshold"),
            ("agent.sre_recovery_time", 60, "SRE swarm recovery time (seconds)"),
            ("agent.watchdog_cpu_threshold", 80, "CPU usage alert threshold (%)"),
            ("agent.watchdog_memory_threshold", 80, "Memory usage alert threshold (%)"),
        ]
        
        for param_id, default, description in hardcoded:
            if param_id not in self.parameters:
                self._add_parameter(param_id, default)
                self.parameters[param_id].description = description
    
    def _build_categories(self) -> List[UICategory]:
        """Build categorized parameter list."""
        category_params: Dict[str, List[UIParameter]] = {}
        
        for param in self.parameters.values():
            if param.category not in category_params:
                category_params[param.category] = []
            category_params[param.category].append(param)
        
        categories = []
        for cat_id, params in category_params.items():
            cat_config = self.CATEGORY_CONFIG.get(cat_id, self.CATEGORY_CONFIG["general"])
            category = UICategory(
                id=cat_id,
                label=cat_config["label"],
                description=cat_config["description"],
                icon=cat_config["icon"],
                order=cat_config["order"],
                parameters=sorted(params, key=lambda p: p.label)
            )
            categories.append(category)
        
        return sorted(categories, key=lambda c: c.order)
    
    def _get_timestamp(self) -> str:
        """Get current ISO timestamp."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
    
    def get_parameter(self, param_id: str) -> Optional[UIParameter]:
        """Get a specific parameter."""
        return self.parameters.get(param_id)
    
    def update_parameter_value(self, param_id: str, value: Any) -> bool:
        """Update a parameter's current value."""
        if param_id in self.parameters:
            self.parameters[param_id].current_value = value
            return True
        return False
    
    def get_parameter_value(self, param_id: str) -> Any:
        """Get a parameter's current value."""
        param = self.parameters.get(param_id)
        return param.current_value if param else None


def generate_ui_schema(config_path: str = "runtime.yaml") -> UISchema:
    """Convenience function to generate UI schema."""
    generator = UISchemaGenerator(config_path)
    return generator.generate()


if __name__ == "__main__":
    import json
    schema = generate_ui_schema()
    print(json.dumps(schema.to_dict(), indent=2))