""""""

from __future__ import annotations
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from rich.console import Console

# Type aliases for improved readability and type safety
OperationType = Literal["commit", "status", "pull", "init", "exec", "other"]
RepoStatusType = Literal["success", "failed", "skipped"]


@dataclass
class RepoChanges:
    """"""

    uncommitted: int = 0
    staged: int = 0
    untracked: int = 0


@dataclass
class RepoRemote:
    """"""

    ahead: int = 0
    behind: int = 0
    url: str = ""


@dataclass
class RepoCommit:
    """"""

    hash: str = ""
    message: str = ""
    author: str = ""
    timestamp: str = ""  # ISO8601 format for parseability


@dataclass
class RepoResult:
    """"""

    path: str
    name: str
    status: RepoStatusType
    branch: str = ""
    changes: RepoChanges = field(default_factory=RepoChanges)
    remote: RepoRemote = field(default_factory=RepoRemote)
    commit: RepoCommit = field(default_factory=RepoCommit)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """"""
        return asdict(self)


@dataclass
class OutputPayload:
    """"""

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
        """"""
        data = asdict(self)
        data["timestamp"] = self.timestamp
        data["results"] = [r.to_dict() for r in self.results]
        return data


class BaseFormatter(ABC):
    """"""

    @abstractmethod
    def emit(self, payload: OutputPayload) -> None:
        """"""
        ...


class JSONFormatter(BaseFormatter):
    """"""

    def __init__(self, console: Optional[Console] = None) -> None:
        """"""
        self._console = console or Console(stderr=False)

    def emit(self, payload: OutputPayload) -> None:
        """"""
        # Convert structured payload to plain dict
        raw = json.dumps(payload.to_dict(), ensure_ascii=False)

        # print_json adds nice formatting but keeps it valid JSON
        # Syntax highlighting only appears in terminals, not when piped
        self._console.print_json(raw)


class ConsoleFormatter(BaseFormatter):
    """"""

    def __init__(self, console: Optional[Console] = None) -> None:
        """"""
        self.console = console or Console()

    def emit(self, payload: OutputPayload) -> None:
        """"""
        # Choose color based on overall success
        border = "green" if payload.success else "red"

        # Print horizontal rule with operation type
        self.console.rule(f"[bold]{payload.operation.upper()} summary[/bold]")

        # Print repository counts in colored border
        self.console.print(
            f"[bold]Repositories:[/bold] {payload.repos_success}/"
            f"{payload.repos_total} success, {payload.repos_failed} failed",
            style=border,
        )

        # Print error list if any errors occurred
        if payload.errors:
            self.console.print("\n[bold red]Errors:[/bold red]")
            for err in payload.errors:
                self.console.print(f"- {err}")


def get_formatter(
    json_mode: bool,
    quiet: bool = False,
    console: Optional[Console] = None,
) -> BaseFormatter:
    """"""
    if json_mode or quiet:
        return JSONFormatter(console=console)
    return ConsoleFormatter(console=console)
