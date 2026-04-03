import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse

from project_kernel_runtime.kernel.credits_engine import credits_engine
from project_kernel_runtime.kernel.task_state_machine import TaskStatus, TaskStep, TaskType
from project_kernel_runtime.memory.state_hub import state_hub
from project_kernel_runtime.services.project_registry import build_project_registry, session_payload

router = APIRouter()

_session_byok: Dict[str, Dict[str, str]] = {}


def _get_orchestrator():
    from project_kernel_runtime.services.fastapi_server import orchestrator

    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return orchestrator


def _session_payload(session) -> Dict[str, Any]:
    return session_payload(session)


def _task_payload(task) -> Dict[str, Any]:
    return {
        "task_id": task.id,
        "id": task.id,
        "type": task.type.value if hasattr(task.type, "value") else str(task.type),
        "description": task.description,
        "status": task.status.value if hasattr(task.status, "value") else str(task.status),
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
        "session_id": task.session_id,
        "error": task.error,
        "progress": task.progress,
        "result": {"response": task.steps[0].result if task.steps and task.steps[0].result else ""},
        "response": task.steps[0].result if task.steps and task.steps[0].result else "",  # Direct field for UI
        "steps": [
            {
                "id": step.id,
                "description": step.description,
                "status": step.status.value if hasattr(step.status, "value") else str(step.status),
                "result": jsonable_encoder(step.result),
                "error": step.error,
            }
            for step in task.steps
        ],
    }


def _tool_result_payload(result) -> Dict[str, Any]:
    output = jsonable_encoder(result.output)
    embedded_error = output.get("error") if isinstance(output, dict) else None
    return {
        "tool_call_id": result.tool_call_id,
        "tool_name": result.tool_name,
        "success": bool(result.success and not embedded_error),
        "output": output,
        "error": result.error or embedded_error,
        "duration_ms": result.duration_ms,
        "metadata": jsonable_encoder(result.metadata),
    }


async def _resolve_session(orchestrator, identifier: Optional[str], user_id: Optional[str]) -> Optional[Any]:
    if identifier:
        session = await orchestrator.get_session_context(identifier)
        if session:
            return session
    if user_id:
        session = await orchestrator.get_session_context(user_id)
        if session:
            return session
    return None


async def _run_agent_task(orchestrator, task, user_id: str, session_id: str, description: str, max_iterations: int, context_bindings: Dict[str, Any] = None):
    try:
        state_hub.update_task_state(task.id, "running")
        result = await orchestrator.execute_agentic_loop(
            description,
            user_id=user_id,
            session_id=session_id,
            max_iterations=max_iterations,
            context_bindings=context_bindings
        )
        # Store just the response string in step result, not the full dict
        task.complete_step(result.get("response", ""))
        task.status = TaskStatus.COMPLETED
        task.updated_at = datetime.now(task.updated_at.tzinfo)
        orchestrator.tasks.save_task(task)
        state_hub.update_task_state(task.id, "completed", result)
    except Exception as exc:
        task.fail_step(str(exc))
        task.status = TaskStatus.FAILED
        task.updated_at = datetime.now(task.updated_at.tzinfo)
        orchestrator.tasks.save_task(task)
        state_hub.update_task_state(task.id, "failed", {"error": str(exc)})
    finally:
        orchestrator.running_tasks.pop(task.id, None)


@router.post("/sessions")
async def create_session(request: Dict[str, Any]):
    orchestrator = _get_orchestrator()

    user_id = request.get("user_id")
    workspace_path = request.get("workspace_path", "")
    mode = request.get("mode", "web")

    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")

    session = await orchestrator.start_session(user_id, workspace_path, mode)
    project_registry = build_project_registry(orchestrator=orchestrator)
    session.skills = []
    session.mcp_servers = []
    session.folders = []
    session.a2a_enabled = False 
    session.a2a_peers = []
    orchestrator.sessions.update_session(session.session_id, session)
    return _session_payload(session)


@router.get("/sessions")
async def list_sessions():
    orchestrator = _get_orchestrator()
    sessions = [_session_payload(session) for session in orchestrator.sessions.sessions.values() if session.is_active]
    sessions.sort(key=lambda item: item["created_at"], reverse=True)
    return {"sessions": sessions}


@router.get("/sessions/{identifier}")
async def get_session(identifier: str):
    orchestrator = _get_orchestrator()
    session = await orchestrator.get_session_context(identifier)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return _session_payload(session)


