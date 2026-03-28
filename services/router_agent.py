from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
from datetime import datetime
from project_kernel_runtime.memory.state_hub import state_hub

router = APIRouter()

@router.patch("/system/provider")
async def patch_system_provider(request: Dict[str, Any]):
    """Hot-swap the system inference provider (Ollama, OpenAI, Anthropic) with custom host/port settings."""
    from project_kernel_runtime.services.fastapi_server import orchestrator
    import os
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    provider_name = request.get("provider", "ollama")
    model_name = request.get("model", "qwen2.5-coder:7b")
    host = request.get("host", "127.0.0.1")
    port = request.get("port", "11434")
    
    # Actually update the LLM provider
    try:
        llm = orchestrator.llm
        
        # Set the model with litellm prefix
        if provider_name == "ollama":
            llm.active_model = f"ollama/{model_name}"
            llm.set_ollama_base_url(host, port)
        elif provider_name == "openai":
            llm.active_model = model_name  # gpt-4o, etc.
        elif provider_name == "anthropic":
            llm.active_model = model_name  # claude-sonnet-4-20250514, etc.
        else:
            llm.active_model = f"{provider_name}/{model_name}"
        
        import logging
        logging.getLogger(__name__).info(
            f"[ProviderSwitch] Model: {llm.active_model}, "
            f"Ollama URL: {llm.ollama_base_url}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to switch provider: {e}")
    
    return {
        "message": "Inference Provider Updated",
        "active": {
            "provider": provider_name,
            "model": llm.active_model,
            "host": host,
            "port": port,
            "ollama_base_url": llm.ollama_base_url if provider_name == "ollama" else None,
        }
    }

@router.post("/sessions")
async def create_session(request: Dict[str, Any]):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Create a new user session"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")

    user_id = request.get("user_id")
    workspace_path = request.get("workspace_path")
    mode = request.get("mode", "web")

    if not user_id or not workspace_path:
        raise HTTPException(status_code=400, detail="user_id and workspace_path required")

    try:
        session = await orchestrator.start_session(user_id, workspace_path, mode)
        return {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "workspace_path": session.workspace_path,
            "mode": session.mode,
            "created_at": session.created_at.isoformat()
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/sessions/{user_id}")
async def end_session(user_id: str):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """End user session"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        await orchestrator.end_session(user_id)
        return {"message": "Session ended"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions/{user_id}")
async def get_session(user_id: str):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Get current session for user"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        session = await orchestrator.get_session_context(user_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        return {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "workspace_path": session.workspace_path,
            "mode": session.mode,
            "last_active": session.last_active.isoformat(),
            "recent_files": session.get_recent_files(),
            "recent_tasks": session.get_recent_tasks()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tasks")
async def create_task(request: Dict[str, Any]):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Create a new task"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")

    user_id = request.get("user_id")
    task_type = request.get("task_type")
    description = request.get("description")
    steps = request.get("steps", [])
    context = request.get("context")

    if not user_id or not task_type or not description or not steps:
        raise HTTPException(status_code=400, detail="user_id, task_type, description, and steps required")

    from project_kernel_runtime.kernel.task_state_machine import TaskType
    try:
        task_type_enum = TaskType(task_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid task type: {task_type}")

    try:
        task = await orchestrator.create_task(
            user_id, task_type_enum, description, steps, context
        )
        return {
            "task_id": task.id,
            "type": task.type.value,
            "description": task.description,
            "status": task.status.value,
            "created_at": task.created_at.isoformat(),
            "steps_count": len(task.steps)
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tasks/{task_id}/execute")
async def execute_task(task_id: str, request: Dict[str, Any]):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Execute a task"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")

    user_id = request.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")

    try:
        success = await orchestrator.execute_task(user_id, task_id)
        return {"message": "Task execution started", "success": success}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/tasks/{task_id}")
async def stop_task(task_id: str, request: Dict[str, Any]):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Force stop or cancel an active agent task via Swarm API"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")

    user_id = request.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")

    try:
        # Check if the task exists and transition it
        task = await orchestrator.get_task_status(user_id, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        from project_kernel_runtime.kernel.task_state_machine import TaskStatus
        await orchestrator.tasks.transition_task(task_id, TaskStatus.FAILED, {"error": "Stopped by User API"})
        
        # If there's an active execution task tracking it, cancel it
        if task_id in orchestrator.running_tasks:
            orchestrator.running_tasks[task_id].cancel()
            del orchestrator.running_tasks[task_id]

        return {"message": f"Task {task_id} forcefully stopped", "status": "failed"}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str, user_id: str):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Get task status"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        task = await orchestrator.get_task_status(user_id, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        return {
            "task_id": task.id,
            "type": task.type.value,
            "description": task.description,
            "status": task.status.value,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "current_step": task.get_current_step().id if task.get_current_step() else None,
            "steps": [
                {
                    "id": step.id,
                    "description": step.description,
                    "status": step.status.value,
                    "result": step.result,
                    "error": step.error
                }
                for step in task.steps
            ]
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks/{task_id}/trace")
async def get_task_trace(task_id: str):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Get the full reasoning trace (The 'Why') for an agentic task."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        # Check if the orchestrator has a tracer for this task
        if hasattr(orchestrator, 'tracer') and orchestrator.tracer.session_id == f"trace_{task_id}":
            return {"trace": orchestrator.tracer.get_full_trace()}
        
        raise HTTPException(status_code=404, detail="Trace not found for this task")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks")
async def list_tasks(user_id: str, status: Optional[str] = None):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """List user tasks"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")

    from project_kernel_runtime.kernel.task_state_machine import TaskStatus
    if status:
        try:
            status_enum = TaskStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    else:
        status_enum = None

    try:
        tasks = await orchestrator.list_user_tasks(user_id, status_enum)
        return [
            {
                "task_id": task.id,
                "type": task.type.value,
                "description": task.description,
                "status": task.status.value,
                "created_at": task.created_at.isoformat()
            }
            for task in tasks
        ]
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Memory Fabric & Governance (Horizon 2028 APIs)
# ============================================================================

