"""
Parameter Registry — Centralized Parameter Management

Centralized control center for all tunable system parameters:
- Get/set parameter values with validation
- Hot-reload support without restart
- Change callbacks for reactive updates
- Persistence to config files
- Event emission on changes

Inspired by: Cursor's config layer, OpenHands RuntimeProfile, Codex's dynamic config
"""

import asyncio
import logging
import os
import yaml
import json
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from .ui_schema import UISchemaGenerator, UIParameter, generate_ui_schema

logger = logging.getLogger(__name__)


ParamChangeCallback = Callable[[str, Any, Any], None]
ParamValidator = Callable[[str, Any], bool]


@dataclass
class ParameterChange:
    """Record of a parameter change."""
    param_id: str
    old_value: Any
    new_value: Any
    timestamp: datetime
    source: str = "unknown"


class ParameterValidator:
    """Validates parameter values."""
    
    VALIDATORS: Dict[str, ParamValidator] = {}
    
    @classmethod
    def register(cls, param_id: str, validator: ParamValidator) -> None:
        cls.VALIDATORS[param_id] = validator
    
    @classmethod
    def validate(cls, param_id: str, value: Any) -> bool:
        validator = cls.VALIDATORS.get(param_id)
        if validator:
            return validator(param_id, value)
        
        if param_id.endswith("_port"):
            return isinstance(value, int) and 1 <= value <= 65535
        
        if param_id.endswith("_enabled") or param_id.endswith("_active"):
            return isinstance(value, bool)
        
        if "timeout" in param_id or "limit" in param_id or "threshold" in param_id:
            return isinstance(value, (int, float)) and value >= 0
        
        return True
    
    @classmethod
    def get_validation_error(cls, param_id: str, value: Any) -> Optional[str]:
        """Get validation error message if invalid."""
        if not cls.validate(param_id, value):
            if param_id.endswith("_port"):
                return "Port must be between 1 and 65535"
            if "timeout" in param_id or "limit" in param_id:
                return "Value must be non-negative"
            return f"Invalid value for {param_id}"
        return None


