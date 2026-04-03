"""
Orchestrator v2 — Coordinator Pattern with Agentic Loop

Refactored from 665-line God Object to Coordinator pattern:
- Lazy initialization via @cached_property (subsystems init on first use)
- Event bus architecture (all subsystems publish/subscribe to EventBus)
- Agentic loop (Gather → Plan → Act → Verify)
- Plugin-based feature pack loading
- All tool execution via ToolExecutor pipeline
- Research orchestration extracted to dedicated methods

Inspired by: OpenHands event-driven runtime, Cursor subagent orchestration,
Claude Code agentic loop, Aider architect/editor dual model
"""

import asyncio
import json
import logging
import os
import re
from functools import cached_property
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class VectorDBFacade:
    """Unified memory and codebase indexing services."""

    def __init__(self, config):
        from project_kernel_runtime.memory.chroma_store import (
            AgentMemory,
            ChromaVectorStore,
            CodebaseRAG,
        )

        persist_dir = getattr(config, "persist_dir", "./data/chroma_db") if config else "./data/chroma_db"
        shared_store = ChromaVectorStore(persist_dir=persist_dir)
        self.agent_memory = AgentMemory(shared_store)
        self.codebase_rag = CodebaseRAG(
            persist_dir=os.path.join(persist_dir, "codebase_index")
        )
        self.persist_dir = persist_dir