@router.delete("/sessions/{session_id}")
async def end_session(session_id: str):
    orchestrator = _get_orchestrator()
    session = orchestrator.sessions.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    orchestrator.sessions.end_session(session_id)
    orchestrator.active_sessions.pop(session.user_id, None)
    return {"message": "Session ended", "session_id": session_id}


@router.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str):
    orchestrator = _get_orchestrator()
    session = orchestrator.sessions.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    history = getattr(session, "conversation_messages", [])
    return {"session_id": session_id, "history": history, "messages": history, "total": len(history)}


@router.patch("/sessions/{session_id}")
async def patch_session(session_id: str, request: Dict[str, Any]):
    orchestrator = _get_orchestrator()
    session = orchestrator.sessions.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if "skills" in request:
        session.skills = list(dict.fromkeys(request.get("skills", [])))
    if "mcp_servers" in request:
        session.mcp_servers = list(dict.fromkeys(request.get("mcp_servers", [])))
    if "folders" in request:
        session.folders = list(dict.fromkeys(request.get("folders", [])))
    if "user_role" in request and request["user_role"]:
        session.user_role = request["user_role"]
    if "a2a_enabled" in request:
        session.a2a_enabled = bool(request["a2a_enabled"])
    if "a2a_peers" in request:
        session.a2a_peers = list(dict.fromkeys(request.get("a2a_peers", [])))
    if "mode" in request and request["mode"]:
        session.mode = request["mode"]
    if "risk_mode" in request and request["risk_mode"]:
        session.risk_mode = request["risk_mode"]

    orchestrator.sessions.update_session(session_id, session)
    return _session_payload(session)


@router.get("/sessions/{session_id}/governance")
async def get_session_governance(session_id: str):
    orchestrator = _get_orchestrator()
    session = orchestrator.sessions.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session_id,
        "user_role": getattr(session, "user_role", "developer"),
        "risk_mode": getattr(session, "risk_mode", "auto"),
        "skills": getattr(session, "skills", []),
        "mcp_servers": getattr(session, "mcp_servers", []),
        "folders": getattr(session, "folders", []),
        "a2a_enabled": getattr(session, "a2a_enabled", False),
        "a2a_peers": getattr(session, "a2a_peers", []),
    }


@router.put("/sessions/{session_id}/governance")
async def put_session_governance(session_id: str, request: Dict[str, Any]):
    return await patch_session(session_id, request)


@router.post("/sessions/{session_id}/mode")
async def set_session_mode(session_id: str, payload: Dict[str, Any]):
    orchestrator = _get_orchestrator()
    session = orchestrator.sessions.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    mode = payload.get("mode", "web")
    session.mode = mode
    orchestrator.sessions.update_session(session_id, session)
    return {"session_id": session_id, "mode": mode}


@router.get("/sessions/{session_id}/skills")
async def get_session_skills(session_id: str):
    orchestrator = _get_orchestrator()
    session = orchestrator.sessions.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session_skills = getattr(session, "skills", [])
    # Debug: get tools for these skills
    tools = []
    for skill_name in session_skills:
        try:
            skill_tools = orchestrator.skills.get_tools_for_skill(skill_name)
            if skill_tools:
                tools.extend(skill_tools)
        except Exception:
            pass
    return {
        "session_id": session_id, 
        "skills": session_skills,
        "available_tools": tools
    }


@router.post("/sessions/{session_id}/skills")
async def set_session_skills(session_id: str, payload: Dict[str, Any]):
    orchestrator = _get_orchestrator()
    session = orchestrator.sessions.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.skills = list(dict.fromkeys(payload.get("skills", [])))
    orchestrator.sessions.update_session(session_id, session)
    return {"session_id": session_id, "skills": session.skills}


@router.post("/sessions/{session_id}/byok")
async def set_session_byok(session_id: str, payload: Dict[str, Any]):
    provider = payload.get("provider", "")
    api_key = payload.get("api_key", "")
    if not provider or not api_key:
        raise HTTPException(status_code=400, detail="provider and api_key required")

    _session_byok.setdefault(session_id, {})[provider] = api_key
    return {
        "session_id": session_id,
        "provider": provider,
        "set": True,
        "masked_key": api_key[:8] + "..." + api_key[-4:],
    }


@router.get("/sessions/{session_id}/byok")
async def get_session_byok(session_id: str):
    keys = _session_byok.get(session_id, {})
    return {
        "session_id": session_id,
        "providers": {provider: value[:8] + "..." + value[-4:] for provider, value in keys.items()},
    }


