"""
Dynamic Tool Registry (Hardened)

Auto-discovers tools AND provides manual fallback for core tools.
The system NEVER goes down because of a missing __init__.py or import error.
"""
import importlib
import inspect
import logging
import pkgutil
from typing import Dict, Type, List, Any, Optional

from src.tools.core.base import BaseTool

logger = logging.getLogger(__name__)

# Singleton tool instance cache
_tool_instances: Dict[str, BaseTool] = {}
_discovered = False


def _discover_tools():
    """Walk src.tools subpackages and register all BaseTool subclasses."""
    global _discovered
    if _discovered:
        return
    _discovered = True

    try:
        import src.tools as tools_pkg
        prefix = tools_pkg.__name__ + "."
        for _, modname, ispkg in pkgutil.walk_packages(tools_pkg.__path__, prefix):
            if not ispkg:
                try:
                    importlib.import_module(modname)
                except Exception as e:
                    logger.warning(f"Failed to load tool module {modname}: {e}")
    except Exception as e:
        logger.warning(f"Dynamic tool discovery failed: {e}")

    # Find ALL subclasses recursively (not just immediate children)
    def _all_subclasses(cls):
        result = set()
        for sub in cls.__subclasses__():
            result.add(sub)
            result.update(_all_subclasses(sub))
        return result

    for cls in _all_subclasses(BaseTool):
        if not inspect.isabstract(cls):
            try:
                instance = cls()
                if instance.name and instance.name not in _tool_instances:
                    _tool_instances[instance.name] = instance
            except Exception as e:
                logger.error(f"Failed to instantiate tool {cls.__name__}: {e}")

    # === MANUAL FALLBACK: If discovery missed core tools, force-register them ===
    _ensure_core_tools()

    names = list(_tool_instances.keys())
    logger.info(f"[Registry] Mounted {len(names)} tools: {', '.join(names)}")


def _ensure_core_tools():
    """Guarantee core tools exist even if auto-discovery fails."""
    fallback_map = {
        "bash_execute": "src.tools.execution.bash.BashExecuteTool",
        "read_file": "src.tools.filesystem.read.ReadFileTool",
        "write_file": "src.tools.filesystem.write.WriteFileTool",
    }
    for name, classpath in fallback_map.items():
        if name not in _tool_instances:
            try:
                module_path, class_name = classpath.rsplit(".", 1)
                mod = importlib.import_module(module_path)
                cls = getattr(mod, class_name)
                _tool_instances[name] = cls()
                logger.info(f"[Registry] Fallback-registered: {name}")
            except Exception as e:
                logger.error(f"[Registry] CRITICAL: Cannot load core tool {name}: {e}")


def get_all_tool_schemas() -> List[Dict[str, Any]]:
    """Returns the JSON schemas for all registered tools."""
    if not _discovered:
        _discover_tools()
    return [inst.get_schema() for inst in _tool_instances.values()]


def get_tool_instance(name: str) -> Optional[BaseTool]:
    """Retrieve an instantiated tool by its schema name."""
    if not _discovered:
        _discover_tools()
    return _tool_instances.get(name)


def get_tool_names() -> List[str]:
    """Returns the list of all registered tool names."""
    if not _discovered:
        _discover_tools()
    return list(_tool_instances.keys())
