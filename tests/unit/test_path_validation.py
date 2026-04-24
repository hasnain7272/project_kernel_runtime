"""Unit tests for path validation."""
import pytest
from pathlib import Path
from src.infrastructure.security.path_validation import (
    sanitize_path,
    validate_command_args,
    PathValidationError
)


class TestSanitizePath:
    """Test path sanitization."""
    
    def test_valid_relative_path(self):
        """Accept valid relative paths."""
        base = Path("/workspace")
        result = sanitize_path("src/main.py", base)
        assert result == Path("/workspace/src/main.py")
    
    def test_blocks_traversal(self):
        """Block directory traversal."""
        base = Path("/workspace")
        with pytest.raises(PathValidationError):
            sanitize_path("../etc/passwd", base)
    
    def test_blocks_absolute_outside_base(self):
        """Block absolute paths outside base."""
        base = Path("/workspace")
        with pytest.raises(PathValidationError):
            sanitize_path("/etc/passwd", base)
    
    def test_blocks_null_bytes(self):
        """Block null byte injection."""
        base = Path("/workspace")
        with pytest.raises(PathValidationError):
            sanitize_path("file.txt\x00.sh", base)
    
    def test_allows_absolute_in_base(self):
        """Allow absolute paths within base."""
        base = Path("/workspace")
        result = sanitize_path("/workspace/src/main.py", base)
        assert result == Path("/workspace/src/main.py")
    
    def test_normalizes_dots(self):
        """Normalize path dots."""
        base = Path("/workspace")
        result = sanitize_path("./src/../lib/file.py", base)
        assert result == Path("/workspace/lib/file.py")


class TestValidateCommandArgs:
    """Test command argument validation."""
    
    def test_blocks_dangerous_commands(self):
        """Block dangerous shell commands."""
        args = {"command": "rm -rf /"}
        valid, error = validate_command_args(args, "session-123")
        assert not valid
        assert "dangerous" in error.lower()
    
    def test_blocks_shell_operators(self):
        """Block shell operators."""
        args = {"command": "ls; cat /etc/passwd"}
        valid, error = validate_command_args(args, "session-123")
        assert not valid
    
    def test_allows_safe_commands(self):
        """Allow safe commands."""
        args = {"command": "ls -la"}
        valid, error = validate_command_args(args, "session-123")
        assert valid
        assert error == ""
    
    def test_blocks_traversal_in_filepath(self):
        """Block traversal in file paths."""
        args = {"filepath": "../etc/passwd"}
        valid, error = validate_command_args(args, "session-123")
        assert not valid
    
    def test_blocks_hidden_files(self):
        """Block hidden files."""
        args = {"filepath": ".env"}
        valid, error = validate_command_args(args, "session-123")
        assert not valid
    
    def test_allows_valid_filepath(self):
        """Allow valid file paths."""
        args = {"filepath": "src/main.py"}
        valid, error = validate_command_args(args, "session-123")
        assert valid
    
    def test_allows_no_dangerous_patterns(self):
        """Allow commands without dangerous patterns."""
        args = {"command": "python main.py"}
        valid, error = validate_command_args(args, "session-123")
        assert valid


class TestEdgeCases:
    """Test edge cases."""
    
    def test_empty_path(self):
        """Handle empty path."""
        base = Path("/workspace")
        result = sanitize_path("", base)
        assert result == Path("/workspace")
    
    def test_empty_command(self):
        """Handle empty command."""
        args = {"command": ""}
        valid, error = validate_command_args(args, "session-123")
        assert valid  # Empty is technically safe
    
    def test_unicode_in_path(self):
        """Handle unicode in path."""
        base = Path("/workspace")
        result = sanitize_path("文件.txt", base)
        assert result == Path("/workspace/文件.txt")
    
    def test_very_long_path(self):
        """Handle very long path."""
        base = Path("/workspace")
        long_path = "a/" * 100 + "file.txt"
        result = sanitize_path(long_path, base)
        assert "file.txt" in str(result)