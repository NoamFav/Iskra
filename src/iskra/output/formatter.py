"""
Output formatters. JSON for machines, Rich for humans.
Dataclasses for the payload because we're civilized.
"""

from __future__ import annotations
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from rich.console import Console
from ..ui.formatting import style, get_color


OperationType = Literal["commit", "status", "pull", "init", "exec", "other"]
RepoStatusType = Literal["success", "failed", "skipped"]


@dataclass
class RepoChanges:
    """Count of changes. Uncommitted, staged, untracked."""

    uncommitted: int = 0
    staged: int = 0
    untracked: int = 0


@dataclass
class RepoRemote:
    """Remote info. How far ahead/behind, the URL."""

    ahead: int = 0
    behind: int = 0
    url: str = ""


@dataclass
class RepoCommit:
    """Commit info. Hash, message, author, when."""

    hash: str = ""
    message: str = ""
    author: str = ""
    timestamp: str = ""


@dataclass
class RepoResult:
    """Result of processing a single repo. Success, failed, or skipped."""

    path: str
    name: str
    status: RepoStatusType
    branch: str = ""
    changes: RepoChanges = field(default_factory=RepoChanges)
    remote: RepoRemote = field(default_factory=RepoRemote)
    commit: RepoCommit = field(default_factory=RepoCommit)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON output."""
        return asdict(self)


@dataclass
class OutputPayload:
    """The whole output. Stats, results, errors, timestamp."""

    success: bool
    operation: OperationType
    repos_total: int
    repos_success: int
    repos_failed: int
    results: List[RepoResult]
    errors: List[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for JSON. Handles nested dataclasses."""
        data = asdict(self)
        data["timestamp"] = self.timestamp
        data["results"] = [r.to_dict() for r in self.results]
        return data


class BaseFormatter(ABC):
    """Base class for output formatters. JSON or Rich."""

    @abstractmethod
    def emit(self, payload: OutputPayload) -> None: ...


class JSONFormatter(BaseFormatter):
    """Spit out JSON. For scripts and automation."""

    def __init__(self, console: Optional[Console] = None) -> None:
        self._console = console or Console(stderr=False)

    def emit(self, payload: OutputPayload) -> None:
        """Print the payload as JSON."""
        raw = json.dumps(payload.to_dict(), ensure_ascii=False)
        self._console.print_json(raw)


class ConsoleFormatter(BaseFormatter):
    """Pretty Rich output for humans."""

    def __init__(self, console: Optional[Console] = None) -> None:
        self.console = console or Console()

    def emit(self, payload: OutputPayload) -> None:
        """Print a nice summary with colors and stuff."""
        border = get_color("success") if payload.success else get_color("error")

        self.console.rule(style(f"{payload.operation.upper()} summary", "highlight"))

        self.console.print(
            f"{style('Repositories:', 'highlight')} {payload.repos_success}/"
            f"{payload.repos_total} success, {payload.repos_failed} failed",
            style=border,
        )

        if payload.errors:
            self.console.print(f"\n{style('Errors:', 'error')}")
            for err in payload.errors:
                self.console.print(f"- {err}")


def get_formatter(
    json_mode: bool,
    quiet: bool = False,
    console: Optional[Console] = None,
) -> BaseFormatter:
    """Pick the right formatter. JSON if --json or --quiet, otherwise Rich."""
    if json_mode or quiet:
        return JSONFormatter(console=console)
    return ConsoleFormatter(console=console)