class Orchestrator:
    """
    Main coordination engine — Coordinator pattern.
    
    Subsystems are lazily initialized via @cached_property.
    All communication goes through EventBus.
    All tool execution goes through ToolExecutor pipeline.
    """

    def __init__(self, config_path: str = "runtime.yaml"):
        # Core config (eagerly loaded — everything depends on this)
        from .runtime import RuntimeConfig
        self.config = RuntimeConfig.from_yaml(config_path)
        
        # Active state (in-memory, not subsystems)
        self.active_sessions: Dict[str, Any] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.research_sessions: Dict[str, Any] = {}
        self.reports: Dict[str, Any] = {}
        self.feature_packs: Dict[str, Any] = {}
        
        logger.info("[Orchestrator] Created (subsystems lazy-initialized on demand)")

    # ════════════════════════════════════════════════════════════════════
    # Lazy Subsystems (@cached_property — init on first access)
    # ════════════════════════════════════════════════════════════════════

    @cached_property
    def event_bus(self):
        from .event_bus import EventBus
        bus = EventBus()
        logger.info("[Orchestrator] EventBus initialized")
        return bus

    @cached_property
    def governance(self):
        from .governance import GovernanceEngine
        engine = GovernanceEngine(self.config.governance.model_dump() if hasattr(self.config, 'governance') else {})
        logger.info("[Orchestrator] Governance initialized")
        return engine

    @cached_property
    def tool_executor(self):
        from .tool_executor import ToolExecutor
        from .universal_tools import get_all_tools
        executor = ToolExecutor(
            governance=self.governance,
            sandbox=self.sandbox,
            event_bus=self.event_bus,
            mcp_bridge=self.mcp_bridge,
        )
        # Register all built-in tools so the executor can dispatch them
        executor.register_tools(get_all_tools())
        logger.info(f"[Orchestrator] ToolExecutor initialized with {len(executor._tools)} tools")
        return executor

    @cached_property
    def sandbox(self):
        from .sandbox import ZeroTrustSandbox
        sandbox_config = getattr(self.config, 'sandbox', None)
        sb = ZeroTrustSandbox(config=sandbox_config)
        logger.info("[Orchestrator] Sandbox initialized")
        return sb

    @cached_property
    def tasks(self):
        from .task_state_machine import TaskStateMachine
        tsm = TaskStateMachine(event_bus=self.event_bus)
        logger.info("[Orchestrator] TaskStateMachine initialized")
        return tsm

    @cached_property
    def sessions(self):
        from .session_manager import SessionManager
        mgr = SessionManager(event_bus=self.event_bus)
        logger.info("[Orchestrator] SessionManager initialized")
        return mgr

    @property
    def session_manager(self):
        """Compatibility alias for older service code."""
        return self.sessions

    @cached_property
    def vector_db(self):
        facade = VectorDBFacade(getattr(self.config, "vector_db", None))
        logger.info("[Orchestrator] VectorDB facade initialized")
        return facade

    @cached_property
    def llm(self):
        from project_kernel_runtime.cognition.llm_provider import LLMProvider
        provider = LLMProvider(
            config=getattr(self.config, 'llm', None),
        )
        logger.info("[Orchestrator] LLMProvider initialized")
        return provider

    @cached_property
    def skills(self):
        from .skills_registry import SkillRegistry
        registry = SkillRegistry()
        logger.info("[Orchestrator] SkillRegistry initialized")
        return registry

    @cached_property
    def swarm(self):
        from .swarm import AgentSwarm
        sw = AgentSwarm(llm_provider=self.llm, event_bus=self.event_bus, tool_executor=self.tool_executor)
        logger.info("[Orchestrator] AgentSwarm initialized with LLM + ToolExecutor")
        return sw

    @cached_property
    def performance_core(self):
        from .rust_core import GACIEngine
        engine = GACIEngine()
        logger.info("[Orchestrator] PerformanceCore initialized")
        return engine

    @cached_property
    def analytics(self):
        from .analytics import AnalyticsService
        svc = AnalyticsService()
        logger.info("[Orchestrator] Analytics initialized")
        return svc

    @cached_property
    def mcp_client(self):
        from project_kernel_runtime.protocols.mcp_client import MCPClient
        mcp_cfg = getattr(self.config, 'mcp', None)
        url = getattr(mcp_cfg, 'server_url', None) if mcp_cfg else None
        if not url and mcp_cfg and getattr(mcp_cfg, "transport", "") == "websocket":
            host = getattr(mcp_cfg, "host", "127.0.0.1")
            port = getattr(mcp_cfg, "port", 3000)
            url = f"ws://{host}:{port}"
        if not url:
            url = "ws://localhost:3000"
        client = MCPClient(url)
        logger.info("[Orchestrator] MCPClient initialized")
        return client

    @cached_property
    def planner(self):
        from .planner import MissionPlanner
        p = MissionPlanner()
        logger.info("[Orchestrator] MissionPlanner initialized")
        return p

    @cached_property
    def observability(self):
        from .observability import NeuralTracer
        tracer = NeuralTracer("orchestrator")
        logger.info("[Orchestrator] Observability initialized")
        return tracer

    @cached_property
    def watchdog(self):
        from project_kernel_runtime.agents.watchdog import WatchdogAgent
        wd = WatchdogAgent(self.analytics, self)
        logger.info("[Orchestrator] Watchdog initialized")
        return wd

    @cached_property
    def sre(self):
        from project_kernel_runtime.agents.sre_swarm import SREMonitor
        sre = SREMonitor(self)
        logger.info("[Orchestrator] SREMonitor initialized")
        return sre

    @cached_property
    def mesh_p2p(self):
        from project_kernel_runtime.protocols.mesh_p2p import GlobalMeshP2P
        mesh = GlobalMeshP2P()
        logger.info("[Orchestrator] MeshP2P initialized")
        return mesh

    @cached_property
    def federated(self):
        from project_kernel_runtime.protocols.federated_hub import FederatedHub
        hub = FederatedHub()
        logger.info("[Orchestrator] FederatedHub initialized")
        return hub

    @cached_property
    def self_attention(self):
        from project_kernel_runtime.cognition.self_attention import SelfAttentionLoop
        loop = SelfAttentionLoop(self)
        logger.info("[Orchestrator] SelfAttention initialized")
        return loop

    @cached_property
    def skill_compiler(self):
        from .skill_compiler import SkillCompiler
        compiler = SkillCompiler()
        logger.info("[Orchestrator] SkillCompiler initialized")
        return compiler

    @cached_property
    def mcp_bridge(self):
        from .mcp_bridge import MCPBridge
        bridge = MCPBridge()
        logger.info("[Orchestrator] MCPBridge initialized")
        return bridge

    @cached_property
    def predictive(self):
        from .predictive import PredictiveEngine
        engine = PredictiveEngine()
        logger.info("[Orchestrator] PredictiveEngine initialized")
        return engine

    @cached_property
    def credits(self):
        from .credits_engine import credits_engine
        return credits_engine

    @cached_property
    def tenancy(self):
        from .multi_tenancy import tenancy_manager
        return tenancy_manager

    @cached_property
    def export_service(self):
        from .export_service import ExportService
        return ExportService()

    @cached_property
    def export_service(self):
        from .export_service import ExportService
        return ExportService()

    # ════════════════════════════════════════════════════════════════════
    # Lifecycle
    # ════════════════════════════════════════════════════════════════════

    async def initialize(self):
        """Initialize the orchestrator — only starts what's needed."""
        logger.info("[Orchestrator] Starting initialization...")

        # Hot-start essential subsystems
        _ = self.event_bus
        _ = self.governance

        # Start watchdog monitoring
        try:
            asyncio.create_task(self.watchdog.start_monitoring())
        except Exception as e:
            logger.warning(f"[Orchestrator] Watchdog start failed: {e}")

        # Connect MCP if configured
        mcp_cfg = getattr(self.config, 'mcp', None)
        if mcp_cfg and getattr(mcp_cfg, 'enabled', False) and getattr(mcp_cfg, "transport", "") == "websocket":
            try:
                await self.mcp_client.connect()
                logger.info("[Orchestrator] MCP connected")
            except Exception as e:
                logger.warning(f"[Orchestrator] MCP connect failed: {e}")

        # Boot persistent MCP servers from registry
        try:
            await self.mcp_bridge.boot_permanent_servers()
            logger.info(f"[Orchestrator] MCPBridge booted — {self.mcp_bridge.get_status()['connected_count']} servers connected")
        except Exception as e:
            logger.warning(f"[Orchestrator] MCPBridge boot failed: {e}")

        # Load feature packs dynamically
        await self._load_feature_packs()

        logger.info("[Orchestrator] Initialization complete")

    async def shutdown(self):
        """Graceful shutdown."""
        logger.info("[Orchestrator] Shutting down...")
        
        # Cancel running tasks
        for task_id, task in self.running_tasks.items():
            task.cancel()
            logger.info(f"[Orchestrator] Cancelled task {task_id}")

        # Disconnect MCP
        try:
            if hasattr(self, '_mcp_client'):
                await self.mcp_client.disconnect()
        except Exception:
            pass

        # Shutdown MCP Bridge
        try:
            await self.mcp_bridge.shutdown()
        except Exception:
            pass

        # Shutdown performance core
        try:
            if hasattr(self, '_performance_core'):
                self.performance_core.shutdown()
        except Exception:
            pass

        logger.info("[Orchestrator] Shutdown complete")

    async def _load_feature_packs(self):
        """Dynamically load feature packs based on config."""
        features = getattr(self.config, 'features', None)
        
        # GTM Swarm
        try:
            from project_kernel_runtime.agents.growth_swarm.gtm_swarm_controller import gtm_swarm
            self.feature_packs["gtm"] = gtm_swarm
            await gtm_swarm.initialize(orchestrator=self)
            logger.info("[Orchestrator] GTM Swarm feature pack loaded")
        except Exception as e:
            logger.debug(f"[Orchestrator] GTM Swarm not loaded: {e}")

    # ════════════════════════════════════════════════════════════════════
    # Agentic Loop (Gather → Plan → Act → Verify)
    # ════════════════════════════════════════════════════════════════════

    async def execute_agentic_loop(self, task_description: str,
                                     user_id: str = "agent",
                                     session_id: Optional[str] = None,
                                     max_iterations: int = 20,
                                     context_bindings: Optional[Dict[str, List[str]]] = None) -> Dict[str, Any]:
        """
        Core agentic loop — Manager-based multi-agent orchestration.
        
        Manager analyzes task → Decomposes into sub-tasks → 
        Dispatches to specialized agents → Aggregates results
        
        This replaces the single prompt loop with proper A2A multi-agent.
        """
        from .task_state_machine import TaskType, TaskStep, TaskStatus

        task = self.tasks.create_task(
            type=TaskType.CUSTOM,
            description=task_description,
            steps=[TaskStep(id="step_0", description=task_description, tools=[])],
            session_id=session_id,
        )

        session = self.sessions.get_session(session_id) if session_id else None
        
        ctx = {
            "workspace_path": session.workspace_path if session else ".",
            "tools": self._session_allowed_builtin_tools(session, context_bindings),
            "session_id": session_id,
            "session_manager": self.sessions,
        }
        
        try:
            from .manager import get_manager
            manager = get_manager(self.llm, self.tool_executor, self.event_bus)
            
            result = await manager.execute(
                task_description,
                session_id=session_id,
                context=ctx,
            )
            
            if result.get("status") == "error":
                task.status = TaskStatus.FAILED
                task.error = result.get("response", result.get("error", "Unknown error"))
                self.tasks.save_task(task)
                await self.event_bus.emit_and_publish("task.failed", {
                    "task_id": task.id,
                    "error": task.error,
                }, source="orchestrator")
                return {
                    "task_id": task.id,
                    "response": result.get("response", ""),
                    "error": task.error,
                    "mode": "manager_failed",
                }
            
            if session_id and session:
                self.sessions.add_message_to_session(session_id, "assistant", result.get("response", ""))
            
            task.status = TaskStatus.COMPLETED
            if task.steps:
                task.steps[0].result = result.get("response", "")
            self.tasks.save_task(task)
            
            await self.event_bus.emit_and_publish("task.completed", {
                "task_id": task.id,
                "iterations": result.get("iterations", 1),
                "mode": "manager",
            }, source="orchestrator")
            
            return {
                "task_id": task.id,
                "response": result.get("response", ""),
                "plan": result.get("plan", []),
                "results": result.get("results", {}),
                "mode": "manager",
                "usage": self.llm.get_usage_stats(),
            }
            
        except Exception as e:
            logger.error(f"[Orchestrator] Manager failed: {e}")
            await self.event_bus.emit_and_publish("agent.error", {
                "task_id": task.id,
                "error": str(e),
            }, source="orchestrator")
            
            return {
                "task_id": task.id,
                "response": f"Agent error: {str(e)[:100]}",
                "mode": "manager_failed",
                "error": str(e),
            }


    def _build_system_prompt(self, session=None) -> str:
        """Short system prompt — Claude Code style. Let the model do the work."""
        workspace = session.workspace_path if session else "."
        folders = ', '.join(getattr(session, 'folders', [])) if session else ""
        
        prompt = (
            f"You are an AI coding assistant. Workspace: {workspace}\n"
            f"Rules:\n"
            f"- Use your tools to read, write, and execute. Don't just explain.\n"
            f"- For file questions, use list_directory or read_file immediately.\n"
            f"- For web questions, use web_search.\n"
            f"- Chain tool calls when needed. Be concise.\n"
            f"- You only have access to tools you've been given access to."
        )
        if folders:
            prompt += f"\nBound folders: {folders}"
        
        # Add available tools to prompt so model knows
        tools = self._session_allowed_builtin_tools(session)
        prompt += f"\nAvailable tools: {', '.join(tools)}"
        return prompt

    def _session_allowed_builtin_tools(self, session, context_bindings: Dict = None) -> List[str]:
        """Return tools available to a session.
        
        Zero-trust: by default NO tools. User attaches skills to session.
        Only then those tools become available.
        
        Args:
            session: Session object with skills attribute
            context_bindings: Optional dict with skills list from request payload
        """
        # No session and no context = no tools
        session_skills = getattr(session, "skills", []) or [] if session else []
        cb_skills = (context_bindings.get("skills", []) if context_bindings else [])
        
        # Combine session skills + context binding skills
        all_skills = list(dict.fromkeys(session_skills + cb_skills))
        
        if not all_skills:
            return []
        
        # Get tools from skills
        tools = []
        for skill_name in all_skills:
            try:
                skill_tools = self.skills.get_tools_for_skill(skill_name)
                if skill_tools:
                    tools.extend(skill_tools)
            except Exception:
                continue
        
        return list(dict.fromkeys(tools)) if tools else []
    
    def _get_tool_schemas(self, session=None, context_bindings: Dict = None) -> List[Dict]:
        """Get tool schemas for LLM function calling, including external MCP tools."""
        from .universal_tools import get_all_tools
        tools = get_all_tools()
        allowed_builtin = set(self._session_allowed_builtin_tools(session, context_bindings))
        if session is not None:
            tools = [tool for tool in tools if tool.name in allowed_builtin]
        schemas = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema,
                }
            }
            for tool in tools
        ]
        
        # Inject external MCP tools from the bridge
        try:
            external_tools = self.mcp_bridge.get_all_external_tools()
            if session and getattr(session, "mcp_servers", None):
                allowed_mcp = set(session.mcp_servers)
                external_tools = [
                    tool for tool in external_tools
                    if tool.get("_mcp_server") in allowed_mcp
                ]
            schemas.extend(external_tools)
            if external_tools:
                logger.info(f"[Orchestrator] Injected {len(external_tools)} external MCP tools into LLM context")
        except Exception as e:
            logger.debug(f"[Orchestrator] No external MCP tools: {e}")
        
        return schemas

    # ════════════════════════════════════════════════════════════════════
    # Session Management
    # ════════════════════════════════════════════════════════════════════

    async def start_session(self, user_id: str, workspace_path: str,
                            mode: str = "cli") -> Any:
        session = self.sessions.create_session(user_id, workspace_path, mode)
        self.active_sessions[user_id] = session
        
        await self.event_bus.emit_and_publish("session.started", {
            "session_id": session.session_id,
            "user_id": user_id,
        }, source="orchestrator")
        
        return session

    async def end_session(self, user_id: str):
        session = self.active_sessions.get(user_id)
        if session:
            self.sessions.end_session(session.session_id)
            self.active_sessions.pop(user_id, None)

    async def get_session_context(self, identifier: str):
        """Resolve a session by session_id first, then by user_id."""
        session = self.sessions.get_session(identifier)
        if session:
            return session

        if identifier in self.active_sessions:
            return self.active_sessions[identifier]

        return self.sessions.get_active_session(identifier)

    # ════════════════════════════════════════════════════════════════════
    # Task Management
    # ════════════════════════════════════════════════════════════════════

    async def create_task(self, user_id: str, task_type, description: str,
                          steps: List[Dict[str, Any]],
                          context: Optional[Dict] = None):
        from .task_state_machine import TaskStep

        task_steps = [
            TaskStep(
                id=f"step_{i}",
                description=step_data["description"],
                tools=step_data.get("tools", []),
            )
            for i, step_data in enumerate(steps)
        ]

        session = self.active_sessions.get(user_id)
        task = self.tasks.create_task(
            task_type, description, task_steps,
            context=context,
            session_id=session.session_id if session else None,
        )

        if session:
            self.sessions.add_task_to_session(session.session_id, task.id)

        return task

    async def execute_task(self, user_id: str, task_id: str) -> bool:
        task = self.tasks.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        execution = asyncio.create_task(self._execute_task_async(user_id, task))
        self.running_tasks[task_id] = execution
        return True

    async def _execute_task_async(self, user_id: str, task):
        """Execute task with full pipeline integration."""
        try:
            # Performance core context
            await self.performance_core.memory.store_context(task.id, task.description)

            # Execute via async task machine
            success = await self.tasks.execute_task_async(task.id)

            # Skill compilation on success
            if success:
                try:
                    domain = task.description.split()[0] if task.description else "generic"
                    self.skill_compiler.analyze_session(task.id, domain)
                except Exception:
                    pass

            await self.governance.audit_log(
                user_id,
                "task_completed" if success else "task_failed",
                {"task_id": task.id, "success": success},
            )

        except Exception as e:
            logger.error(f"[Orchestrator] Task {task.id} failed: {e}")
            try:
                healed = await self.sre.monitor_and_heal(task.id, str(e))
                if healed:
                    logger.info(f"[Orchestrator] SRE healed task {task.id}")
            except Exception:
                pass

            task.fail_step(str(e))
            await self.governance.audit_log(
                user_id, "task_error", {"task_id": task.id, "error": str(e)}
            )
        finally:
            self.running_tasks.pop(task.id, None)

    async def cancel_task(self, user_id: str, task_id: str):
        task = self.running_tasks.get(task_id)
        if task:
            task.cancel()
            self.tasks.cancel_task(task_id)
        await self.governance.audit_log(user_id, "task_cancelled", {"task_id": task_id})

    async def get_task_status(self, user_id: str, task_id: str):
        return self.tasks.get_task(task_id)

    async def list_user_tasks(self, user_id: str, status=None):
        session = self.active_sessions.get(user_id)
        if not session:
            return []
        return [
            self.tasks.get_task(tid)
            for tid in session.task_history
            if self.tasks.get_task(tid) and (status is None or self.tasks.get_task(tid).status == status)
        ]

    # ════════════════════════════════════════════════════════════════════
    # Tool Execution (via ToolExecutor pipeline)
    # ════════════════════════════════════════════════════════════════════

    async def call_tool(self, user_id: str, tool_name: str,
                        arguments: Dict[str, Any],
                        session_id: Optional[str] = None) -> Any:
        """Execute tool through the ToolExecutor pipeline."""
        from .tool_executor import ToolCall as TC, ExecutionContext

        if session_id:
            self.sessions.update_session_activity(session_id)

        tc = TC(name=tool_name, arguments=arguments, session_id=session_id, user_id=user_id)
        session = self.sessions.get_session(session_id) if session_id else None
        allowed_builtin_tools = self._session_allowed_builtin_tools(session)
        enabled_features = ["skills", "llms"]
        if session and getattr(session, "mcp_servers", []):
            enabled_features.append("mcp")
        if session and getattr(session, "a2a_enabled", False):
            enabled_features.append("a2a")
        ctx = ExecutionContext(
            user_id=user_id,
            session_id=session_id or "default",
            execution_mode=self.config.mode if hasattr(self.config, 'mode') else "build",
            user_role=getattr(session, "user_role", getattr(self.config.governance, "default_role", "developer")) if session else getattr(self.config.governance, "default_role", "developer"),
            risk_mode=getattr(session, "risk_mode", "auto") if session else "auto",
            workspace_path=session.workspace_path if session else ".",
            enabled_features=enabled_features,
            enforce_skill_scope=session is not None,
            allowed_builtin_tools=allowed_builtin_tools,
            allowed_mcp_servers=getattr(session, "mcp_servers", []) if session else [],
            allowed_folders=getattr(session, "folders", []) if session else [],
        )

        result = await self.tool_executor.execute(tc, ctx)

        await self.governance.audit_log(
            user_id, "tool_called", {
                "tool": tool_name,
                "success": result.success,
                "output_preview": str(result.output)[:100] if result.output else "",
            }
        )

        return result

    # ════════════════════════════════════════════════════════════════════
    # Research Mode
    # ════════════════════════════════════════════════════════════════════

    async def start_research_session(self, user_id: str, query: str,
                                      params: Optional[Dict] = None):
        from .research import ResearchSession
        session_id = f"research_{len(self.research_sessions) + 1}"
        rs = ResearchSession(session_id=session_id, user_id=user_id,
                             query=query, params=params or {})
        self.research_sessions[session_id] = rs
        return rs

    async def list_research_sessions(self, user_id: str):
        return [s for s in self.research_sessions.values() if s.user_id == user_id]

    async def add_research_source(self, user_id: str, session_id: str,
                                   source_uri: str, source_type: str = "web"):
        from .research import Source
        session = self.research_sessions.get(session_id)
        if not session:
            raise ValueError("Session not found")

        import urllib.request
        try:
            req = urllib.request.Request(source_uri, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8', errors='ignore')
                snippet = html[:500] + "..." if len(html) > 500 else html
                metadata = {"status": response.status}
        except Exception as e:
            snippet = f"Error fetching source: {str(e)}"
            metadata = {"error": str(e)}
        src = Source(
            id=f"src_{len(session.sources) + 1}",
            type=source_type,
            uri=source_uri,
            content_snippet=snippet,
            fetched_at=datetime.now(timezone.utc),
            metadata=metadata,
        )
        session.sources.append(src)
        session.progress = min(0.9, session.progress + 0.2)
        return src

    async def summarize_session(self, user_id: str, session_id: str,
                                 strategy: str = "default"):
        from .research import ResearchReport
        from project_kernel_runtime.cognition.llm_provider import summarize_text
        
        session = self.research_sessions.get(session_id)
        if not session:
            raise ValueError("Session not found")

        combined = "\n".join([s.content_snippet or "" for s in session.sources])
        summary = summarize_text(combined, strategy=strategy, max_chars=2000)
        
        report_id = f"report_{len(self.reports) + 1}"
        report = ResearchReport(
            id=report_id, session_id=session_id,
            generated_at=datetime.now(timezone.utc), summary=summary,
        )
        session.reports.append(report)
        self.reports[report_id] = report
        session.progress = 1.0
        session.status = "completed"
        return report

    async def get_research_progress(self, user_id: str, session_id: str):
        session = self.research_sessions.get(session_id)
        if not session:
            raise ValueError("Session not found")
        return {"session_id": session_id, "status": session.status,
                "progress": session.progress}

    async def get_research_session(self, user_id: str, session_id: str):
        session = self.research_sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        return session

    async def list_research_reports(self, user_id: str):
        return [r for r in self.reports.values()
                if self.research_sessions.get(r.session_id)
                and self.research_sessions.get(r.session_id).user_id == user_id]

    async def export_research_report(self, user_id: str, session_id: str,
                                      report_id: str, format: str = "markdown"):
        from .export_service import ExportService
        session = await self.get_research_session(user_id, session_id)
        report = self.reports.get(report_id)
        if not report:
            raise ValueError(f"Report {report_id} not found")
        if format == "json":
            return ExportService.to_json(report)
        elif format == "markdown":
            return ExportService.to_markdown(report, session)
        return ExportService.to_json(report)

    # ════════════════════════════════════════════════════════════════════
    # System Status
    # ════════════════════════════════════════════════════════════════════

    async def get_system_status(self) -> Dict[str, Any]:
        return {
            "runtime": {"mode": getattr(self.config, 'mode', 'development'),
                        "version": getattr(self.config, 'version', '2.0.0')},
            "tasks": {"active": len(self.running_tasks),
                      "total": len(self.tasks.tasks)},
            "sessions": {"active": len(self.active_sessions),
                         "total": len(self.sessions.sessions)},
            "llm": self.llm.get_usage_stats(),
            "performance": self.performance_core.stats,
            "features": list(self.feature_packs.keys()),
        }

    async def get_available_skills(self, user_id: str) -> List[str]:
        all_skills = []
        for pack in ["core", "coding"]:
            try:
                pack_skills = self.skills.list_skills(pack)
                for skill in pack_skills:
                    all_skills.append(skill.name)
            except Exception:
                pass
        return all_skills

    def register_mcp_tools(self, mcp_server):
        """Register orchestrator tools with MCP server."""
        from project_kernel_runtime.protocols.mcp_server import MCPTool
        tools = [
            MCPTool(
                name="start_research_session",
                description="Start a research session",
                input_schema={"type": "object", "properties": {
                    "user_id": {"type": "string"},
                    "query": {"type": "string"},
                }, "required": ["user_id", "query"]},
            ),
            MCPTool(
                name="execute_agentic_loop",
                description="Execute an autonomous agentic task",
                input_schema={"type": "object", "properties": {
                    "description": {"type": "string"},
                }, "required": ["description"]},
            ),
        ]
        for tool in tools:
            mcp_server.register_tool(tool)

    # ════════════════════════════════════════════════════════════════════
    # GTM Feature Pack
    # ════════════════════════════════════════════════════════════════════

    async def trigger_gtm_campaign(self, name: str, niche: str):
        gtm = self.feature_packs.get("gtm")
        if not gtm:
            raise ValueError("GTM feature pack not loaded")
        return await gtm.start_campaign(name, niche)


# ════════════════════════════════════════════════════════════════════
# Global Instance
# ════════════════════════════════════════════════════════════════════

_orchestrator: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


async def init_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
        await _orchestrator.initialize()
    return _orchestrator
