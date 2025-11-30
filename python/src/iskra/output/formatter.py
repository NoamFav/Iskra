"""
Output formatter system for Iskra operations.

Provides a unified data model and formatting system for all Iskra commands,
supporting both machine-readable JSON output and human-friendly console summaries.
This abstraction allows CLI modules to emit structured data without worrying
about presentation details.

Architecture:
    - Data Models: Structured dataclasses for operation results
    - Formatters: Abstract base with JSON and Console implementations
    - Factory: get_formatter() selects appropriate formatter

Design Pattern:
    Strategy pattern - formatters implement common interface,
    allowing runtime selection based on user flags (--json, --quiet)

Benefits:
    - Consistent output structure across all commands
    - Easy addition of new output formats (CSV, XML, etc.)
    - Separation of data gathering and presentation
    - Machine-readable output for automation/scripting
"""

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
    """
        Change counters for a single repository.

        Tracks the state of modifications in a git working directory,
        categorizing changes by their staging status. Useful for
        understanding repository state and deciding whether commits
        are needed.

        Attributes:
            uncommitted: Modified files not yet staged (git diff output)
            staged: Files staged for commit (git diff --cached output)
            untracked: New files not tracked by git (git ls-files --others)

        Example:
    ```python
            changes = RepoChanges(
                uncommitted=5,  # 5 modified files
                staged=3,       # 3 files ready to commit
                untracked=2     # 2 new files not in git
            )
    ```

        Note:
            All counters default to 0, representing a clean repository.
            This allows omitting unchanged fields in JSON output.
    """

    uncommitted: int = 0
    staged: int = 0
    untracked: int = 0


@dataclass
class RepoRemote:
    """
        Remote tracking information for a repository.

        Describes the relationship between local and remote branches,
        indicating whether the local branch is ahead (has unpushed commits)
        or behind (missing remote commits). Essential for sync operations.

        Attributes:
            ahead: Number of commits ahead of remote (unpushed)
            behind: Number of commits behind remote (need to pull)
            url: Remote repository URL (e.g., GitHub, GitLab)

        States:
            - ahead=0, behind=0: In sync with remote
            - ahead>0, behind=0: Have local commits to push
            - ahead=0, behind>0: Need to pull remote commits
            - ahead>0, behind>0: Diverged (need merge/rebase)

        Example:
    ```python
            remote = RepoRemote(
                ahead=2,
                behind=0,
                url="https://github.com/user/repo.git"
            )
            # Indicates 2 commits ready to push, in sync otherwise
    ```

        Note:
            Empty URL string indicates no remote configured.
            Some repos (local-only) may have no remote.
    """

    ahead: int = 0
    behind: int = 0
    url: str = ""


@dataclass
class RepoCommit:
    """
        Last commit metadata for a repository.

        Captures information about the most recent commit in the repository.
        Useful for tracking what was last changed, by whom, and when.
        Supports commit history tracking and audit trails.

        Attributes:
            hash: Git commit SHA-1 hash (40 hex chars, or short form)
            message: Commit message (first line or full message)
            author: Commit author name and/or email
            timestamp: Commit date in ISO8601 format (YYYY-MM-DDTHH:MM:SSZ)

        Example:
    ```python
            commit = RepoCommit(
                hash="a1b2c3d4e5f6",
                message="feat: add user authentication",
                author="Jane Doe <jane@example.com>",
                timestamp="2024-01-15T14:30:45Z"
            )
    ```

        Note:
            All fields default to empty strings, allowing omission
            when commit info is unavailable (e.g., empty repository).
            Timestamp should use UTC timezone for consistency.
    """

    hash: str = ""
    message: str = ""
    author: str = ""
    timestamp: str = ""  # ISO8601 format for parseability


