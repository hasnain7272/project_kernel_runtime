"""
Workflow Engine: AgentScope-inspired Pipelines

This module provides the orchestration logic for complex, multi-step tasks
expressed as structured pipelines (Sequential, Fanout).

Inspired by: AgentScope (SequentialPipeline, FanoutPipeline)
"""

import asyncio
import logging
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

logger = logging.getLogger(__name__)

@dataclass
class PipelineStep:
    """A single step in a workflow pipeline."""
    tool_name: str
    arguments: Dict[str, Any]
    id: str = field(default_factory=lambda: str(uuid4().hex[:8]))
    depends_on: List[str] = field(default_factory=list)
    output_key: Optional[str] = None  # Key to store the result for later steps

@dataclass
class PipelineResult:
    """Result of a pipeline execution."""
    pipeline_id: str
    success: bool
    outputs: Dict[str, Any]
    step_results: List[Dict[str, Any]]
    error: Optional[str] = None

class BasePipeline:
    """Base class for all Agentic OS pipelines."""
    def __init__(self, name: str, executor: Any):
        self.name = name
        self.executor = executor
        self.pipeline_id = f"pipe_{uuid4().hex[:8]}"

    async def run(self, input_data: Any, context: Any) -> PipelineResult:
        raise NotImplementedError

class SequentialPipeline(BasePipeline):
    """
    Executes steps one by one.
    Output of step N can be used as input for step N+1 using '{{prev}}' or '{{step_id}}' syntax.
    """
    def __init__(self, name: str, steps: List[PipelineStep], executor: Any):
        super().__init__(name, executor)
        self.steps = steps

    async def run(self, input_data: Any, context: Any) -> PipelineResult:
        outputs = {"initial": input_data}
        step_results = []
        last_output = input_data
        
        logger.info(f"[SequentialPipeline] Starting {self.pipeline_id} ({self.name}) with {len(self.steps)} steps")
        
        for step in self.steps:
            # 1. Resolve arguments (template substitution)
            resolved_args = self._resolve_args(step.arguments, last_output, outputs)
            
            # 2. Execute tool via central hub
            from project_kernel_runtime.kernel.tool_executor import ToolCall
            call = ToolCall(
                name=step.tool_name,
                arguments=resolved_args,
                session_id=context.session_id,
                task_id=context.task_id
            )
            
            result = await self.executor.execute(call, context)
            
            # Record result
            res_entry = {
                "step_id": step.id,
                "tool": step.tool_name,
                "success": result.success,
                "output": result.output,
                "error": result.error,
                "duration_ms": result.duration_ms
            }
            step_results.append(res_entry)
            
            if not result.success:
                logger.error(f"[SequentialPipeline] Step {step.id} ({step.tool_name}) failed: {result.error}")
                return PipelineResult(self.pipeline_id, False, outputs, step_results, result.error)
            
            # Update context for next step
            last_output = result.output
            if step.output_key:
                outputs[step.output_key] = last_output
            outputs[step.id] = last_output
            
        return PipelineResult(self.pipeline_id, True, outputs, step_results)

    def _resolve_args(self, args: Dict, last_output: Any, all_outputs: Dict) -> Dict:
        """Substitute {{prev}} or {{key}} in arguments."""
        try:
            serialized = json.dumps(args)
            
            # Replace common placeholders
            if "{{prev}}" in serialized:
                serialized = serialized.replace('"{{prev}}"', json.dumps(last_output))
                
            for key, val in all_outputs.items():
                pattern = f'"{{{{{key}}}}}"'
                if pattern in serialized:
                    serialized = serialized.replace(pattern, json.dumps(val))
                    
            return json.loads(serialized)
        except Exception as e:
            logger.error(f"[SequentialPipeline] Argument resolution failed: {e}")
            return args

class FanoutPipeline(BasePipeline):
    """Executes steps in parallel."""
    def __init__(self, name: str, steps: List[PipelineStep], executor: Any):
        super().__init__(name, executor)
        self.steps = steps

    async def run(self, input_data: Any, context: Any) -> PipelineResult:
        logger.info(f"[FanoutPipeline] Starting {self.pipeline_id} ({self.name}) with {len(self.steps)} steps")
        
        from project_kernel_runtime.kernel.tool_executor import ToolCall
        
        # Parallel dispatch
        tasks = []
        for step in self.steps:
            call = ToolCall(
                name=step.tool_name,
                arguments=step.arguments,
                session_id=context.session_id,
                task_id=context.task_id
            )
            tasks.append(self.executor.execute(call, context))
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        outputs = {}
        step_results = []
        success = True
        error = None
        
        for i, res in enumerate(results):
            step = self.steps[i]
            
            if isinstance(res, Exception):
                entry = {
                    "step_id": step.id,
                    "tool": step.tool_name,
                    "success": False,
                    "error": str(res)
                }
                success = False
                error = str(res)
            else:
                entry = {
                    "step_id": step.id,
                    "tool": step.tool_name,
                    "success": res.success,
                    "output": res.output,
                    "error": res.error,
                    "duration_ms": res.duration_ms
                }
                if not res.success:
                    success = False
                    error = res.error
                outputs[step.output_key or step.id] = res.output
                
            step_results.append(entry)
            
        return PipelineResult(self.pipeline_id, success, outputs, step_results, error)
