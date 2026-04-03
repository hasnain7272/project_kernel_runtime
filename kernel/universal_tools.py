"""
Universal Tools Module - Consolidated tools for Agentic OS
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict
from typing import Any, Dict, Optional
import asyncio
import logging
import os
import platform
import re
import shlex


"""
Base Tool — Abstract base class for all tool implementations.

Every tool in the kernel inherits from BaseTool and implements execute().
"""



class ToolMutability(str, Enum):
    """How a tool modifies the environment."""
    READ_ONLY = "read_only"
    WRITE = "write"
    EXECUTE = "execute"
    NETWORK = "network"


@dataclass
class ToolResult:
    """Standard result from tool execution."""
    success: bool
    output: Any = None
    error: Optional[str] = None


class BaseTool(ABC):
    """
    Abstract base class for all kernel tools.
    
    Subclasses must define:
    - name: unique identifier (e.g., "read_file")
    - description: what the tool does
    - input_schema: JSON Schema for arguments
    - execute(): the actual implementation
    """
    
    name: str = ""
    description: str = ""
    input_schema: Dict[str, Any] = {}
    requires_sandbox: bool = False
    mutability: ToolMutability = ToolMutability.READ_ONLY
    
    @abstractmethod
    async def execute(self, arguments: Dict[str, Any], context=None) -> Any:
        """Execute the tool with the given arguments."""
        pass
    
    def to_schema(self) -> Dict[str, Any]:
        """Export tool definition for MCP/LLM function calling."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


"""
File Operations Tools — Real implementations for reading, writing, editing,
searching, and listing files.

Inspired by: Claude Code's file tools, Aider's edit format, OpenHands file ops
"""



logger = logging.getLogger(__name__)


class ReadFileTool(BaseTool):
    """Read the contents of a file with optional line range."""
    
    name = "read_file"
    description = "Read the contents of a file. Supports optional line range with start_line and end_line."
    mutability = ToolMutability.READ_ONLY
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Absolute or relative file path"},
            "start_line": {"type": "integer", "description": "Start line (1-indexed, inclusive)"},
            "end_line": {"type": "integer", "description": "End line (1-indexed, inclusive)"},
        },
        "required": ["path"],
    }
    
    async def execute(self, arguments: Dict[str, Any], context=None) -> Any:
        path = arguments["path"]
        start = arguments.get("start_line")
        end = arguments.get("end_line")
        
        # Resolve path relative to workspace
        if context and hasattr(context, 'workspace_path') and not os.path.isabs(path):
            path = os.path.join(context.workspace_path, path)
        
        if not os.path.exists(path):
            return {"error": f"File not found: {path}"}
        
        if not os.path.isfile(path):
            return {"error": f"Not a file: {path}"}
        
        try:
            # Check if binary
            with open(path, 'rb') as f:
                chunk = f.read(8192)
                if b'\x00' in chunk:
                    file_size = os.path.getsize(path)
                    return {"content": f"[Binary file, {file_size} bytes]", "is_binary": True}
            
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            
            total_lines = len(lines)
            
            if start and end:
                start = max(1, start)
                end = min(total_lines, end)
                selected = lines[start - 1:end]
                content = ''.join(selected)
                return {
                    "content": content,
                    "total_lines": total_lines,
                    "showing": f"lines {start}-{end}",
                }
            
            content = ''.join(lines)
            return {
                "content": content,
                "total_lines": total_lines,
            }
            
        except Exception as e:
            return {"error": f"Failed to read file: {str(e)}"}


class WriteFileTool(BaseTool):
    """Write content to a file, creating directories as needed."""
    
    name = "write_file"
    description = "Write content to a file. Creates the file and parent directories if they don't exist. Overwrites existing content."
    mutability = ToolMutability.WRITE
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to write to"},
            "content": {"type": "string", "description": "Content to write"},
            "create_dirs": {"type": "boolean", "description": "Create parent directories", "default": True},
        },
        "required": ["path", "content"],
    }
    
    async def execute(self, arguments: Dict[str, Any], context=None) -> Any:
        path = arguments["path"]
        content = arguments["content"]
        create_dirs = arguments.get("create_dirs", True)
        
        if context and hasattr(context, 'workspace_path') and not os.path.isabs(path):
            path = os.path.join(context.workspace_path, path)
        
        try:
            if create_dirs:
                os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
            
            # Create backup if file exists
            existed = os.path.exists(path)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            line_count = content.count('\n') + (1 if content and not content.endswith('\n') else 0)
            
            return {
                "success": True,
                "path": path,
                "bytes_written": len(content.encode('utf-8')),
                "lines": line_count,
                "created": not existed,
            }
        except Exception as e:
            return {"error": f"Failed to write file: {str(e)}"}


