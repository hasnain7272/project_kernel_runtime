from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
import asyncio
import requests


class Source(BaseModel):
    id: str
    type: str  # web|pdf|repo|db
    uri: str
    title: Optional[str] = None
    content_snippet: Optional[str] = None
    fetched_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ResearchReport(BaseModel):
    id: str
    session_id: str
    generated_at: datetime
    summary: str
    findings: List[Dict[str, Any]] = Field(default_factory=list)
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    actions: List[Dict[str, Any]] = Field(default_factory=list)


class ResearchSession(BaseModel):
    session_id: str
    user_id: str
    query: str
    params: Dict[str, Any] = Field(default_factory=dict)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "running"
    progress: float = 0.0
    sources: List[Source] = Field(default_factory=list)
    reports: List[ResearchReport] = Field(default_factory=list)
    contributors: List[str] = Field(default_factory=list)



def simple_summarize(text: str, max_chars: int = 2000) -> str:
    """Basic text summarizer fallback."""
    snippet = text.strip()
    return (snippet[:max_chars] + "...") if len(snippet) > max_chars else snippet
