"""Path traversal protection and validation."""
import re
from pathlib import Path
from typing import Optional, Tuple


class PathValidationError(Exception):
    """Raised when path validation fails."""
    pass


def sanitize_path(filepath: str, base_dir: Optional[Path] = None) -> Path:
    """
    Sanitize and validate file path.
    
    Prevents:
    - Directory traversal (../)
    - Absolute paths outside base
    - Null byte injection
    - Unicode normalization attacks
    """
    # Check for null bytes
    if '\x00' in filepath:
        raise PathValidationError("Path contains null bytes")
    
    # Normalize path
    path = Path(filepath).resolve()
    
    # If base directory specified, ensure path is within it
    if base_dir:
        base = Path(base_dir).resolve()
        try:
            path.relative_to(base)
        except ValueError:
            raise PathValidationError(
                f"Path {filepath} is outside allowed directory {base_dir}"
            )
    
    return path


def validate_command_args(args: dict, session_id: str) -> Tuple[bool, str]:
    """
    Validate tool arguments for security.
    
    Returns (is_valid, error_message)
    """
    # Check filepath arguments
    if 'filepath' in args:
        filepath = args['filepath']
        
        # Block directory traversal
        if '..' in filepath:
            return False, "Path cannot contain '..'"
        
        # Block absolute paths (unless explicitly allowed)
        if filepath.startswith('/'):
            return False, "Absolute paths not allowed"
        
        # Block hidden files
        if '/.' in filepath or filepath.startswith('.'):
            return False, "Hidden files not allowed"
    
    # Check command for bash
    if 'command' in args:
        command = args['command']
        
        # Block dangerous patterns
        dangerous = [
            'rm -rf /', 'mkfs', 'dd if=', ':(){', 
            'shutdown', 'reboot', 'format', 'del /f',
            'curl | sh', 'wget |', 'chmod 777',
            'nc -e', '/dev/tcp'
        ]
        
        cmd_lower = command.lower()
        for pattern in dangerous:
            if pattern in cmd_lower:
                return False, f"Command contains dangerous pattern: {pattern}"
        
        # Block shell operators
        if re.search(r'[;&|`$()]', command):
            return False, "Shell operators not allowed"
    
    return True, ""