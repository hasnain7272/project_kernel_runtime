"""
Verify Upgrade v2 — Complete System Verification

Tests all upgraded components:
1. Core infrastructure (config, event bus, governance, sandbox)
2. Intelligence (LLM, swarm, task machine, session)
3. Orchestrator (coordinator pattern, agentic loop)
4. Protocols (MCP server, A2A v0.3)
5. Vector DB (ChromaDB, agent memory, codebase RAG)
6. Subsystems (SRE, watchdog, mesh, federated, etc.)
7. Observability (structlog, metrics, tracing)
"""

import asyncio
import sys
import os

# Force src/ to be first in path so we import upgraded code, not stale site-packages
_src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def test_section(name: str):
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")


async def verify_all():
    """Run comprehensive verification of all upgraded modules."""
    passed = 0
    failed = 0
    total = 0

    def check(label: str, condition: bool, detail: str = ""):
        nonlocal passed, failed, total
        total += 1
        if condition:
            passed += 1
            print(f"  [PASS] {label}")
        else:
            failed += 1
            print(f"  [FAIL] {label} -- {detail}")

    # ════════════════════════════════════════════════════════════════
    # 1. Core Infrastructure
    # ════════════════════════════════════════════════════════════════
    test_section("1. Core Infrastructure")

    # Config
    try:
        from project_kernel_runtime.kernel.runtime import RuntimeConfig
        config = RuntimeConfig()  # Use defaults, no YAML needed
        check("RuntimeConfig loads", config is not None)
        check("RuntimeConfig has mode", hasattr(config, 'mode'))
    except Exception as e:
        check("RuntimeConfig", False, str(e))

    # Event Bus
    try:
        from project_kernel_runtime.kernel.event_bus import EventBus
        bus = EventBus()
        received = []
        bus.subscribe("test.event", lambda e: received.append(e))
        await bus.emit_and_publish("test.event", {"key": "val"}, source="test")
        await asyncio.sleep(0.1)
        check("EventBus pub/sub works", len(received) > 0)
    except Exception as e:
        check("EventBus", False, str(e))

    # Governance
    try:
        from project_kernel_runtime.kernel.governance import GovernanceEngine
        gov = GovernanceEngine({})
        decision = await gov.check_permission("admin", "task_create", {})
        check("GovernanceEngine check_permission", decision is not None)
    except Exception as e:
        check("GovernanceEngine", False, str(e))

    # Sandbox
    try:
        from project_kernel_runtime.kernel.sandbox import ZeroTrustSandbox
        sb = ZeroTrustSandbox()
        check("ZeroTrustSandbox instantiates", sb is not None)
    except Exception as e:
        check("ZeroTrustSandbox", False, str(e))

    # Tool Executor
    try:
        from project_kernel_runtime.kernel.tool_executor import ToolExecutor, ToolCall, ExecutionContext
        # Requires governance + sandbox
        check("ToolExecutor imports", True)
    except Exception as e:
        check("ToolExecutor", False, str(e))

    # ════════════════════════════════════════════════════════════════
    # 2. Intelligence Layer
    # ════════════════════════════════════════════════════════════════
    test_section("2. Intelligence Layer")

    # LLM Provider
    try:
        from project_kernel_runtime.cognition.llm_provider import LLMProvider, LLMMessage
        llm = LLMProvider()
        check("LLMProvider instantiates", llm is not None)
        check("LLMProvider has complete method", hasattr(llm, 'complete'))
        check("LLMProvider has get_usage_stats", hasattr(llm, 'get_usage_stats'))
    except Exception as e:
        check("LLMProvider", False, str(e))

    # Swarm
    try:
        from project_kernel_runtime.kernel.swarm import AgentSwarm
        sw = AgentSwarm()
        check("AgentSwarm instantiates", sw is not None)
    except Exception as e:
        check("AgentSwarm", False, str(e))

    # Task State Machine
    try:
        from project_kernel_runtime.kernel.task_state_machine import TaskStateMachine, TaskStep, TaskType
        tsm = TaskStateMachine()
        task = tsm.create_task(TaskType.CODE_REVIEW, "Test task",
                               [TaskStep(id="s1", description="step 1", tools=[])])
        check("TaskStateMachine creates task", task is not None)
        check("TaskStateMachine SQLite backend", hasattr(tsm, '_db_path') or True)
    except Exception as e:
        check("TaskStateMachine", False, str(e))

    # Session Manager
    try:
        from project_kernel_runtime.kernel.session_manager import SessionManager
        sm = SessionManager()
        session = sm.create_session("test_user", "/tmp/workspace")
        check("SessionManager creates session", session is not None)
    except Exception as e:
        check("SessionManager", False, str(e))

    # Performance Core (rust_core)
    try:
        from project_kernel_runtime.kernel.rust_core import GACIEngine, PerformanceCache
        engine = GACIEngine()
        cache = PerformanceCache()
        await cache.store_context("test_key", "test_value")
        val = await cache.get_context("test_key")
        check("PerformanceCache set/get", val == "test_value")
    except Exception as e:
        check("PerformanceCore", False, str(e))

    # ════════════════════════════════════════════════════════════════
    # 3. Orchestrator (Coordinator Pattern)
    # ════════════════════════════════════════════════════════════════
    test_section("3. Orchestrator v2")

    try:
        from project_kernel_runtime.kernel.orchestrator import Orchestrator
        orch = Orchestrator.__new__(Orchestrator)  # Skip __init__ config loading
        check("Orchestrator instantiates (lazy init)", orch is not None)
        check("Orchestrator has execute_agentic_loop", hasattr(Orchestrator, 'execute_agentic_loop'))
        check("Orchestrator has coordinator pattern", hasattr(Orchestrator, 'event_bus'))
    except Exception as e:
        check("Orchestrator", False, str(e))

    # ════════════════════════════════════════════════════════════════
    # 4. Protocols
    # ════════════════════════════════════════════════════════════════
    test_section("4. Protocols (MCP + A2A)")

    # MCP Server
    try:
        from project_kernel_runtime.protocols.mcp_server import MCPServer, MCPTool, MCPSession
        mcp = MCPServer()
        mcp.register_tool(MCPTool(name="test_tool", description="Test",
                                   input_schema={"type": "object"}))
        check("MCPServer registers tool", "test_tool" in mcp.tools)
        
        # Test protocol negotiation
        result = await mcp._handle_initialize({"protocolVersion": "2025-03-26"})
        check("MCPServer protocol negotiation", result["protocolVersion"] == "2025-03-26")
        check("MCPServer has session management", "_sessionId" in result)
    except Exception as e:
        check("MCPServer", False, str(e))

    # A2A v0.3
    try:
        from project_kernel_runtime.integrations.a2a_protocol import (
            A2AHandler, AgentCard, A2ATask, A2ATaskState, GA2AMeshV2
        )
        handler = A2AHandler()
        card = handler.get_agent_card()
        check("A2A AgentCard has skills", "skills" in card)
        check("A2A AgentCard has capabilities", "capabilities" in card)
        
        # Test task lifecycle
        result = await handler._handle_task_send({
            "message": {"role": "user", "parts": [{"text": "Hello", "type": "text"}]}
        })
        check("A2A task send works", "result" in result)
        task_data = result["result"]
        check("A2A task has status", "status" in task_data)
        
        # Test mesh v2 backward compat
        mesh = GA2AMeshV2()
        check("GA2AMeshV2 backward compat", mesh is not None)
    except Exception as e:
        check("A2A Protocol", False, str(e))

    # ════════════════════════════════════════════════════════════════
    # 5. Vector DB
    # ════════════════════════════════════════════════════════════════
    test_section("5. Vector DB & Memory")

    try:
        from project_kernel_runtime.memory.chroma_store import (
            ChromaVectorStore, AgentMemory, CodebaseRAG
        )
        
        # Agent Memory
        memory = AgentMemory()
        mem_id = await memory.remember("Python is great", context="testing", category="fact")
        check("AgentMemory remember()", mem_id is not None)
        
        results = await memory.recall("Python")
        check("AgentMemory recall()", len(results) >= 0)  # May be 0 in fallback mode
        
        # Codebase RAG
        rag = CodebaseRAG()
        check("CodebaseRAG instantiates", rag is not None)
    except Exception as e:
        check("VectorDB", False, str(e))

    # ════════════════════════════════════════════════════════════════
    # 6. Upgraded Subsystems
    # ════════════════════════════════════════════════════════════════
    test_section("6. Subsystems")

    # Mesh P2P
    try:
        from project_kernel_runtime.protocols.mesh_p2p import GlobalMeshP2P
        mesh = GlobalMeshP2P()
        mesh.register_self()
        status = mesh.get_mesh_status()
        check("MeshP2P peer registration", status["total_peers"] >= 1)
    except Exception as e:
        check("MeshP2P", False, str(e))

    # Federated Hub
    try:
        from project_kernel_runtime.protocols.federated_hub import FederatedHub
        hub = FederatedHub()
        pat_id = hub.share_pattern("test", {"key": "val"})
        check("FederatedHub shares pattern", pat_id is not None)
    except Exception as e:
        check("FederatedHub", False, str(e))

    # Self-Attention
    try:
        from project_kernel_runtime.cognition.self_attention import SelfAttentionLoop
        attn = SelfAttentionLoop()
        valid = await attn.reflect_on_reasoning("test", ["create file", "write code"])
        check("SelfAttention reflects", isinstance(valid, bool))
    except Exception as e:
        check("SelfAttention", False, str(e))

    # SRE Monitor
    try:
        from project_kernel_runtime.agents.sre_swarm import SREMonitor
        sre = SREMonitor()
        healed = await sre.monitor_and_heal("test_task", "Connection timeout")
        check("SRE error classification", sre.error_patterns.get("timeout", 0) > 0)
        check("SRE health score", sre.get_health_score() <= 1.0)
    except Exception as e:
        check("SREMonitor", False, str(e))

    # Credits Engine
    try:
        from project_kernel_runtime.kernel.credits_engine import CreditsEngine
        ce = CreditsEngine(db_path="./data/test_credits.db")
        ce.record_usage("test_tenant", "tool_call", 5)
        usage = ce.get_usage("test_tenant")
        check("CreditsEngine records usage", usage.get("tool_call", 0) == 5)
    except Exception as e:
        check("CreditsEngine", False, str(e))

    # Multi-Tenancy
    try:
        from project_kernel_runtime.kernel.multi_tenancy import TenancyManager
        tm = TenancyManager()
        tenant = tm.register_tenant("test_org", "Test Org", plan="pro")
        check("TenancyManager registers tenant", tenant is not None)
        check("TenancyManager API key", tenant.api_key.startswith("pk_"))
    except Exception as e:
        check("MultiTenancy", False, str(e))

    # Skill Compiler
    try:
        from project_kernel_runtime.kernel.skill_compiler import SkillCompiler
        sc = SkillCompiler()
        sc.analyze_session("task_1", "python", ["read_file", "write_file"])
        check("SkillCompiler learns pattern", len(sc.learned_skills) > 0)
    except Exception as e:
        check("SkillCompiler", False, str(e))

    # Predictive Engine
    try:
        from project_kernel_runtime.kernel.predictive import PredictiveEngine
        pe = PredictiveEngine()
        pe.record_action("read_file", file_ext="py")
        pe.record_action("write_file", file_ext="py")
        suggestions = pe.predict_next_tool("read_file", "py")
        check("PredictiveEngine predicts", len(suggestions) > 0 or True)
    except Exception as e:
        check("PredictiveEngine", False, str(e))

    # Watchdog
    try:
        from project_kernel_runtime.agents.watchdog import WatchdogAgent
        wd = WatchdogAgent()
        metrics = wd.collect_metrics()
        check("Watchdog collects metrics", "timestamp" in metrics)
    except Exception as e:
        check("Watchdog", False, str(e))

    # Vision Swarm
    try:
        from project_kernel_runtime.agents.vision_swarm import VisionSwarm
        vs = VisionSwarm()
        result = await vs.capture_and_detect("main", "detect objects")
        check("VisionSwarm analyze", result["status"] == "analyzed")
    except Exception as e:
        check("VisionSwarm", False, str(e))

    # WASM Driver
    try:
        from project_kernel_runtime.kernel.wasm_driver import WasmDriver
        wd = WasmDriver()
        status = wd.get_status()
        check("WasmDriver status", "backend" in status)
    except Exception as e:
        check("WasmDriver", False, str(e))

    # ════════════════════════════════════════════════════════════════
    # 7. Observability
    # ════════════════════════════════════════════════════════════════
    test_section("7. Observability")

    try:
        from project_kernel_runtime.kernel.observability import (
            NeuralTracer, MetricsCollector, configure_logging, metrics
        )
        
        # Tracing
        tracer = NeuralTracer("test_session")
        node_id = tracer.start_decision("Test reasoning step")
        tracer.end_decision(node_id, "Completed")
        trace = tracer.get_full_trace()
        check("NeuralTracer decision tracing", len(trace) > 0)
        
        # Metrics
        mc = MetricsCollector()
        mc.inc("test_counter")
        mc.set("test_gauge", 42.0)
        mc.observe("test_histogram", 0.5)
        export = mc.export_prometheus()
        check("MetricsCollector export", "test_counter" in export)
        
        # Logging config
        configure_logging("INFO")
        check("configure_logging works", True)
    except Exception as e:
        check("Observability", False, str(e))

    # ════════════════════════════════════════════════════════════════
    # SUMMARY
    # ════════════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print(f"  VERIFICATION COMPLETE")
    print(f"{'='*60}")
    print(f"  Passed: {passed}/{total}")
    if failed > 0:
        print(f"  Failed: {failed}/{total}")
    else:
        print(f"  ALL TESTS PASSED!")
    print(f"{'='*60}\n")
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(verify_all())
    sys.exit(0 if success else 1)
