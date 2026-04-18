"""
Parallel Tool Execution Router

Supports modern LLM capabilities like OpenAI's parallel_tool_calls.
Executes independent tools concurrently for 2-3x latency reduction.
"""
import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Callable
from enum import Enum
import time

from src.tools.core.base import BaseTool
from src.infrastructure.observability.tracing import traced, tracer, SpanKind
from src.domain.exceptions import ToolExecutionError, GovernanceDeniedError

logger = logging.getLogger(__name__)


class DependencyType(Enum):
    """Types of tool dependencies."""
    NONE = "none"          # Can run in parallel with anything
    SEQUENTIAL = "sequential"  # Must run after previous tools
    FILE_READ = "file_read"    # Depends on file being written first
    FILE_WRITE = "file_write"  # Modifies files - careful with parallel


@dataclass
class ToolExecutionPlan:
    """Represents a tool call with dependency analysis."""
    tool_name: str
    tool_instance: BaseTool
    args: Dict[str, Any]
    dependencies: Set[str]  # Tool names this depends on
    dependency_type: DependencyType
    priority: int = 0  # Higher = execute first
    
    def __hash__(self):
        return hash(self.tool_name + json.dumps(self.args, sort_keys=True))


@dataclass
class ToolResult:
    """Result of a tool execution."""
    tool_name: str
    success: bool
    result: Any
    duration_ms: float
    error: Optional[str] = None
    trace_id: Optional[str] = None