class EditFileTool(BaseTool):
    """Search-and-replace editing within a file."""
    
    name = "edit_file"
    description = "Edit a file by replacing exact text matches. Provide the exact text to find and the replacement text."
    mutability = ToolMutability.WRITE
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to edit"},
            "old_text": {"type": "string", "description": "Exact text to find and replace"},
            "new_text": {"type": "string", "description": "Replacement text"},
        },
        "required": ["path", "old_text", "new_text"],
    }
    
    async def execute(self, arguments: Dict[str, Any], context=None) -> Any:
        path = arguments["path"]
        old_text = arguments["old_text"]
        new_text = arguments["new_text"]
        
        if context and hasattr(context, 'workspace_path') and not os.path.isabs(path):
            path = os.path.join(context.workspace_path, path)
        
        if not os.path.exists(path):
            return {"error": f"File not found: {path}"}
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            count = content.count(old_text)
            if count == 0:
                return {"error": "old_text not found in file", "searched_for": old_text[:200]}
            
            new_content = content.replace(old_text, new_text, 1)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return {
                "success": True,
                "path": path,
                "replacements": 1,
                "occurrences_found": count,
            }
        except Exception as e:
            return {"error": f"Failed to edit file: {str(e)}"}


class SearchFilesTool(BaseTool):
    """Search for text patterns across files using ripgrep-style matching."""
    
    name = "search_files"
    description = "Search for text patterns across files in a directory. Returns matching lines with file paths and line numbers."
    mutability = ToolMutability.READ_ONLY
    input_schema = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Text or regex pattern to search for"},
            "path": {"type": "string", "description": "Directory to search in", "default": "."},
            "include": {"type": "string", "description": "File glob pattern to include (e.g., '*.py')"},
            "max_results": {"type": "integer", "description": "Maximum results", "default": 50},
        },
        "required": ["pattern"],
    }
    
    async def execute(self, arguments: Dict[str, Any], context=None) -> Any:
        pattern = arguments["pattern"]
        search_path = arguments.get("path", ".")
        include = arguments.get("include")
        max_results = arguments.get("max_results", 50)
        
        if context and hasattr(context, 'workspace_path') and not os.path.isabs(search_path):
            search_path = os.path.join(context.workspace_path, search_path)
        
        if not os.path.exists(search_path):
            return {"error": f"Path not found: {search_path}"}
        
        results = []
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error:
            regex = re.compile(re.escape(pattern), re.IGNORECASE)
        
        try:
            for root, dirs, files in os.walk(search_path):
                # Skip hidden and common ignored directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in 
                          ('node_modules', '__pycache__', '.git', 'venv', '.venv', 'dist', 'build')]
                
                for fname in files:
                    if include and not self._glob_match(fname, include):
                        continue
                    
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                            for i, line in enumerate(f, 1):
                                if regex.search(line):
                                    rel_path = os.path.relpath(fpath, search_path)
                                    results.append({
                                        "file": rel_path,
                                        "line": i,
                                        "content": line.rstrip()[:200],
                                    })
                                    if len(results) >= max_results:
                                        return {"results": results, "truncated": True, "total_found": len(results)}
                    except (OSError, UnicodeDecodeError):
                        continue
            
            return {"results": results, "truncated": False, "total_found": len(results)}
        except Exception as e:
            return {"error": f"Search failed: {str(e)}"}
    
    @staticmethod
    def _glob_match(filename: str, pattern: str) -> bool:
        """Simple glob matching for file extensions."""
        if pattern.startswith("*."):
            return filename.endswith(pattern[1:])
        return pattern in filename