class ParameterRegistry:
    """
    Centralized registry for all system parameters.
    
    Features:
    - Get/set with validation
    - Change callbacks
    - Hot-reload support
    - Persistence to YAML/JSON
    - Event emission
    """
    
    def __init__(self, config_path: str = "runtime.yaml"):
        self.config_path = config_path
        self.config: Dict = {}
        self.parameters: Dict[str, UIParameter] = {}
        self._change_callbacks: Dict[str, List[ParamChangeCallback]] = {}
        self._change_history: List[ParameterChange] = []
        self._global_callbacks: List[ParamChangeCallback] = []
        self._subscribers: Set[str] = set()
        self._lock = asyncio.Lock()
        self._schema_generator = UISchemaGenerator(config_path)
        
        self._register_default_validators()
        self._load_config()
        self._load_schema()
        
        logger.info("[ParameterRegistry] Initialized")
    
    def _register_default_validators(self) -> None:
        """Register default parameter validators."""
        ParameterValidator.register("sandbox.timeout_seconds", 
            lambda _, v: isinstance(v, (int, float)) and 1 <= v <= 3600)
        ParameterValidator.register("sandbox.memory_limit_mb",
            lambda _, v: isinstance(v, int) and 64 <= v <= 32768)
        ParameterValidator.register("server.port",
            lambda _, v: isinstance(v, int) and 1 <= v <= 65535)
        ParameterValidator.register("llm.temperature",
            lambda _, v: isinstance(v, (int, float)) and 0 <= v <= 2)
        ParameterValidator.register("orchestrator.max_iterations",
            lambda _, v: isinstance(v, int) and 1 <= v <= 200)
    
    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f) or {}
                logger.info(f"[ParameterRegistry] Loaded config from {self.config_path}")
            except Exception as e:
                logger.error(f"[ParameterRegistry] Failed to load config: {e}")
                self.config = {}
    
    def _load_schema(self) -> None:
        """Load parameter schema."""
        schema = self._schema_generator.generate()
        self.parameters = {p.id: p for p in schema.parameters}
    
    def get(self, param_id: str, default: Any = None) -> Any:
        """Get parameter value."""
        if param_id in self.parameters:
            return self.parameters[param_id].current_value
        
        parts = param_id.split(".")
        value = self.config
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        return value
    
    def set(self, param_id: str, value: Any, source: str = "api") -> tuple[bool, Optional[str]]:
        """
        Set parameter value with validation.
        
        Returns:
            (success: bool, error_message: Optional[str])
        """
        error = ParameterValidator.get_validation_error(param_id, value)
        if error:
            logger.warning(f"[ParameterRegistry] Validation failed for {param_id}: {error}")
            return False, error
        
        old_value = self.get(param_id)
        
        if param_id in self.parameters:
            self.parameters[param_id].current_value = value
        else:
            param = self._schema_generator.parameters.get(param_id)
            if param:
                param.current_value = value
                self.parameters[param_id] = param
            else:
                self._add_parameter(param_id, value)
        
        self._record_change(param_id, old_value, value, source)
        
        self._notify_callbacks(param_id, old_value, value)
        
        logger.info(f"[ParameterRegistry] Parameter {param_id} changed: {old_value} -> {value}")
        return True, None
    
    def _add_parameter(self, param_id: str, value: Any) -> None:
        """Add a new parameter dynamically."""
        from .ui_schema import UIParameter, ParameterTypeInferrer
        
        param = UIParameter(
            id=param_id,
            type=ParameterTypeInferrer.infer_type(value, param_id),
            label=ParameterTypeInferrer.get_label(param_id),
            description=f"Dynamic parameter: {param_id}",
            category=ParameterTypeInferrer.infer_category(param_id),
            default=value,
            current_value=value
        )
        self.parameters[param_id] = param
    
    def _record_change(self, param_id: str, old_value: Any, new_value: Any, source: str) -> None:
        """Record parameter change in history."""
        change = ParameterChange(
            param_id=param_id,
            old_value=old_value,
            new_value=new_value,
            timestamp=datetime.now(timezone.utc),
            source=source
        )
        self._change_history.append(change)
        if len(self._change_history) > 1000:
            self._change_history = self._change_history[-1000:]
    
    def _notify_callbacks(self, param_id: str, old_value: Any, new_value: Any) -> None:
        """Notify all registered callbacks."""
        for callback in self._global_callbacks:
            try:
                callback(param_id, old_value, new_value)
            except Exception as e:
                logger.error(f"[ParameterRegistry] Callback error: {e}")
        
        callbacks = self._change_callbacks.get(param_id, [])
        for callback in callbacks:
            try:
                callback(param_id, old_value, new_value)
            except Exception as e:
                logger.error(f"[ParameterRegistry] Callback error for {param_id}: {e}")
    
    def subscribe(self, param_id: str, callback: ParamChangeCallback) -> None:
        """Subscribe to parameter changes."""
        if param_id not in self._change_callbacks:
            self._change_callbacks[param_id] = []
        self._change_callbacks[param_id].append(callback)
    
    def unsubscribe(self, param_id: str, callback: ParamChangeCallback) -> None:
        """Unsubscribe from parameter changes."""
        if param_id in self._change_callbacks:
            self._change_callbacks[param_id] = [
                c for c in self._change_callbacks[param_id] if c != callback
            ]
    
    def subscribe_global(self, callback: ParamChangeCallback) -> None:
        """Subscribe to all parameter changes."""
        self._global_callbacks.append(callback)
    
    def unsubscribe_global(self, callback: ParamChangeCallback) -> None:
        """Unsubscribe from all parameter changes."""
        if callback in self._global_callbacks:
            self._global_callbacks.remove(callback)
    
    def get_schema(self) -> Dict:
        """Get UI schema for dynamic rendering."""
        schema = self._schema_generator.generate()
        
        for param_id, param in self.parameters.items():
            schema.parameters[param_id].current_value = param.current_value
        
        return schema.to_dict()
    
    def get_all_params(self) -> Dict[str, Any]:
        """Get all parameters as flat dictionary."""
        return {pid: p.current_value for pid, p in self.parameters.items()}
    
    def get_change_history(self, limit: int = 50) -> List[Dict]:
        """Get parameter change history."""
        changes = self._change_history[-limit:]
        return [
            {
                "param_id": c.param_id,
                "old_value": c.old_value,
                "new_value": c.new_value,
                "timestamp": c.timestamp.isoformat(),
                "source": c.source
            }
            for c in changes
        ]
    
    def search_params(self, query: str) -> List[Dict]:
        """Search parameters by label or ID."""
        query_lower = query.lower()
        results = []
        for param in self.parameters.values():
            if (query_lower in param.id.lower() or 
                query_lower in param.label.lower() or
                query_lower in param.description.lower()):
                results.append({
                    "id": param.id,
                    "label": param.label,
                    "category": param.category,
                    "value": param.current_value,
                    "type": param.type
                })
        return results
    
    def get_by_category(self, category: str) -> Dict[str, Any]:
        """Get all parameters in a category."""
        return {
            pid: param.current_value
            for pid, param in self.parameters.items()
            if param.category == category
        }
    
    def get_categories(self) -> List[Dict]:
        """Get all categories with parameter counts."""
        categories: Dict[str, int] = {}
        for param in self.parameters.values():
            categories[param.category] = categories.get(param.category, 0) + 1
        
        return [
            {"id": cat_id, "count": count}
            for cat_id, count in categories.items()
        ]
    
    async def save_to_config(self) -> bool:
        """Save current values back to config file."""
        try:
            async with self._lock:
                self._save_config_nolock()
            return True
        except Exception as e:
            logger.error(f"[ParameterRegistry] Failed to save config: {e}")
            return False
    
    def _save_config_nolock(self) -> None:
        """Save config without locking."""
        flat_params = {pid: p.current_value for pid, p in self.parameters.items()}
        
        nested = {}
        for key, value in flat_params.items():
            parts = key.split(".")
            current = nested
            for i, part in enumerate(parts[:-1]):
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(nested, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"[ParameterRegistry] Saved config to {self.config_path}")
    
    def reload(self) -> None:
        """Reload configuration from file."""
        self._load_config()
        self._load_schema()
        logger.info("[ParameterRegistry] Reloaded configuration")


_global_registry: Optional[ParameterRegistry] = None


def get_registry(config_path: str = "runtime.yaml") -> ParameterRegistry:
    """Get global parameter registry instance."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ParameterRegistry(config_path)
    return _global_registry


def get_param(param_id: str, default: Any = None) -> Any:
    """Convenience function to get parameter."""
    return get_registry().get(param_id, default)


def set_param(param_id: str, value: Any, source: str = "api") -> tuple[bool, Optional[str]]:
    """Convenience function to set parameter."""
    return get_registry().set(param_id, value, source)


if __name__ == "__main__":
    registry = get_registry()
    print(json.dumps(registry.get_schema(), indent=2))