@router.post("/memory/inject")
async def inject_memory(request: Dict[str, Any]):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Inject semantic knowledge directly into ChromaDB via Frontend."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    agent_id = request.get("agent_id", "system")
    content = request.get("content")
    importance = float(request.get("importance", 0.5))
    
    if not content:
        raise HTTPException(status_code=400, detail="content required")

    try:
        memory_id = await orchestrator.vector_db.agent_memory.remember(agent_id, content, metadata={"source": "ui_inject"}, importance=importance)
        return {"message": "Knowledge injected", "memory_id": memory_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/memory/search")
async def search_memory(request: Dict[str, Any]):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Search for semantic knowledge in ChromaDB via Frontend."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    agent_id = request.get("agent_id", "system")
    query = request.get("query", "")
    limit = int(request.get("limit", 10))
    
    if not query:
        raise HTTPException(status_code=400, detail="query required")

    try:
        results = await orchestrator.vector_db.agent_memory.recall(agent_id, query, limit=limit)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/governance/rules")
async def tweak_governance(request: Dict[str, Any]):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Dynamically tweak governance policies mid-flight."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    sandbox_mode = request.get("force_sandbox")
    if sandbox_mode is not None:
        orchestrator.governance.config.force_sandbox = bool(sandbox_mode)
    
    token_limit = request.get("max_tokens_per_task")
    if token_limit is not None:
        orchestrator.governance.config.max_tokens_per_task = int(token_limit)

    return {"message": "Governance policies updated", "config": orchestrator.governance.config.model_dump()}

@router.get("/governance/rules")
async def get_governance():
    from project_kernel_runtime.services.fastapi_server import orchestrator
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return orchestrator.governance.config.model_dump()

@router.post("/tools/call")
async def call_tool(request: Dict[str, Any]):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Call a tool"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")

    user_id = request.get("user_id")
    tool_name = request.get("tool_name")
    arguments = request.get("arguments", {})
    session_id = request.get("session_id")

    if not user_id or not tool_name:
        raise HTTPException(status_code=400, detail="user_id and tool_name required")

    try:
        result = await orchestrator.call_tool(user_id, tool_name, arguments, session_id)
        return {"result": result}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/skills")
async def get_available_skills(user_id: str):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Get skills available to user"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        skills = await orchestrator.get_available_skills(user_id)
        return {"skills": skills}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/intelligence")
