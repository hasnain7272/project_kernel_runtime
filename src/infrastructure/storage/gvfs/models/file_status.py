"""File status enumeration for virtual filesystem."""
from enum import Enum


class FileStatus(Enum):
    """Virtual file status relative to Git HEAD."""
    UNCHANGED = "unchanged"
    MODIFIED = "modified"
    ADDED = "added"
    DELETED = "deleted"
    CONFLICT = "conflict"
    UNTRACKED = "untracked"