class DependencyAnalyzer:
    """Analyzes tool calls to determine parallelization strategy."""
    
    # Tools that modify state and shouldn't run in parallel
    STATEFUL_TOOLS = {"write_file", "bash_execute", "delete_file", "move_file", "copy_file"}
    
    # Tools that are read-only and safe to parallelize
    READONLY_TOOLS = {"read_file", "search", "grep", "view", "list_directory"}
    
    @classmethod
    def analyze_dependencies(
        cls,
        tool_calls: List[Dict[str, Any]],
        registry: Dict[str, BaseTool]
    ) -> List[List[ToolExecutionPlan]]:
        """
        Analyze tool calls and group them into execution phases.
        
        Returns a list of phases, where each phase can be executed in parallel.
        """
        if not tool_calls:
            return []
        
        # Single tool call - no parallelization needed
        if len(tool_calls) == 1:
            tc = tool_calls[0]
            tool_name = tc.get("name", tc.get("function", {}).get("name"))
            tool = registry.get(tool_name)
            if tool:
                args = tc.get("args") or tc.get("function", {}).get("arguments", {})
                if isinstance(args, str):
                    args = json.loads(args)
                return [[ToolExecutionPlan(
                    tool_name=tool_name,
                    tool_instance=tool,
                    args=args,
                    dependencies=set(),
                    dependency_type=cls._classify_tool(tool_name)
                )]]
            return []
        
        # Multiple tool calls - analyze for parallelization
        plans = []
        file_writes = {}  # Track which files are being written
        
        for tc in tool_calls:
            tool_name = tc.get("name") or tc.get("function", {}).get("name", "")
            tool = registry.get(tool_name)
            
            if not tool:
                logger.warning(f"Unknown tool: {tool_name}")
                continue
            
            args = tc.get("args") or tc.get("function", {}).get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            
            dep_type = cls._classify_tool(tool_name)
            deps = set()
            
            # Check for file dependencies
            if dep_type != DependencyType.NONE and "filepath" in args:
                filepath = args["filepath"]
                if filepath in file_writes:
                    deps.add(file_writes[filepath])
            
            plan = ToolExecutionPlan(
                tool_name=tool_name,
                tool_instance=tool,
                args=args,
                dependencies=deps,
                dependency_type=dep_type,
                priority=cls._calculate_priority(tool_name, args)
            )
            plans.append(plan)
            
            # Track writes
            if dep_type == DependencyType.FILE_WRITE and "filepath" in args:
                file_writes[args["filepath"]] = tool_name
        
        # Group into phases using topological sort
        return cls._group_into_phases(plans)
    
    @classmethod
    def _classify_tool(cls, tool_name: str) -> DependencyType:
        """Classify tool by its side effects."""
        if tool_name in cls.READONLY_TOOLS:
            return DependencyType.NONE
        elif tool_name in cls.STATEFUL_TOOLS:
            if "write" in tool_name or "delete" in tool_name:
                return DependencyType.FILE_WRITE
            return DependencyType.SEQUENTIAL
        return DependencyType.SEQUENTIAL
    
    @classmethod
    def _calculate_priority(cls, tool_name: str, args: Dict) -> int:
        """Calculate execution priority."""
        # File reads before file writes
        if tool_name in cls.READONLY_TOOLS:
            return 10
        # Shorter commands first
        if tool_name == "bash_execute":
            cmd = args.get("command", "")
            return max(0, 5 - len(cmd) // 100)
        return 0
    
    @classmethod
    def _group_into_phases(
        cls,
        plans: List[ToolExecutionPlan]
    ) -> List[List[ToolExecutionPlan]]:
        """Group plans into execution phases."""
        if not plans:
            return []
        
        # Separate by dependency type
        parallelizable = [p for p in plans if p.dependency_type == DependencyType.NONE]
        sequential = [p for p in plans if p.dependency_type != DependencyType.NONE]
        
        phases = []
        
        # Phase 1: All read-only operations in parallel
        if parallelizable:
            phases.append(sorted(parallelizable, key=lambda p: -p.priority))
        
        # Phase 2+: Stateful operations in sequence
        for plan in sorted(sequential, key=lambda p: -p.priority):
            phases.append([plan])
        
        return phases


class ParallelToolRouter:
    """
    Router that supports parallel tool execution.
    
    Replaces the sequential ToolExecutionRouter with intelligent parallelization.
    """
    
    def __init__(self):
        self._dependency_analyzer = DependencyAnalyzer()
        self._max_parallel = int(os.environ.get("MAX_PARALLEL_TOOLS", "5"))
        self._execution_timeout = int(os.environ.get("TOOL_EXECUTION_TIMEOUT", "60"))
        
    async def execute_parallel(
        self,
        tool_calls: List[Dict[str, Any]],
        session_id: str,
        registry: Dict[str, BaseTool],
        governance_checker: Optional[Callable] = None
    ) -> List[ToolResult]:
        """
        Execute multiple tool calls with parallelization.
        
        This is the main entry point for modern LLM tool calling.
        """
        if not tool_calls:
            return []
        
        # Analyze dependencies and create execution plan
        phases = self._dependency_analyzer.analyze_dependencies(tool_calls, registry)
        
        if not phases:
            return []
        
        # Execute phases
        all_results = []
        
        for phase_idx, phase in enumerate(phases):
            logger.info(
                f"[ParallelRouter] Executing phase {phase_idx + 1}/{len(phases)} "
                f"with {len(phase)} tool(s)"
            )
            
            if len(phase) == 1:
                # Sequential execution
                result = await self._execute_single(
                    phase[0], session_id, governance_checker
                )
                all_results.append(result)
            else:
                # Parallel execution
                results = await self._execute_parallel_batch(
                    phase, session_id, governance_checker
                )
                all_results.extend(results)
        
        return all_results
    
    @traced(
        operation="tool.execute_single",
        kind=SpanKind.INTERNAL,
        attributes={"execution_mode": "sequential"}
    )
    async def _execute_single(
        self,
        plan: ToolExecutionPlan,
        session_id: str,
        governance_checker: Optional[Callable] = None
    ) -> ToolResult:
        """Execute a single tool."""
        start_time = time.time()
        
        try:
            # Governance check
            if governance_checker:
                governance_checker(plan.tool_name, plan.args)
            
            # Execute
            result = await plan.tool_instance.execute(
                session_id=session_id,
                **plan.args
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            return ToolResult(
                tool_name=plan.tool_name,
                success=True,
                result=result,
                duration_ms=duration_ms
            )
            
        except GovernanceDeniedError as e:
            duration_ms = (time.time() - start_time) * 1000
            return ToolResult(
                tool_name=plan.tool_name,
                success=False,
                result=None,
                duration_ms=duration_ms,
                error=f"GOVERNANCE DENIED: {e}"
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"[ParallelRouter] Tool {plan.tool_name} failed: {e}")
            return ToolResult(
                tool_name=plan.tool_name,
                success=False,
                result=None,
                duration_ms=duration_ms,
                error=str(e)
            )
    
    async def _execute_parallel_batch(
        self,
        plans: List[ToolExecutionPlan],
        session_id: str,
        governance_checker: Optional[Callable] = None
    ) -> List[ToolResult]:
        """Execute a batch of tools in parallel."""
        
        # Limit concurrent execution
        semaphore = asyncio.Semaphore(self._max_parallel)
        
        async def execute_with_limit(plan: ToolExecutionPlan) -> ToolResult:
            async with semaphore:
                return await self._execute_single(
                    plan, session_id, governance_checker
                )
        
        # Execute all in parallel with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*[
                    execute_with_limit(plan) for plan in plans
                ]),
                timeout=self._execution_timeout
            )
            return list(results)
        except asyncio.TimeoutError:
            logger.error("[ParallelRouter] Batch execution timed out")
            # Return timeout errors for incomplete tools
            return [
                ToolResult(
                    tool_name=plan.tool_name,
                    success=False,
                    result=None,
                    duration_ms=self._execution_timeout * 1000,
                    error="Execution timeout"
                )
                for plan in plans
            ]