@dataclass
class RepoResult:
    """
        Per-repository result entry in the JSON payload.

        Comprehensive record of a single repository's processing result,
        including status, changes, remote state, and last commit. Forms
        the building block of the results array in OutputPayload.

        Required Attributes:
            path: Absolute filesystem path to repository
            name: Display name (typically directory name)
            status: Operation result (success/failed/skipped)

        Optional Attributes:
            branch: Current branch name (main, develop, feature/xyz)
            changes: Working directory change counts
            remote: Remote tracking information
            commit: Last commit metadata
            error: Error message if status is "failed"

        Status Values:
            - "success": Operation completed successfully
            - "failed": Operation encountered an error
            - "skipped": Repository was intentionally skipped

        Example:
    ```python
            result = RepoResult(
                path="/home/user/projects/myapp",
                name="myapp",
                status="success",
                branch="main",
                changes=RepoChanges(uncommitted=0, staged=3),
                commit=RepoCommit(
                    hash="abc123",
                    message="fix: resolve bug #42"
                ),
                error=None
            )
    ```

        Design:
            Uses default_factory for mutable defaults (dataclass requirement).
            Allows granular control over which fields are populated based
            on operation type (commit vs status vs pull).

        Note:
            Not all fields are relevant for all operations. For example,
            pull_repos may only populate path, name, status, and remote.
            Auto-commit operations populate all fields.
    """

    path: str
    name: str
    status: RepoStatusType
    branch: str = ""
    changes: RepoChanges = field(default_factory=RepoChanges)
    remote: RepoRemote = field(default_factory=RepoRemote)
    commit: RepoCommit = field(default_factory=RepoCommit)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Uses dataclasses.asdict() for automatic conversion of
        nested dataclasses. Preserves structure for JSON output.

        Returns:
            Nested dictionary with all fields serialized
        """
        return asdict(self)


@dataclass
class OutputPayload:
    """
        Top-level JSON payload for any Iskra operation.

        Standardized output structure for all Iskra commands, providing
        consistent format regardless of operation type. Includes summary
        statistics, per-repository results, and error tracking.

        Required Attributes:
            success: Overall operation success (True if all repos succeeded)
            operation: Operation type identifier (commit, status, pull, etc.)
            repos_total: Total number of repositories processed
            repos_success: Count of successfully processed repositories
            repos_failed: Count of failed repositories
            results: List of per-repository results

        Optional Attributes:
            errors: List of global error messages (not repo-specific)
            timestamp: ISO8601 timestamp of operation completion

        Operation Types:
            - "commit": Automated git commit operation
            - "status": Repository status check
            - "pull": GitHub repository cloning
            - "init": Configuration initialization
            - "exec": Custom command execution
            - "other": Miscellaneous operations

        Success Logic:
            success=True only if repos_failed==0 AND repos_total>0
            Empty operations (repos_total=0) can be success=True
            Single failure sets success=False for entire operation

        Example:
    ```python
            payload = OutputPayload(
                success=True,
                operation="commit",
                repos_total=10,
                repos_success=10,
                repos_failed=0,
                results=[
                    RepoResult(path="/path1", name="repo1", status="success"),
                    RepoResult(path="/path2", name="repo2", status="success"),
                    # ... 8 more
                ],
                errors=[],
                timestamp="2024-01-15T14:30:45.123456+00:00"
            )
    ```

        JSON Structure:
    ```json
            {
              "success": true,
              "operation": "commit",
              "repos_total": 10,
              "repos_success": 10,
              "repos_failed": 0,
              "timestamp": "2024-01-15T14:30:45.123456+00:00",
              "errors": [],
              "results": [
                {
                  "path": "/path/to/repo",
                  "name": "repo-name",
                  "status": "success",
                  "branch": "main",
                  ...
                }
              ]
            }
    ```

        Design Rationale:
            - Summary at top level for quick status checks
            - Detailed results in array for per-repo analysis
            - Timestamp for logging and correlation
            - Errors separate from results for clarity

        Note:
            Timestamp is automatically generated at payload creation using
            UTC timezone. Can be overridden by passing explicit value.
    """

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
        """
        Convert to dictionary for JSON serialization.

        Handles nested dataclass conversion, ensuring RepoResult
        objects are also converted to dictionaries. Preserves
        timestamp field explicitly.

        Returns:
            Fully serialized dictionary ready for json.dumps()

        Note:
            Uses asdict() for top level, then manually converts
            results list to ensure proper nesting.
        """
        data = asdict(self)
        data["timestamp"] = self.timestamp
        data["results"] = [r.to_dict() for r in self.results]
        return data


class BaseFormatter(ABC):
    """
    Abstract base formatter for output rendering.

    Defines the interface that all formatters must implement.
    Allows polymorphic handling of output - CLI code calls emit()
    without knowing whether it's JSON or console format.

    Strategy Pattern:
        Different formatters implement different output strategies,
        selected at runtime based on user preferences (--json flag).

    Subclasses:
        - JSONFormatter: Machine-readable JSON output
        - ConsoleFormatter: Human-readable console summary
        - Future: CSVFormatter, XMLFormatter, etc.

    Design:
        Abstract base class ensures all formatters have consistent
        interface. Client code (CLI modules) depends on abstraction,
        not concrete implementations.
    """

    @abstractmethod
    def emit(self, payload: OutputPayload) -> None:
        """
        Render the payload to stdout using the chosen format.

        Args:
            payload: Structured operation results to output

        Side Effects:
            Writes to stdout (or stderr for some formatters)

        Implementation:
            Concrete formatters must override this method to
            provide format-specific rendering logic.

        Note:
            Method never returns a value - output is side effect only.
            Allows formatters to write directly to console for
            streaming output without building large strings.
        """
        ...


class JSONFormatter(BaseFormatter):
    """
        Formatter that prints the payload as a single JSON object.

        Outputs structured, machine-readable JSON for automation, logging,
        and integration with other tools. Uses Rich's print_json for pretty
        formatting while maintaining valid JSON structure.

        Output Characteristics:
            - Single JSON object per operation
            - Pretty-printed with indentation
            - Valid JSON (parseable by any JSON parser)
            - UTF-8 encoded (ensure_ascii=False)
            - Includes all payload fields

        Example Output:
    ```json
            {
              "success": true,
              "operation": "commit",
              "repos_total": 5,
              "repos_success": 5,
              "repos_failed": 0,
              "timestamp": "2024-01-15T14:30:45.123456+00:00",
              "errors": [],
              "results": [...]
            }
    ```

        Use Cases:
            - CI/CD pipelines: Parse results for build success/failure
            - Logging systems: Structured logs for analysis
            - Monitoring: Feed into metrics/alerting systems
            - Scripting: Parse with jq, Python json module, etc.
            - Testing: Assert on structured output

        Console Handling:
            Uses Rich Console for output to support ANSI stripping
            when piping to files. Defaults to stdout (stderr=False).
    """

    def __init__(self, console: Optional[Console] = None) -> None:
        """
        Initialize JSON formatter with optional console.

        Args:
            console: Rich Console for output control
                    Defaults to new Console writing to stdout

        Note:
            Custom console allows testing and output redirection.
            Production code typically uses default.
        """
        self._console = console or Console(stderr=False)

    def emit(self, payload: OutputPayload) -> None:
        """
        Emit payload as pretty-printed JSON.

        Args:
            payload: Operation results to serialize

        Side Effects:
            Prints JSON to stdout via Rich console

        Implementation:
            1. Convert payload to dictionary
            2. Serialize to JSON string with UTF-8
            3. Pretty-print via Rich (adds syntax highlighting in terminal)

        Note:
            Rich's print_json maintains valid JSON while adding
            visual formatting. Output is still parseable by standard
            JSON parsers - color codes are only added to terminals.
        """
        # Convert structured payload to plain dict
        raw = json.dumps(payload.to_dict(), ensure_ascii=False)

        # print_json adds nice formatting but keeps it valid JSON
        # Syntax highlighting only appears in terminals, not when piped
        self._console.print_json(raw)


class ConsoleFormatter(BaseFormatter):
    """
        Formatter that prints a concise human-readable summary.

        Provides a brief text summary of operation results for human
        consumption. Designed to complement the detailed Rich UI output
        that appears during processing, adding only a final summary.

        Output Characteristics:
            - One-line summary of success/failure counts
            - Color-coded based on success (green) or failure (red)
            - Lists any global errors
            - Minimal, non-redundant with Rich UI

        Example Output:
    ```
            ─────────────── COMMIT summary ───────────────
            Repositories: 8/10 success, 2 failed

            Errors:
            - Repository not found: /path/to/missing
            - Permission denied: /path/to/locked
    ```

        Design Philosophy:
            Detailed Rich UI (progress bars, panels, tables) shows
            per-repository progress during operations. ConsoleFormatter
            only adds a brief final summary, avoiding duplication.

        Color Coding:
            - Green: All operations succeeded
            - Red: One or more operations failed

        Use Cases:
            - Interactive CLI usage (default mode)
            - Shell scripts checking exit codes
            - Quick status checks
            - Terminal sessions where JSON is overkill

        Contrast with JSONFormatter:
            - ConsoleFormatter: Human-readable, minimal, colorful
            - JSONFormatter: Machine-readable, complete, structured
    """

    def __init__(self, console: Optional[Console] = None) -> None:
        """
        Initialize console formatter with optional console.

        Args:
            console: Rich Console for styled output
                    Defaults to new Console with auto-detected settings

        Note:
            Auto-detection handles terminal capabilities, color
            support, and output redirection automatically.
        """
        self.console = console or Console()

    def emit(self, payload: OutputPayload) -> None:
        """
        Emit human-readable summary to console.

        Args:
            payload: Operation results to summarize

        Side Effects:
            Prints styled text to stdout via Rich console

        Output Structure:
            1. Horizontal rule with operation name
            2. Repository success/failure counts
            3. Error list (if any errors exist)

        Styling:
            - Border color: Green for success, red for failure
            - Bold text: For emphasis on key information
            - Errors: Red color for visibility

        Note:
            Keeps output minimal to avoid cluttering terminal
            after detailed Rich UI has already shown progress.
            Only adds high-level summary and error aggregation.
        """
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
    """
        Factory function returning the appropriate formatter.

        Selects between JSON and console formatters based on user
        preferences expressed through command-line flags. Implements
        the factory pattern for formatter creation.

        Args:
            json_mode: If True, return JSONFormatter for structured output
            quiet: If True, return JSONFormatter (quiet implies JSON-only)
            console: Optional Console instance to pass to formatter
                    Allows testing and output control

        Returns:
            JSONFormatter if json_mode or quiet is True
            ConsoleFormatter otherwise (default for interactive use)

        Selection Logic:
            - --json flag: User explicitly wants JSON
            - --quiet flag: Suppresses Rich UI, implies JSON-only output
            - Neither flag: Interactive mode, use console formatter

        Example Usage:
    ```python
            # In CLI module
            formatter = get_formatter(
                json_mode=args.json,
                quiet=args.quiet,
                console=console
            )

            # ... process repositories ...

            # Output results in chosen format
            formatter.emit(payload)
    ```

        Design Benefits:
            - Single point of control for formatter selection
            - Client code doesn't need to know formatter types
            - Easy to add new formatters (CSV, XML) in future
            - Testable: Can pass mock console for testing

        Note:
            quiet and json_mode both result in JSON output.
            This ensures --quiet truly suppresses all human-readable
            output, leaving only machine-parseable JSON.
    """
    if json_mode or quiet:
        return JSONFormatter(console=console)
    return ConsoleFormatter(console=console)
