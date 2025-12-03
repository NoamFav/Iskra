"""Iskra - Intelligent Git Repository Automation"""

from iskra.api import (
    IskraManager,
    RepoStatus,
    ProcessResult,
    BatchResult,
)
from iskra.config import ConfigManager, RepoInfo, GlobalConfig

__version__ = "1.7.3"

__all__ = [
    "IskraManager",
    "ConfigManager",
    "RepoStatus",
    "ProcessResult",
    "BatchResult",
    "RepoInfo",
    "GlobalConfig",
]
