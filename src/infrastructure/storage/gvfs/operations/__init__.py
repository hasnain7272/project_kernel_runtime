"""GVFS Operations."""
from .clone import clone_repository, index_repository
from .persistence import persist_file_change, save_mount_state, restore_mount_state, get_modified_path
from .diff import is_binary_content, generate_diff

__all__ = [
    "clone_repository", "index_repository",
    "persist_file_change", "save_mount_state", "restore_mount_state", "get_modified_path",
    "is_binary_content", "generate_diff"
]