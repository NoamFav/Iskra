"""Core utilities for auto_commit."""

from .constants import HEAVY_DIRS, ICONS, FILE_ICONS
from .git_operations import (
    generate_commit_message,
    handle_gitignore,
    remove_ds_store_files,
    get_current_branch,
    git_pull,
    git_add_all,
    git_status_porcelain,
    git_commit,
    git_push,
    git_show_last_commit,
)
from .repo_scanner import find_git_repos, find_repo_in_subdirs, _match_any

__all__ = [
    "HEAVY_DIRS",
    "ICONS",
    "FILE_ICONS",
    "generate_commit_message",
    "handle_gitignore",
    "remove_ds_store_files",
    "get_current_branch",
    "git_pull",
    "git_add_all",
    "git_status_porcelain",
    "git_commit",
    "git_push",
    "git_show_last_commit",
    "find_git_repos",
    "find_repo_in_subdirs",
    "_match_any",
]