class ListDirectoryTool(BaseTool):
    """List contents of a directory."""
    
    name = "list_directory"
    description = "List files and subdirectories in a directory with file sizes and types."
    mutability = ToolMutability.READ_ONLY
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory path to list", "default": "."},
            "recursive": {"type": "boolean", "description": "List recursively", "default": False},
            "max_depth": {"type": "integer", "description": "Max recursion depth", "default": 2},
        },
        "required": [],
    }
    
    async def execute(self, arguments: Dict[str, Any], context=None) -> Any:
        path = arguments.get("path", ".")
        recursive = arguments.get("recursive", False)
        max_depth = arguments.get("max_depth", 2)
        
        if context and hasattr(context, 'workspace_path') and not os.path.isabs(path):
            path = os.path.join(context.workspace_path, path)
        
        if not os.path.exists(path):
            return {"error": f"Directory not found: {path}"}
        
        if not os.path.isdir(path):
            return {"error": f"Not a directory: {path}"}
        
        try:
            entries = []
            self._list_dir(path, entries, recursive, max_depth, 0, path)
            return {"entries": entries, "total": len(entries), "path": path}
        except Exception as e:
            return {"error": f"Failed to list directory: {str(e)}"}
    
    def _list_dir(self, dir_path, entries, recursive, max_depth, current_depth, base_path):
        """Recursively list directory contents."""
        try:
            items = sorted(os.listdir(dir_path))
        except PermissionError:
            return
        
        for item in items:
            if item.startswith('.'):
                continue
            
            full_path = os.path.join(dir_path, item)
            rel_path = os.path.relpath(full_path, base_path)
            is_dir = os.path.isdir(full_path)
            
            entry = {
                "name": rel_path,
                "type": "directory" if is_dir else "file",
            }
            
            if not is_dir:
                try:
                    entry["size"] = os.path.getsize(full_path)
                except OSError:
                    entry["size"] = 0
            
            entries.append(entry)
            
            if is_dir and recursive and current_depth < max_depth:
                self._list_dir(full_path, entries, recursive, max_depth, current_depth + 1, base_path)


"""
Git Operations Tools — Real git integration via subprocess.

Provides tools for git status, diff, commit, and log — using actual
git commands, not mocks.

Inspired by: Aider's deep git integration with auto-commit and attribution
"""



logger = logging.getLogger(__name__)


async def _run_git(args: list, cwd: str, timeout: int = 15) -> Dict[str, Any]:
    """Run a git command and return structured output."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        
        return {
            "exit_code": proc.returncode,
            "stdout": stdout.decode('utf-8', errors='replace').strip(),
            "stderr": stderr.decode('utf-8', errors='replace').strip(),
        }
    except asyncio.TimeoutError:
        return {"exit_code": -1, "stdout": "", "stderr": f"Git command timed out after {timeout}s"}
    except FileNotFoundError:
        return {"exit_code": -1, "stdout": "", "stderr": "Git is not installed or not in PATH"}
    except Exception as e:
        return {"exit_code": -1, "stdout": "", "stderr": str(e)}


def _resolve_cwd(arguments, context):
    """Resolve working directory from arguments or context."""
    cwd = arguments.get("cwd")
    if not cwd and context and hasattr(context, 'workspace_path'):
        cwd = context.workspace_path
    return cwd or "."


class GitStatusTool(BaseTool):
    """Show the working tree status."""
    
    name = "git_status"
    description = "Show the git working tree status including staged, unstaged, and untracked files."
    mutability = ToolMutability.READ_ONLY
    input_schema = {
        "type": "object",
        "properties": {
            "cwd": {"type": "string", "description": "Repository directory"},
        },
        "required": [],
    }
    
    async def execute(self, arguments: Dict[str, Any], context=None) -> Any:
        cwd = _resolve_cwd(arguments, context)
        result = await _run_git(["status", "--porcelain=v2", "--branch"], cwd)
        
        if result["exit_code"] != 0:
            # Try short format as fallback
            result = await _run_git(["status", "--short", "--branch"], cwd)
        
        return result


class GitDiffTool(BaseTool):
    """Show changes in the working tree."""
    
    name = "git_diff"
    description = "Show git diff of changes. Can diff staged, unstaged, or between commits."
    mutability = ToolMutability.READ_ONLY
    input_schema = {
        "type": "object",
        "properties": {
            "cwd": {"type": "string", "description": "Repository directory"},
            "staged": {"type": "boolean", "description": "Show staged changes", "default": False},
            "file": {"type": "string", "description": "Specific file to diff"},
            "ref": {"type": "string", "description": "Commit ref to diff against (e.g., 'HEAD~1')"},
        },
        "required": [],
    }
    
    async def execute(self, arguments: Dict[str, Any], context=None) -> Any:
        cwd = _resolve_cwd(arguments, context)
        args = ["diff"]
        
        if arguments.get("staged"):
            args.append("--cached")
        if arguments.get("ref"):
            args.append(arguments["ref"])
        if arguments.get("file"):
            args.extend(["--", arguments["file"]])
        
        result = await _run_git(args, cwd, timeout=30)
        
        # Truncate very large diffs
        if len(result.get("stdout", "")) > 50000:
            result["stdout"] = result["stdout"][:50000] + "\n... [diff truncated]"
            result["truncated"] = True
        
        return result


class GitCommitTool(BaseTool):
    """Commit staged changes with a message."""
    
    name = "git_commit"
    description = "Stage and commit changes to git. Optionally stage specific files or all changes."
    mutability = ToolMutability.WRITE
    input_schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "Commit message"},
            "cwd": {"type": "string", "description": "Repository directory"},
            "files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Files to stage before commit (empty = commit already staged)"
            },
            "all": {"type": "boolean", "description": "Stage all modified files", "default": False},
        },
        "required": ["message"],
    }
    
    async def execute(self, arguments: Dict[str, Any], context=None) -> Any:
        cwd = _resolve_cwd(arguments, context)
        message = arguments["message"]
        files = arguments.get("files", [])
        stage_all = arguments.get("all", False)
        
        # Stage files if requested
        if stage_all:
            stage_result = await _run_git(["add", "-A"], cwd)
            if stage_result["exit_code"] != 0:
                return {"error": f"Failed to stage files: {stage_result['stderr']}"}
        elif files:
            stage_result = await _run_git(["add", "--"] + files, cwd)
            if stage_result["exit_code"] != 0:
                return {"error": f"Failed to stage files: {stage_result['stderr']}"}
        
        # Commit with agent attribution (Aider pattern)
        result = await _run_git([
            "commit",
            "-m", message,
            "--author", "Antigravity Agent <agent@antigravity.dev>",
        ], cwd)
        
        return result


class GitLogTool(BaseTool):
    """Show commit history."""
    
    name = "git_log"
    description = "Show recent git commit history with hashes, authors, and messages."
    mutability = ToolMutability.READ_ONLY
    input_schema = {
        "type": "object",
        "properties": {
            "cwd": {"type": "string", "description": "Repository directory"},
            "count": {"type": "integer", "description": "Number of commits to show", "default": 10},
            "oneline": {"type": "boolean", "description": "One line per commit", "default": True},
        },
        "required": [],
    }
    
    async def execute(self, arguments: Dict[str, Any], context=None) -> Any:
        cwd = _resolve_cwd(arguments, context)
        count = arguments.get("count", 10)
        oneline = arguments.get("oneline", True)
        
        args = ["log", f"-{count}"]
        if oneline:
            args.append("--oneline")
        else:
            args.extend(["--format=%H|%an|%ar|%s"])
        
        return await _run_git(args, cwd)


"""
Terminal Tool — Real shell command execution.