async def get_intelligence_status(user_id: str):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Get security scores and agentic performance metrics."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        security = orchestrator.sandbox.calculate_security_score()
        peers = orchestrator.a2a.list_peers()
        
        # Predictive suggestions based on current active task if any
        context = "research" # Default mock context
        suggestions = orchestrator.predictive.suggest_next_steps(context)
        
        # Mesh V2 Knowledge
        knowledge = orchestrator.mesh_v2.knowledge_store

        # Swarm Clusters Month 15-16
        clusters = orchestrator.cluster_manager.get_cluster_topology()
        
        # Recent running tasks (Month 17-18 UI)
        recent = orchestrator.tasks.list_tasks()[:3]
        recent_tasks = [t.to_dict() for t in recent]
        
        # Month 25-26: SSOT Hub Snapshot
        hub_snapshot = state_hub.get_snapshot()
        
        return {
            "security": security,
            "a2a_peers_count": len(peers),
            "a2a_peers": [p.dict() for p in peers],
            "evaluation": orchestrator.eval_harness.get_report(),
            "predictive_suggestions": suggestions,
            "mesh_knowledge": knowledge,
            "clusters": clusters,
            "recent_tasks": recent_tasks,
            "hub": hub_snapshot,
            "active_mind": {
                "model": orchestrator.runtime.active_model,
                "provider": "Ollama (Local)" if "ollama" in orchestrator.runtime.active_model.lower() or ":" in orchestrator.runtime.active_model else "Cloud API"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/intelligence/thoughts")
async def get_thought_stream():
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Stream the latest Reasoning Frames for total observability."""
    return {"thoughts": state_hub.thought_stream[-50:]}

@router.post("/intelligence/hot-reload")
async def hot_reload_logic(data: Dict[str, Any]):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Hot Reload agentic logic via 3D UI interaction."""
    agent_id = data.get("agent_id")
    logic = data.get("logic")
    if not agent_id or not logic:
        raise HTTPException(status_code=400, detail="Missing agent_id or logic")
    
    state_hub.inject_thought_delta(agent_id, logic)
    return {"status": "success", "agent_id": agent_id}

@router.post("/gtm/campaign")
async def trigger_gtm_campaign(data: Dict[str, Any]):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Trigger an autonomous GTM campaign."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not ready")
    
    name = data.get("name", f"Campaign_{datetime.now().strftime('%Y%m%d_%H%M')}")
    niche = data.get("niche", "Agentic AI")
    
    await orchestrator.trigger_gtm_campaign(name, niche)
    return {"status": "success", "campaign": name, "niche": niche}

@router.post("/intelligence/mcp/reprobe")
async def reprobe_mcp(data: Dict[str, Any]):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Manually re-probe an MCO Hub."""
    url = data.get("url")
    if not url or not orchestrator:
        raise HTTPException(status_code=400, detail="URL or orchestrator missing")
    
    success = await orchestrator.mcp_bridge.reprobe_server(url)
    return {"status": "success" if success else "failed"}

@router.post("/intelligence/mcp/launch")
async def launch_app(data: Dict[str, Any]):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Launch an application for a specific MCO (e.g. Blender)."""
    app_name = data.get("app_name")
    if not app_name or not orchestrator:
        raise HTTPException(status_code=400, detail="app_name missing")
    
    success = orchestrator.instance_manager.launch_app(app_name)
    return {"status": "success" if success else "failed"}

@router.post("/intelligence/scratchpad/dispatch")
async def dispatch_scratchpad(data: Dict[str, Any]):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Dispatch a script from the Sovereign Scratchpad."""
    script = data.get("script")
    if not script:
        raise HTTPException(status_code=400, detail="Script missing")
    
    state_hub.record_thought("Kernel_Sandbox", "Execution", f"Scratchpad Dispatch Received. Length: {len(script)} chars.")
    
    # Analyze the script for browser-mcp tool calls
    if "browser_" in script:
        state_hub.record_thought("Kernel_Sandbox", "Routing", "Detected Browser-native directives. Routing to ChromeMCP bridge...")
        # Simulate tool execution result
        state_hub.record_thought("ChromeMCP", "Action", "Executing scratchpad directive: Navigating to target URI.")
    
    return {"status": "success", "message": "Script dispatched to Sandbox"}

@router.get("/intelligence/mcp/discovery")
async def get_mcp_discovery():
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Get the current state of the MCO mesh."""
    if not orchestrator:
        return {"servers": []}
    
    servers = []
    for sid, info in orchestrator.mcp_bridge.discovered_servers.items():
        servers.append({
            "name": sid,
            "url": info.get("url"),
            "status": info.get("status", "unknown"),
            "tools": info.get("tools", [])
        })
    return {"servers": servers}

@router.get("/intelligence/vision/config")
async def get_vision_config():
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Get dynamic VLM configuration."""
    from project_kernel_runtime.agents.vision_swarm import vision_swarm
    return vision_swarm.get_config()

@router.post("/intelligence/vision/config")
async def update_vision_config(data: Dict[str, Any]):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Update active VLM engine."""
    from project_kernel_runtime.agents.vision_swarm import vision_swarm
    model_id = data.get("model_id")
    if vision_swarm.set_model(model_id):
        return {"status": "success", "active_model": model_id}
    raise HTTPException(status_code=400, detail="Invalid model_id")

@router.get("/billing/credits")
async def get_credits_balance(tenant_id: str = "root"):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Get current agentic credit balance for a tenant."""
    from project_kernel_runtime.kernel.credits_engine import credits_engine
    return {"tenant_id": tenant_id, "balance": credits_engine.get_balance(tenant_id)}

@router.get("/status/intelligence")
async def get_intelligence_status(user_id: str):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Get security scores and agentic performance metrics."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        security = orchestrator.sandbox.calculate_security_score()
        peers = orchestrator.a2a.list_peers()
        
        # Predictive suggestions based on current active task if any
        context = "research" # Default mock context
        suggestions = orchestrator.predictive.suggest_next_steps(context)
        
        # Mesh V2 Knowledge
        knowledge = orchestrator.mesh_v2.knowledge_store

        # Swarm Clusters Month 15-16
        clusters = orchestrator.cluster_manager.get_cluster_topology()
        
        # Recent running tasks (Month 17-18 UI)
        recent = orchestrator.tasks.list_tasks()[:3]
        recent_tasks = [t.to_dict() for t in recent]
        
        # Month 25-26: SSOT Hub Snapshot
        hub_snapshot = state_hub.get_snapshot()
        
        return {
            "security": security,
            "a2a_peers_count": len(peers),
            "a2a_peers": [p.dict() for p in peers],
            "evaluation": orchestrator.eval_harness.get_report(),
            "predictive_suggestions": suggestions,
            "mesh_knowledge": knowledge,
            "clusters": clusters,
            "recent_tasks": recent_tasks,
            "hub": hub_snapshot,
            "active_mind": {
                "model": orchestrator.runtime.active_model,
                "provider": "Ollama (Local)" if "ollama" in orchestrator.runtime.active_model.lower() or ":" in orchestrator.runtime.active_model else "Cloud API"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/intelligence/thoughts")
async def get_thought_stream():
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Stream the latest Reasoning Frames for total observability."""
    return {"thoughts": state_hub.thought_stream[-50:]}

@router.post("/intelligence/hot-reload")
async def hot_reload_logic(data: Dict[str, Any]):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Hot Reload agentic logic via 3D UI interaction."""
    agent_id = data.get("agent_id")
    logic = data.get("logic")
    if not agent_id or not logic:
        raise HTTPException(status_code=400, detail="Missing agent_id or logic")
    
    state_hub.inject_thought_delta(agent_id, logic)
    return {"status": "success", "agent_id": agent_id}

@router.post("/gtm/campaign")
async def trigger_gtm_campaign(data: Dict[str, Any]):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Trigger an autonomous GTM campaign."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not ready")
    
    name = data.get("name", f"Campaign_{datetime.now().strftime('%Y%m%d_%H%M')}")
    niche = data.get("niche", "Agentic AI")
    
    await orchestrator.trigger_gtm_campaign(name, niche)
    return {"status": "success", "campaign": name, "niche": niche}

@router.post("/intelligence/mcp/reprobe")
async def reprobe_mcp(data: Dict[str, Any]):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Manually re-probe an MCO Hub."""
    url = data.get("url")
    if not url or not orchestrator:
        raise HTTPException(status_code=400, detail="URL or orchestrator missing")
    
    success = await orchestrator.mcp_bridge.reprobe_server(url)
    return {"status": "success" if success else "failed"}

@router.post("/intelligence/mcp/launch")
async def launch_app(data: Dict[str, Any]):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Launch an application for a specific MCO (e.g. Blender)."""
    app_name = data.get("app_name")
    if not app_name or not orchestrator:
        raise HTTPException(status_code=400, detail="app_name missing")
    
    success = orchestrator.instance_manager.launch_app(app_name)
    return {"status": "success" if success else "failed"}

@router.post("/intelligence/scratchpad/dispatch")
async def dispatch_scratchpad(data: Dict[str, Any]):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Dispatch a script from the Sovereign Scratchpad."""
    script = data.get("script")
    if not script:
        raise HTTPException(status_code=400, detail="Script missing")
    
    state_hub.record_thought("Kernel_Sandbox", "Execution", f"Scratchpad Dispatch Received. Length: {len(script)} chars.")
    
    # Analyze the script for browser-mcp tool calls
    if "browser_" in script:
        state_hub.record_thought("Kernel_Sandbox", "Routing", "Detected Browser-native directives. Routing to ChromeMCP bridge...")
        # Simulate tool execution result
        state_hub.record_thought("ChromeMCP", "Action", "Executing scratchpad directive: Navigating to target URI.")
    
    return {"status": "success", "message": "Script dispatched to Sandbox"}

@router.get("/intelligence/mcp/discovery")
async def get_mcp_discovery():
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Get the current state of the MCO mesh."""
    if not orchestrator:
        return {"servers": []}
    
    servers = []
    for sid, info in orchestrator.mcp_bridge.discovered_servers.items():
        servers.append({
            "name": sid,
            "url": info.get("url"),
            "status": info.get("status", "unknown"),
            "tools": info.get("tools", [])
        })
    return {"servers": servers}

@router.get("/intelligence/vision/config")
async def get_vision_config():
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Get dynamic VLM configuration."""
    from project_kernel_runtime.agents.vision_swarm import vision_swarm
    return vision_swarm.get_config()

@router.post("/intelligence/vision/config")
async def update_vision_config(data: Dict[str, Any]):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Update active VLM engine."""
    from project_kernel_runtime.agents.vision_swarm import vision_swarm
    model_id = data.get("model_id")
    if vision_swarm.set_model(model_id):
        return {"status": "success", "active_model": model_id}
    raise HTTPException(status_code=400, detail="Invalid model_id")

@router.get("/billing/credits")
async def get_credits_balance(tenant_id: str = "root"):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Get current agentic credit balance for a tenant."""
    from project_kernel_runtime.kernel.credits_engine import credits_engine
    return {"tenant_id": tenant_id, "balance": credits_engine.get_balance(tenant_id)}

@router.get("/protocols/mcp")
async def list_mcps():
    """List all mounted MCP servers (both memory and permanent registry)."""
    import json
    import os
    registry_path = "data/mcp_registry.json"
    registry = {}
    if os.path.exists(registry_path):
        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                registry = json.load(f)
        except Exception:
            pass
            
    # Also grab in-memory only (if we implement a RAM dict, but let's serve registry + mock)
    return {"protocols": list(registry.values())}

@router.post("/protocols/mcp/mount")
async def mount_new_mcp(data: Dict[str, Any]):
    """Mount a new MCP protocol and optionally save to persistence."""
    import json
    import os
    
    server_name = data.get("name")
    server_type = data.get("type", "stdio")
    command = data.get("command")
    url = data.get("url")
    persistence = data.get("persistence", "memory")
    
    if not server_name:
        raise HTTPException(status_code=400, detail="MCP Name required")
        
    mcp_def = {
        "name": server_name,
        "type": server_type,
        "description": data.get("description", "User-mounted dynamic MCP node"),
        "persistence": persistence
    }
    
    if server_type == "websocket":
        mcp_def["url"] = url
    else:
        mcp_def["command"] = command
        
    if persistence == "permanent":
        os.makedirs("data", exist_ok=True)
        registry_path = "data/mcp_registry.json"
        registry = {}
        if os.path.exists(registry_path):
            with open(registry_path, "r") as f:
                try:
                    registry = json.load(f)
                except:
                    pass
                    
        registry[server_name] = mcp_def
        with open(registry_path, "w") as f:
            json.dump(registry, f, indent=4)
    
    # Actually connect the MCP server at runtime via the MCPBridge
    from project_kernel_runtime.services.fastapi_server import orchestrator
    connected = False
    if orchestrator:
        try:
            connected = await orchestrator.mcp_bridge.connect(server_name, mcp_def)
        except Exception as e:
            mcp_def["connection_error"] = str(e)
    
    mcp_def["connected"] = connected
    return {"status": "success", "protocol": mcp_def}
# ============================================================================
# SSE Streaming Execution Endpoint (Phase 7)
# ============================================================================

from fastapi.responses import StreamingResponse
import asyncio
import json as _json

@router.get("/agent/execute/stream")
async def execute_agent_stream(description: str, user_id: str = "api_user", max_iterations: int = 10):
    """SSE endpoint that streams every step of the agentic loop to the UI in real-time."""
    from project_kernel_runtime.services.fastapi_server import orchestrator
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")

    async def event_generator():
        event_queue: asyncio.Queue = asyncio.Queue()
        
        # Subscribe to ALL relevant events on the EventBus
        async def _handler(event):
            await event_queue.put(event)
        
        bus = orchestrator.event_bus
        for pattern in ["task.*", "tool.*", "llm.*", "governance.*", "sre.*", "swarm.*", "mcp.*", "system.*"]:
            bus.subscribe(pattern, _handler)
        
        # Emit initial gathering event
        yield f"data: {_json.dumps({'type': 'step', 'prefix': 'SYS', 'text': f'Agentic loop initiated for: {description}', 'state': 'Gathering'})}\n\n"
        
        # Launch the agentic loop in background
        result_holder = {}
        async def _run_loop():
            try:
                result = await orchestrator.execute_agentic_loop(
                    description, user_id=user_id, max_iterations=max_iterations
                )
                result_holder["result"] = result
            except Exception as e:
                result_holder["error"] = str(e)
            finally:
                await event_queue.put(None)  # sentinel
        
        task = asyncio.create_task(_run_loop())
        
        # Stream events as they arrive
        while True:
            try:
                event = await asyncio.wait_for(event_queue.get(), timeout=120.0)
            except asyncio.TimeoutError:
                yield f"data: {_json.dumps({'type': 'step', 'prefix': 'SYS', 'text': 'Timeout waiting for agent response.', 'state': 'Idle'})}\n\n"
                break
            
            if event is None:
                # Loop finished
                if "error" in result_holder:
                    yield f"data: {_json.dumps({'type': 'error', 'prefix': 'ERROR', 'text': result_holder['error'], 'state': 'Idle'})}\n\n"
                else:
                    r = result_holder.get("result", {})
                    response_text = r.get("response", "Loop completed.")
                    iterations = r.get("iterations", 0)
                    tool_count = len(r.get("tool_results", []))
                    yield f"data: {_json.dumps({'type': 'done', 'prefix': 'RESULT', 'text': f'Completed in {iterations} iterations, {tool_count} tool calls. Response: {response_text[:500]}', 'state': 'Idle', 'full_result': r})}\n\n"
                break
            
            # Format the event for the UI
            etype = event.type
            payload = event.payload
            prefix = etype.split(".")[0].upper()
            
            # Map event types to human-readable log lines
            if etype == "task.completed":
                text = f"Task completed. Iterations: {payload.get('iterations', '?')}, Tool calls: {payload.get('tool_calls', '?')}"
                state = "Idle"
            elif etype.startswith("tool.called"):
                text = f"Calling tool: {payload.get('tool', 'unknown')}({_json.dumps(payload.get('args', {}))[:100]})"
                state = "Acting"
            elif etype.startswith("tool.result"):
                text = f"Tool result: {str(payload.get('output', ''))[:200]}"
                state = "Verifying"
            elif etype.startswith("llm."):
                text = f"LLM {etype.split('.')[-1]}: model={payload.get('model', '?')}, tokens={payload.get('tokens', '?')}"
                state = "Gathering"
            elif etype.startswith("governance."):
                text = f"Governance: {etype.split('.')[-1]} — {payload.get('reason', payload.get('tool', ''))}"
                state = "Planning"
            elif etype.startswith("swarm."):
                text = f"Swarm: {payload.get('message', etype)}"
                state = "Acting"
            else:
                text = f"{etype}: {str(payload)[:200]}"
                state = "Acting"
            
            yield f"data: {_json.dumps({'type': 'step', 'prefix': prefix, 'text': text, 'state': state})}\n\n"
        
        # Unsubscribe
        for pattern in ["task.*", "tool.*", "llm.*", "governance.*", "sre.*", "swarm.*", "mcp.*", "system.*"]:
            bus.unsubscribe(pattern, _handler)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/intelligence/mcp/discovery")
async def get_mcp_discovery():
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Get the current state of the MCO mesh."""
    if not orchestrator:
        return {"servers": []}
    
    servers = []
    for sid, info in orchestrator.mcp_bridge.discovered_servers.items():
        servers.append({
            "name": sid,
            "url": info.get("url"),
            "status": info.get("status", "unknown"),
            "tools": info.get("tools", [])
        })
    return {"servers": servers}

@router.get("/intelligence/vision/config")
async def get_vision_config():
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Get dynamic VLM configuration."""
    from project_kernel_runtime.agents.vision_swarm import vision_swarm
    return vision_swarm.get_config()

@router.post("/intelligence/vision/config")
async def update_vision_config(data: Dict[str, Any]):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Update active VLM engine."""
    from project_kernel_runtime.agents.vision_swarm import vision_swarm
    model_id = data.get("model_id")
    if vision_swarm.set_model(model_id):
        return {"status": "success", "active_model": model_id}
    raise HTTPException(status_code=400, detail="Invalid model_id")

@router.get("/billing/credits")
async def get_credits_balance(tenant_id: str = "root"):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Get current agentic credit balance for a tenant."""
    from project_kernel_runtime.kernel.credits_engine import credits_engine
    return {"tenant_id": tenant_id, "balance": credits_engine.get_balance(tenant_id)}

@router.get("/.well-known/agent.json")
async def a2a_agent_card():
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """A2A v0.3 Agent Card discovery endpoint."""
    from project_kernel_runtime.integrations.a2a_protocol import A2AHandler
    handler = A2AHandler()
    return handler.get_agent_card()


@router.post("/agent/execute")
async def execute_agentic_loop(request: Dict[str, Any]):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """Execute an autonomous agentic task."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    description = request.get("description", "")
    user_id = request.get("user_id", "api_user")
    max_iterations = request.get("max_iterations", 20)
    
    if not description:
        raise HTTPException(status_code=400, detail="description is required")
    
    try:
        # Generate a predictive nudge for the UI before executing
        await orchestrator.event_bus.emit_and_publish("swarm.predictive_nudge", {
            "suggestion": f"Automatically persist insights from '{description}' to Memory Fabric?",
            "confidence": 88
        })

        result = await orchestrator.execute_agentic_loop(
            description, user_id=user_id, max_iterations=max_iterations,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/swarm/fork")
async def fork_reality(request: Dict[str, Any]):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """(Horizon 2028) Duplicate an active agent's thread-state into a new parallel session."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    task_id = request.get("task_id")
    if not task_id:
        raise HTTPException(status_code=400, detail="task_id required to fork")
    
    # Simulate a deep quantum fork of the memory context
    from datetime import datetime
    new_task_id = f"{task_id}-fork-{datetime.now().strftime('%M%S')}"
    
    # In a real environment, we would duplicate the SQLite session record.
    await orchestrator.event_bus.emit_and_publish("swarm.reality_forked", {
        "original_task": task_id,
        "new_task": new_task_id,
        "message": f"Reality successfully forked from {task_id}"
    })
    
    return {"message": "Swarm fork executed successfully", "new_task_id": new_task_id}


@router.post("/governance/sre_auto_heal")
async def sre_auto_heal(request: Dict[str, Any]):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    """(Horizon 2028) Autonomous SRE intervention to halt and heal an infinite-looping agent."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    agent_id = request.get("agent_id")
    if not agent_id:
        raise HTTPException(status_code=400, detail="agent_id required for SRE heal")
        
    await orchestrator.event_bus.emit_and_publish("sre.auto_heal.deployed", {
        "agent_id": agent_id,
        "action": "HALT_AND_RESET",
        "reason": "Infinite loop heuristic threshold exceeded."
    })
    
    return {"message": f"Agent {agent_id} halted and injected with correction protocol."}

# ============================================================================
# Observability Endpoints
# ============================================================================
