"""
Web search - fully automatic, agentic.
Priority: 1. Open WebSearch MCP (npx, multi-engine)
        2. ddgs (DuckDuckGo, works in venv)
        3. Wikipedia fallback
"""

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

# Check for ddgs (works in venv without anything else)
_DDGS_AVAILABLE = False
try:
    from ddgs import DDGS
    _DDGS_AVAILABLE = True
except ImportError:
    pass

logger.info(f"[WebSearch] ddgs available: {_DDGS_AVAILABLE}")

# Open WebSearch MCP state
_MCP_PROCESS = None
_MCP_URL = os.getenv("OPEN_WEBSEARCH_URL", "http://localhost:3030")


def _check_mcp_running() -> bool:
    """Check if MCP server is running."""
    try:
        import httpx
        r = httpx.get(f"{_MCP_URL}/health", timeout=3)
        return r.status_code == 200
    except:
        return False


async def _ensure_mcp_running() -> str:
    """Auto-start Open WebSearch MCP via npx."""
    global _MCP_PROCESS, _MCP_URL
    
    # Already running?
    if _check_mcp_running():
        return _MCP_URL
    
    # Check for npm/npx
    npx_cmd = shutil.which("npx") or "npx"
    if not npx_cmd:
        return ""
    
    logger.info("[WebSearch] Starting Open WebSearch MCP...")
    
    try:
        # Start MCP server
        _MCP_PROCESS = subprocess.Popen(
            [npx_cmd, "-y", "open-websearch@latest"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={
                **os.environ,
                "PORT": "3030",
                "DEFAULT_SEARCH_ENGINE": "duckduckgo",
                "MODE": "http",
                "ENABLE_CORS": "true"
            }
        )
        
        # Wait for it to start
        for _ in range(15):
            await asyncio.sleep(2)
            if _check_mcp_running():
                _MCP_URL = "http://localhost:3030"
                logger.info("[WebSearch] MCP ready at http://localhost:3030")
                return _MCP_URL
    except Exception as e:
        logger.error(f"Failed to start MCP: {e}")
    
    return ""


def _search_mcp(query: str, max_results: int = 5) -> list:
    """Search using Open WebSearch MCP."""
    if not _check_mcp_running():
        return []
    
    try:
        import httpx
        resp = httpx.post(
            f"{_MCP_URL}/search",
            json={"query": query, "limit": max_results},
            timeout=30.0
        )
        if resp.status_code == 200:
            data = resp.json()
            # MCP returns array directly
            results = data if isinstance(data, list) else data.get("results", [])
            return [{
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("description", "")[:200] or r.get("body", "")[:200]
            } for r in results]
    except Exception as e:
        logger.error(f"MCP search error: {e}")
    return []


def _search_ddgs(query: str, max_results: int = 5) -> list:
    """Search using ddgs library."""
    if not _DDGS_AVAILABLE:
        return []
    
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", "")[:200]
                })
        return results
    except Exception as e:
        logger.error(f"DDGS error: {e}")
    return []


def _search_wiki(query: str, max_results: int = 5) -> list:
    """Search Wikipedia API."""
    try:
        url = "https://en.wikipedia.org/w/api.php"
        params = urllib.parse.urlencode({
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": max_results
        })
        req = urllib.request.Request(f"{url}?{params}")
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
            return data.get("query", {}).get("search", [])
    except Exception as e:
        logger.error(f"Wikipedia error: {e}")
    return []


async def web_search(query: str, max_results: int = 5):
    """
    Fully automatic web search.
    
    1. Open WebSearch MCP (auto-start via npx)
    2. ddgs (DDG library, works in venv)
    3. Wikipedia fallback
    """
    loop = asyncio.get_event_loop()
    
    # 1. Try Open WebSearch MCP (multi-engine, no API key)
    url = await _ensure_mcp_running()
    if url:
        results = await loop.run_in_executor(None, _search_mcp, query, max_results)
        if results:
            return results
    
    # 2. Try ddgs (works without any setup)
    if _DDGS_AVAILABLE:
        results = await loop.run_in_executor(None, _search_ddgs, query, max_results)
        if results:
            return results
    
    # 3. Fallback to Wikipedia
    results = await loop.run_in_executor(None, _search_wiki, query, max_results)
    formatted = []
    for r in results:
        formatted.append({
            "title": r.get("title", ""),
            "url": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(r.get('title', ''))}",
            "snippet": re.sub(r'<[^>]+>', '', r.get("snippet", ""))[:200]
        })
    
    if formatted:
        return formatted
    
    return [{"title": f"Search: {query}", "url": f"https://google.com/search?q={urllib.parse.quote(query)}", "snippet": "Click for Google"}]


async def web_fetch(url: str):
    """Fetch content from URL via MCP or direct."""
    # Try MCP fetch first
    if _check_mcp_running():
        try:
            import httpx
            resp = httpx.post(
                f"{_MCP_URL}/fetchWebContent",
                json={"url": url},
                timeout=30.0
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("content", "")[:3000]
        except:
            pass
    
    # Fallback to direct fetch
    loop = asyncio.get_event_loop()
    
    def _fetch():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as response:
                html = response.read().decode("utf-8", errors="ignore")
                text = re.sub(r'<[^>]+>', ' ', html)
                return re.sub(r'\s+', ' ', text)[:3000]
        except Exception as e:
            return f"Error: {e}"
    
    return await loop.run_in_executor(None, _fetch)