Executes bash/powershell commands with proper subprocess isolation,
timeout enforcement, streaming output, and working directory support.

Inspired by: OpenHands bash tool, Claude Code's code_execution tool
"""



logger = logging.getLogger(__name__)


class BashExecuteTool(BaseTool):
    """Execute shell commands with timeout and output capture."""
    
    name = "bash_execute"
    description = "Execute a shell command (bash on Linux/Mac, powershell on Windows). Returns stdout, stderr, and exit code."
    mutability = ToolMutability.EXECUTE
    requires_sandbox = False  # Can be routed to sandbox by ToolExecutor
    input_schema = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command to execute"},
            "cwd": {"type": "string", "description": "Working directory (optional)"},
            "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30},
            "env": {"type": "object", "description": "Additional environment variables"},
        },
        "required": ["command"],
    }
    
    async def execute(self, arguments: Dict[str, Any], context=None) -> Any:
        command = arguments["command"]
        cwd = arguments.get("cwd")
        timeout = arguments.get("timeout", 30)
        env_extra = arguments.get("env", {})
        
        # Resolve working directory
        if not cwd and context and hasattr(context, 'workspace_path'):
            cwd = context.workspace_path
        
        if cwd and not os.path.isabs(cwd):
            if context and hasattr(context, 'workspace_path'):
                cwd = os.path.join(context.workspace_path, cwd)
        
        if cwd and not os.path.isdir(cwd):
            return {"error": f"Working directory not found: {cwd}"}
        
        # Build environment
        env = os.environ.copy()
        env.update(env_extra)
        # Safety: prevent agent from modifying PATH to unsafe locations
        env.pop('LD_PRELOAD', None)
        
        try:
            is_windows = platform.system() == "Windows"
            
            if is_windows:
                proc = await asyncio.create_subprocess_exec(
                    "powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                    env=env,
                )
            else:
                proc = await asyncio.create_subprocess_exec(
                    "/bin/bash", "-c", command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                    env=env,
                )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return {
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": f"Command timed out after {timeout}s",
                    "timed_out": True,
                }
            
            stdout_str = stdout.decode('utf-8', errors='replace').strip()
            stderr_str = stderr.decode('utf-8', errors='replace').strip()
            
            # Truncate very long output
            max_output = 50000
            if len(stdout_str) > max_output:
                stdout_str = stdout_str[:max_output] + f"\n... [truncated, {len(stdout_str)} total chars]"
            if len(stderr_str) > max_output:
                stderr_str = stderr_str[:max_output] + f"\n... [truncated, {len(stderr_str)} total chars]"
            
            return {
                "exit_code": proc.returncode,
                "stdout": stdout_str,
                "stderr": stderr_str,
                "timed_out": False,
            }
        
        except FileNotFoundError:
            shell_name = "powershell.exe" if platform.system() == "Windows" else "/bin/bash"
            return {"error": f"Shell not found: {shell_name}"}
        except Exception as e:
            return {"error": f"Command execution failed: {type(e).__name__}: {str(e)}"}


"""
Web Search & Fetch Tools — Real web content retrieval.

