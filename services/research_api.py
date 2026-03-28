from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from project_kernel_runtime.kernel.orchestrator import Orchestrator

router = APIRouter()


@router.post("/")
async def start_research(body: Dict[str, Any]):
    user_id = body.get("user_id")
    query = body.get("query")
    params = body.get("params", {})
    if not user_id or not query:
        raise HTTPException(status_code=400, detail="user_id and query required")

    # Acquire or create orchestrator (import lazily to avoid circulars)
    from project_kernel_runtime.services.fastapi_server import orchestrator
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")

    session = await orchestrator.start_research_session(user_id, query, params)
    return {"session_id": session.session_id, "status": session.status}


@router.get("/")
async def list_sessions(user_id: str = None):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    if user_id:
        sessions = await orchestrator.list_research_sessions(user_id)
        return {"sessions": [s.session_id for s in sessions]}
    return {"sessions": list(orchestrator.research_sessions.keys())}


@router.post("/{session_id}/sources")
async def add_source(session_id: str, body: Dict[str, Any]):
    uri = body.get("uri")
    type_ = body.get("type", "web")
    if not uri:
        raise HTTPException(status_code=400, detail="uri required")

    from project_kernel_runtime.services.fastapi_server import orchestrator
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        user_id = body.get("user_id")
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id required for source addition")
        src = await orchestrator.add_research_source(user_id, session_id, uri, type_)
        return {"source_id": src.id, "uri": src.uri}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/reports")
async def list_reports(session_id: str, user_id: str):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    try:
        session = await orchestrator.get_research_session(user_id, session_id)
        return {"reports": [r.id for r in session.reports]}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{session_id}/summarize")
async def summarize(session_id: str, body: Dict[str, Any]):
    strategy = body.get("strategy", "default")
    user_id = body.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required for summarize")

    from project_kernel_runtime.services.fastapi_server import orchestrator
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        report = await orchestrator.summarize_session(user_id, session_id, strategy)
        return {"report_id": report.id, "summary": report.summary}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}")
async def get_session(session_id: str, user_id: str):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    try:
        session = await orchestrator.get_research_session(user_id, session_id)
        return session.model_dump()
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/progress")
async def get_progress(session_id: str, user_id: str):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    try:
        return await orchestrator.get_research_progress(user_id, session_id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{session_id}/sources")
async def get_sources(session_id: str, user_id: str):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    try:
        session = await orchestrator.get_research_session(user_id, session_id)
        return {"sources": [s.model_dump() for s in session.sources]}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{session_id}/end")
async def end_session(session_id: str, body: Dict[str, Any]):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    user_id = body.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required to end session")
    try:
        await orchestrator.end_research_session(user_id, session_id)
        return {"message": "completed", "session_id": session_id}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{session_id}/report/{report_id}/export")
async def export_report(session_id: str, report_id: str, user_id: str, format: str = "markdown"):
    from project_kernel_runtime.services.fastapi_server import orchestrator
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    try:
        content = await orchestrator.export_research_report(user_id, session_id, report_id, format)
        return {"report_id": report_id, "format": format, "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
