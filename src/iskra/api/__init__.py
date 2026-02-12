"""
Iskra Python Library API
Provides a clean programmatic interface for repository automation
"""

from .manager import (
    IskraManager,
    RepoStatus,
    ChangesSummary,
    RemoteStatus,
    CommitInfo,
    ProcessResult,
    BatchResult,
    ValidationResult,
    Operation,
)

__all__ = [
    "IskraManager",
    "RepoStatus",
    "ChangesSummary",
    "RemoteStatus",
    "CommitInfo",
    "ProcessResult",
    "BatchResult",
    "ValidationResult",
    "Operation",
]