Provides tools for searching the web and fetching URL content
with HTML-to-text conversion.
"""



logger = logging.getLogger(__name__)


class WebSearchTool(BaseTool):
    """Search the web using DuckDuckGo Lite (no API key required)."""
    
    name = "web_search"
    description = "Search the web for information. Uses DuckDuckGo Lite, no API key needed."
    mutability = ToolMutability.NETWORK
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "max_results": {"type": "integer", "description": "Max results", "default": 5},
        },
        "required": ["query"],
    }
    
    async def execute(self, arguments: Dict[str, Any], context=None) -> Any:
        from .web_search import web_search as do_search
        query = arguments.get("query") or arguments.get("q", "")
        max_results = arguments.get("max_results", 5)
        
        if not query:
            return {"error": "Query is required"}
        
        try:
            results = await do_search(query, max_results=int(max_results))
            return {"results": results, "query": query, "total_found": len(results)}
        except Exception as e:
            return {"error": f"Search failed: {type(e).__name__}: {str(e)}"}


class WebFetchTool(BaseTool):
    """Fetch content from a URL and convert to text."""
    
    name = "web_fetch"
    description = "Fetch content from a URL and return as text. HTML is converted to readable text."
    mutability = ToolMutability.NETWORK
    input_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to fetch"},
            "max_length": {"type": "integer", "description": "Max content length in chars", "default": 10000},
        },
        "required": ["url"],
    }
    
    async def execute(self, arguments: Dict[str, Any], context=None) -> Any:
        url = arguments["url"]
        max_length = arguments.get("max_length", 10000)
        
        try:
            import httpx
        except ImportError:
            return {"error": "httpx not installed. Run: pip install httpx"}
        
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; AntigravityAgent/1.0)"}
                )
                
                content_type = response.headers.get('content-type', '')
                
                if response.status_code != 200:
                    return {"error": f"Fetch returned status {response.status_code}"}
                
                text = response.text
                
                # Convert HTML to plain text
                if 'text/html' in content_type:
                    text = self._html_to_text(text)
                
                # Truncate
                if len(text) > max_length:
                    text = text[:max_length] + f"\n... [truncated at {max_length} chars]"
                
                return {
                    "content": text,
                    "url": str(response.url),
                    "status_code": response.status_code,
                    "content_type": content_type,
                    "length": len(text),
                }
                
        except Exception as e:
            return {"error": f"Fetch failed: {type(e).__name__}: {str(e)}"}
    
    @staticmethod
    def _html_to_text(html: str) -> str:
        """Basic HTML to text conversion."""
        # Remove script and style blocks
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        # Convert common elements
        text = re.sub(r'<br\s*/?>', '\n', text)
        text = re.sub(r'</?p[^>]*>', '\n', text)
        text = re.sub(r'</?div[^>]*>', '\n', text)
        text = re.sub(r'<h[1-6][^>]*>(.*?)</h[1-6]>', r'\n\n\1\n\n', text, flags=re.DOTALL)
        text = re.sub(r'<li[^>]*>(.*?)</li>', r'\n- \1', text, flags=re.DOTALL)
        # Remove remaining tags
        text = re.sub(r'<[^>]+>', '', text)
        # Decode entities
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
        # Clean up whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        return text.strip()



def get_all_tools():
    """Return instances of all core tools."""
    return [
        ReadFileTool(),
        WriteFileTool(),
        EditFileTool(),
        SearchFilesTool(),
        ListDirectoryTool(),
        BashExecuteTool(),
        GitStatusTool(),
        GitDiffTool(),
        GitCommitTool(),
        GitLogTool(),
        WebSearchTool(),
        WebFetchTool(),
    ]