class SmartToolRouter(ParallelToolRouter):
    """
    Smart router that adapts between sequential and parallel execution
    based on the tools being called.
    """
    
    def __init__(self):
        super().__init__()
        self._execution_stats = {
            "total_calls": 0,
            "parallel_calls": 0,
            "avg_parallel_batch_size": 0.0,
            "total_duration_ms": 0.0
        }
    
    async def execute(
        self,
        tool_calls: List[Dict[str, Any]],
        session_id: str,
        registry: Dict[str, BaseTool],
        governance_checker: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Smart execution that chooses between sequential and parallel.
        
        Returns format compatible with LLM tool call responses.
        """
        start_time = time.time()
        
        # Decide execution strategy
        if len(tool_calls) == 1:
            # Single tool - use simple execution
            result = await self._execute_single_tool(
                tool_calls[0], session_id, registry, governance_checker
            )
            results = [result]
        else:
            # Multiple tools - use parallel router
            results = await self.execute_parallel(
                tool_calls, session_id, registry, governance_checker
            )
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Update stats
        self._execution_stats["total_calls"] += len(tool_calls)
        if len(tool_calls) > 1:
            self._execution_stats["parallel_calls"] += 1
            self._execution_stats["avg_parallel_batch_size"] = (
                (self._execution_stats["avg_parallel_batch_size"] * 
                 (self._execution_stats["parallel_calls"] - 1) + len(tool_calls)) /
                self._execution_stats["parallel_calls"]
            )
        self._execution_stats["total_duration_ms"] += duration_ms
        
        # Format results for LLM
        formatted_results = []
        for result in results:
            formatted_results.append({
                "tool": result.tool_name,
                "success": result.success,
                "result": result.result if result.success else None,
                "error": result.error if not result.success else None,
                "duration_ms": result.duration_ms
            })
        
        return {
            "results": formatted_results,
            "execution_mode": "parallel" if len(tool_calls) > 1 else "sequential",
            "total_duration_ms": duration_ms,
            "tools_executed": len(results),
            "tools_successful": sum(1 for r in results if r.success)
        }
    
    async def _execute_single_tool(
        self,
        tool_call: Dict[str, Any],
        session_id: str,
        registry: Dict[str, BaseTool],
        governance_checker: Optional[Callable] = None
    ) -> ToolResult:
        """Execute a single tool call."""
        tool_name = tool_call.get("name") or tool_call.get("function", {}).get("name", "")
        tool = registry.get(tool_name)
        
        if not tool:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                result=None,
                duration_ms=0,
                error=f"Unknown tool: {tool_name}"
            )
        
        args = tool_call.get("args") or tool_call.get("function", {}).get("arguments", {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}
        
        plan = ToolExecutionPlan(
            tool_name=tool_name,
            tool_instance=tool,
            args=args,
            dependencies=set(),
            dependency_type=DependencyAnalyzer._classify_tool(tool_name)
        )
        
        return await self._execute_single(plan, session_id, governance_checker)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        stats = self._execution_stats.copy()
        if stats["total_calls"] > 0:
            stats["avg_duration_ms"] = stats["total_duration_ms"] / stats["total_calls"]
        else:
            stats["avg_duration_ms"] = 0
        return stats


# Factory function for backward compatibility
async def get_parallel_router() -> SmartToolRouter:
    """Get the parallel tool router instance."""
    return SmartToolRouter()


# Import at end to avoid circular imports
import os