@router.post("/tasks")
async def create_task(request: Dict[str, Any]):
    orchestrator = _get_orchestrator()

    description = request.get("description", "").strip()
    if not description:
        raise HTTPException(status_code=400, detail="description required")

    session = await _resolve_session(
        orchestrator,
        request.get("session_id"),
        request.get("user_id"),
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    raw_task_type = request.get("task_type", TaskType.CUSTOM.value)
    try:
        task_type = TaskType(raw_task_type)
    except ValueError:
        task_type = TaskType.CUSTOM

    task = orchestrator.tasks.create_task(
        type=task_type,
        description=description,
        steps=[TaskStep(id="agent_loop", description=description, tools=[])],
        context=request.get("context", {}),
        session_id=session.session_id,
    )
    orchestrator.sessions.add_task_to_session(session.session_id, task.id)
    orchestrator.sessions.add_message_to_session(session.session_id, "user", description)
    state_hub.update_task_state(task.id, "queued", {"session_id": session.session_id})

    max_iterations = int(request.get("max_iterations", 8))
    background = asyncio.create_task(
        _run_agent_task(
            orchestrator,
            task,
            session.user_id,
            session.session_id,
            description,
            max_iterations,
        )
    )
    orchestrator.running_tasks[task.id] = background

    return _task_payload(task)


@router.post("/tasks/{task_id}/execute")
async def execute_task(task_id: str, request: Dict[str, Any]):
    orchestrator = _get_orchestrator()
    task = orchestrator.tasks.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task_id in orchestrator.running_tasks and not orchestrator.running_tasks[task_id].done():
        return {"message": "Task already running", "task_id": task_id, "status": "running"}

    session = orchestrator.sessions.get_session(task.session_id) if task.session_id else None
    if not session:
        raise HTTPException(status_code=404, detail="Task session not found")

    background = asyncio.create_task(
        _run_agent_task(
            orchestrator,
            task,
            session.user_id,
            session.session_id,
            task.description,
            int(request.get("max_iterations", 8)),
        )
    )
    orchestrator.running_tasks[task.id] = background
    return {"message": "Task execution started", "task_id": task_id, "status": "running"}


@router.delete("/tasks/{task_id}")
async def stop_task(task_id: str):
    orchestrator = _get_orchestrator()
    task = orchestrator.tasks.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    running = orchestrator.running_tasks.pop(task_id, None)
    if running and not running.done():
        running.cancel()

    await orchestrator.tasks.transition_task(task_id, TaskStatus.CANCELLED, {"error": "Cancelled by user"})
    state_hub.update_task_state(task_id, "cancelled")
    return {"message": f"Task {task_id} cancelled", "status": "cancelled"}


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    orchestrator = _get_orchestrator()
    task = orchestrator.tasks.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_payload(task)


@router.get("/tasks/{task_id}/trace")
async def get_task_trace(task_id: str):
    orchestrator = _get_orchestrator()
    task = orchestrator.tasks.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    events = [
        {
            "type": event.type,
            "timestamp": event.timestamp.isoformat(),
            "payload": jsonable_encoder(event.payload),
        }
        for event in orchestrator.event_bus.get_event_log(last_n=200)
        if event.task_id == task_id
    ]
    return {"task_id": task_id, "events": events}


@router.get("/tasks")
async def list_tasks(user_id: Optional[str] = None, status: Optional[str] = None):
    orchestrator = _get_orchestrator()
    task_status = TaskStatus(status) if status else None

    if user_id:
        session = await orchestrator.get_session_context(user_id)
        if session:
            tasks = orchestrator.tasks.list_tasks(status=task_status, session_id=session.session_id)
        else:
            tasks = []
    else:
        tasks = orchestrator.tasks.list_tasks(status=task_status)

    return [_task_payload(task) for task in tasks]


@router.post("/memory/inject")
async def inject_memory(request: Dict[str, Any]):
    orchestrator = _get_orchestrator()
    content = request.get("content", "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="content required")

    memory_id = await orchestrator.vector_db.agent_memory.remember(
        content=content,
        context=request.get("context", ""),
        task_id=request.get("task_id", ""),
        category=request.get("category", "general"),
    )
    return {"message": "Knowledge injected", "memory_id": memory_id}


@router.post("/memory/search")
async def search_memory(request: Dict[str, Any]):
    orchestrator = _get_orchestrator()
    query = request.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query required")

    results = await orchestrator.vector_db.agent_memory.recall(
        query=query,
        limit=int(request.get("limit", 10)),
        category=request.get("category"),
    )
    return {"results": [result.to_dict() for result in results]}


@router.post("/sessions/{session_id}/terminal")
async def run_session_terminal(session_id: str, request: Dict[str, Any]):
    orchestrator = _get_orchestrator()
    session = orchestrator.sessions.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    command = request.get("command", "").strip()
    if not command:
        raise HTTPException(status_code=400, detail="command required")

    result = await orchestrator.call_tool(
        session.user_id,
        "bash_execute",
        {
            "command": command,
            "cwd": request.get("cwd") or (getattr(session, "folders", [])[:1] or [session.workspace_path])[0],
            "timeout": int(request.get("timeout", 30)),
        },
        session_id=session_id,
    )
    orchestrator.sessions.add_command_to_session(session_id, command)
    return {"result": _tool_result_payload(result)}


@router.put("/sessions/{session_id}/workspace/file")
async def save_session_file(session_id: str, request: Dict[str, Any]):
    orchestrator = _get_orchestrator()
    session = orchestrator.sessions.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    path = request.get("path", "").strip()
    if not path:
        raise HTTPException(status_code=400, detail="path required")

    result = await orchestrator.call_tool(
        session.user_id,
        "write_file",
        {"path": path, "content": request.get("content", "")},
        session_id=session_id,
    )
    if result.success:
        orchestrator.sessions.add_file_to_session(session_id, path)
    return {"result": _tool_result_payload(result)}


@router.post("/governance/rules")
async def tweak_governance(request: Dict[str, Any]):
    orchestrator = _get_orchestrator()
    governance = orchestrator.config.governance

    for key in ("default_role", "enabled", "require_approval_for", "network_allowlist"):
        if key in request:
            setattr(governance, key, request[key])
    return {"message": "Governance policies updated", "config": governance.model_dump()}


@router.get("/governance/rules")
async def get_governance():
    orchestrator = _get_orchestrator()
    return orchestrator.config.governance.model_dump()


@router.post("/tools/call")
async def call_tool(request: Dict[str, Any]):
    orchestrator = _get_orchestrator()

    session = await _resolve_session(
        orchestrator,
        request.get("session_id"),
        request.get("user_id"),
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    tool_name = request.get("tool_name", "").strip()
    if not tool_name:
        raise HTTPException(status_code=400, detail="tool_name required")

    result = await orchestrator.call_tool(
        session.user_id,
        tool_name,
        request.get("arguments", {}),
        session.session_id,
    )
    return {"result": _tool_result_payload(result)}


@router.get("/skills")
async def get_available_skills(user_id: Optional[str] = None):
    orchestrator = _get_orchestrator()
    skills = await orchestrator.get_available_skills(user_id or "anonymous")
    return {"skills": skills}


@router.get("/status/intelligence")
async def get_intelligence_status(user_id: Optional[str] = Query(default=None)):
    orchestrator = _get_orchestrator()
    session = await orchestrator.get_session_context(user_id) if user_id else None

    recent_tasks = orchestrator.tasks.list_tasks(
        session_id=session.session_id if session else None
    )[:5]
    memory_count = getattr(orchestrator.vector_db.agent_memory.store, "count", 0)
    memory_count = memory_count() if callable(memory_count) else memory_count

    return {
        "runtime": {
            "version": getattr(orchestrator.config, "version", "2.0.0"),
            "mode": getattr(orchestrator.config, "mode", "development"),
        },
        "session": _session_payload(session) if session else None,
        "security": orchestrator.sandbox.calculate_security_score(),
        "llm": orchestrator.llm.get_usage_stats(),
        "mcp": orchestrator.mcp_bridge.get_status(),
        "mesh": orchestrator.mesh_p2p.get_mesh_status(),
        "memory": {"stored_items": memory_count},
        "tasks": [_task_payload(task) for task in recent_tasks],
        "snapshot": state_hub.get_snapshot(),
    }


@router.get("/billing/credits")
async def get_credits_balance(tenant_id: str = "root"):
    return {
        "tenant_id": tenant_id,
        "balance": credits_engine.get_balance(tenant_id),
        "usage": credits_engine.get_usage(tenant_id),
        "report": credits_engine.get_report(tenant_id),
    }


@router.get("/protocols/mcp")
async def list_mcps():
    orchestrator = _get_orchestrator()
    registry_path = Path(__file__).resolve().parent.parent / "data" / "mcp_registry.json"
    registry = {}
    if registry_path.exists():
        try:
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
        except Exception:
            registry = {}

    return {
        "protocols": list(registry.values()),
        "bridge": orchestrator.mcp_bridge.get_status(),
    }


@router.post("/dispatch")
async def dispatch_task(request: Dict[str, Any]):
    orchestrator = _get_orchestrator()
    session_id = request.get("session_id")
    task_description = request.get("input", "").strip()
    context_bindings = request.get("context_bindings", {})

    if not session_id or not task_description:
        raise HTTPException(status_code=400, detail="session_id and input required")

    session = orchestrator.sessions.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Create Task
    task = orchestrator.tasks.create_task(
        type=TaskType.RESEARCH,
        description=task_description,
        steps=[TaskStep(id="agent_loop", description=task_description, tools=[])],
        context=context_bindings,
        session_id=session_id,
    )
    orchestrator.sessions.add_task_to_session(session_id, task.id)
    orchestrator.sessions.add_message_to_session(session_id, "user", task_description)

    # Start Background Loop
    asyncio.create_task(_run_agent_task(
        orchestrator,
        task,
        session.user_id,
        session_id,
        task_description,
        max_iterations=int(request.get("max_iterations", 10)),
        context_bindings=context_bindings
    ))

    return {"task_id": task.id, "status": "dispatched"}


@router.post("/governance/approve/{approval_id}")
async def approve_governance(approval_id: str):
    orchestrator = _get_orchestrator()
    success = await orchestrator.governance.resolve_approval(approval_id, approved=True)
    if not success:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return {"status": "approved"}


@router.post("/governance/deny/{approval_id}")
async def deny_governance(approval_id: str):
    orchestrator = _get_orchestrator()
    success = await orchestrator.governance.resolve_approval(approval_id, approved=False)
    if not success:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return {"status": "denied"}


@router.post("/protocols/mcp/mount")
async def mount_new_mcp(payload: Dict[str, Any]):
    orchestrator = _get_orchestrator()

    name = payload.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name required")

    config = {
        "type": payload.get("type", "stdio"),
        "command": payload.get("command", ""),
        "url": payload.get("url", ""),
        "args": payload.get("args", []),
        "persistence": payload.get("persistence", "permanent"),
    }
    if not config["command"] and not config["url"]:
        raise HTTPException(status_code=400, detail="command or url required")

    registry_path = Path(__file__).resolve().parent.parent / "data" / "mcp_registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if registry_path.exists():
        try:
            existing = json.loads(registry_path.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
    existing[name] = config
    registry_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    connected = await orchestrator.mcp_bridge.connect(name, config)
    return {"status": "success", "protocol": {"name": name, **config, "connected": connected}}


@router.get("/agent/execute/stream")
async def execute_agent_stream(
    description: str,
    user_id: str = "api_user",
    session_id: Optional[str] = None,
    max_iterations: int = 10,
):
    orchestrator = _get_orchestrator()

    async def event_generator():
        yield "data: " + json.dumps({"type": "start", "description": description}) + "\n\n"
        try:
            result = await orchestrator.execute_agentic_loop(
                description,
                user_id=user_id,
                session_id=session_id,
                max_iterations=max_iterations,
            )
            yield "data: " + json.dumps({"type": "done", "result": jsonable_encoder(result)}) + "\n\n"
        except Exception as exc:
            yield "data: " + json.dumps({"type": "error", "error": str(exc)}) + "\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/agent/execute")
async def execute_agentic_loop(request: Dict[str, Any]):
    orchestrator = _get_orchestrator()

    description = request.get("description", "").strip()
    if not description:
        raise HTTPException(status_code=400, detail="description is required")

    session = await _resolve_session(
        orchestrator,
        request.get("session_id"),
        request.get("user_id"),
    )
    user_id = session.user_id if session else request.get("user_id", "api_user")
    session_id = session.session_id if session else request.get("session_id")

    result = await orchestrator.execute_agentic_loop(
        description,
        user_id=user_id,
        session_id=session_id,
        max_iterations=int(request.get("max_iterations", 12)),
    )
    return jsonable_encoder(result)


@router.get("/.well-known/agent.json")
async def a2a_agent_card():
    from project_kernel_runtime.integrations.a2a_protocol import A2AHandler

    handler = A2AHandler()
    return handler.get_agent_card()


@router.get("/workspace/diff")
async def get_workspace_diff(session_id: str = "default"):
    import subprocess

    workspace = Path(__file__).resolve().parent.parent
    diff = subprocess.run(
        ["git", "diff", "HEAD", "--unified=3"],
        cwd=workspace,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )
    stat = subprocess.run(
        ["git", "diff", "HEAD", "--stat"],
        cwd=workspace,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )
    return {
        "session_id": session_id,
        "diff": diff.stdout or "",
        "summary": stat.stdout or "",
    }
