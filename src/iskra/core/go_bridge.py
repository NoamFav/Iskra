"""
Bridge to the Go CLI binary.

This module handles calling the Go `iskra` binary and parsing results.
The Go binary handles all the heavy lifting (git ops, AI, scanning).
Python handles the UI and orchestration.
"""

import json
import os
import subprocess
import shutil
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


def find_go_binary() -> Optional[str]:
    """Find the iskra Go binary."""
    # Check in project bin first
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    )
    project_bin = os.path.join(project_root, "bin", "iskra")

    if os.path.isfile(project_bin) and os.access(project_bin, os.X_OK):
        return project_bin

    # Check in PATH
    return shutil.which("iskra-go")  # Renamed to avoid conflict with Python


GO_BINARY = find_go_binary()


class GoBridgeError(Exception):
    """Error from Go bridge."""
    pass


def is_go_available() -> bool:
    """Check if Go binary is available."""
    return GO_BINARY is not None


def call_go(
    command: str,
    *args: str,
    json_output: bool = True,
    timeout: int = 300,
    **kwargs
) -> Dict[str, Any]:
    """
    Call the Go binary and return parsed JSON.

    Args:
        command: The subcommand (commit, status, scan, etc.)
        *args: Positional arguments
        json_output: Whether to request JSON output
        timeout: Command timeout in seconds
        **kwargs: Keyword arguments (converted to --key=value flags)

    Returns:
        Parsed JSON response from Go binary

    Raises:
        GoBridgeError: If Go binary not found or command fails
    """
    if GO_BINARY is None:
        raise GoBridgeError(
            "iskra Go binary not found. "
            "Build it with: cd go-core && go build -o ../bin/iskra ./cmd/iskra"
        )

    cmd = [GO_BINARY]

    # Add JSON flag first if needed
    if json_output:
        cmd.append("--json")

    # Add command
    if command:
        cmd.append(command)

    # Add positional args
    cmd.extend(args)

    # Add keyword args as flags
    for key, value in kwargs.items():
        flag = f"--{key.replace('_', '-')}"
        if isinstance(value, bool):
            if value:
                cmd.append(flag)
        elif value is not None:
            cmd.append(f"{flag}={value}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode != 0 and result.stderr:
            # Check if it's just a non-critical issue
            if "zoxide" not in result.stderr.lower():
                raise GoBridgeError(f"Go CLI failed: {result.stderr}")

        if json_output:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                # Maybe there's stderr noise before the JSON
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.startswith('{') or line.startswith('['):
                        return json.loads(line)
                raise GoBridgeError(f"Invalid JSON from Go CLI: {result.stdout[:200]}")
        else:
            return {"output": result.stdout, "returncode": result.returncode}

    except subprocess.TimeoutExpired:
        raise GoBridgeError("Go CLI timed out")


# ============================================================================
# Data classes for structured results
# ============================================================================

@dataclass
class Changes:
    """Repository changes."""
    uncommitted: int = 0
    staged: int = 0
    untracked: int = 0
    total: int = 0

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> "Changes":
        if not data:
            return cls()
        return cls(
            uncommitted=data.get("uncommitted", 0),
            staged=data.get("staged", 0),
            untracked=data.get("untracked", 0),
            total=data.get("total", 0),
        )


@dataclass
class Remote:
    """Remote status."""
    ahead: int = 0
    behind: int = 0
    url: str = ""

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> "Remote":
        if not data:
            return cls()
        return cls(
            ahead=data.get("ahead", 0),
            behind=data.get("behind", 0),
            url=data.get("url", ""),
        )


@dataclass
class CommitInfo:
    """Commit information."""
    hash: str = ""
    message: str = ""
    is_ai: bool = False

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> Optional["CommitInfo"]:
        if not data:
            return None
        return cls(
            hash=data.get("hash", ""),
            message=data.get("message", ""),
            is_ai=data.get("is_ai", False),
        )


@dataclass
class Operation:
    """A single operation performed."""
    type: str = ""
    success: bool = False
    message: Optional[str] = None
    error: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict) -> "Operation":
        return cls(
            type=data.get("type", ""),
            success=data.get("success", False),
            message=data.get("message"),
            error=data.get("error"),
        )


@dataclass
class RepoResult:
    """Result of processing a single repository."""
    path: str = ""
    name: str = ""
    status: str = "unknown"  # success, failed, skipped
    branch: str = ""
    changes: Changes = field(default_factory=Changes)
    remote: Remote = field(default_factory=Remote)
    operations: List[Operation] = field(default_factory=list)
    elapsed_ms: int = 0
    is_protected: bool = False
    commit: Optional[CommitInfo] = None
    error: Optional[str] = None
    conflicts: Optional[List[str]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RepoResult":
        """Create from JSON dict."""
        return cls(
            path=data.get("path", ""),
            name=data.get("name", ""),
            status=data.get("status", "unknown"),
            branch=data.get("branch", ""),
            changes=Changes.from_dict(data.get("changes")),
            remote=Remote.from_dict(data.get("remote")),
            operations=[Operation.from_dict(op) for op in data.get("operations", [])],
            elapsed_ms=data.get("elapsed_ms", 0),
            is_protected=data.get("is_protected", False),
            commit=CommitInfo.from_dict(data.get("commit")),
            error=data.get("error"),
            conflicts=data.get("conflicts"),
        )


@dataclass
class BatchResult:
    """Result of processing multiple repositories."""
    success: bool = False
    operation: str = ""  # commit, status, pull
    repos_total: int = 0
    repos_success: int = 0
    repos_failed: int = 0
    results: List[RepoResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    elapsed_ms: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BatchResult":
        """Create from JSON dict."""
        return cls(
            success=data.get("success", False),
            operation=data.get("operation", ""),
            repos_total=data.get("repos_total", 0),
            repos_success=data.get("repos_success", 0),
            repos_failed=data.get("repos_failed", 0),
            results=[RepoResult.from_dict(r) for r in data.get("results", [])],
            errors=data.get("errors") or [],
            elapsed_ms=data.get("elapsed_ms", 0),
        )


# ============================================================================
# High-level API functions
# ============================================================================

def process_repos(
    repos: Optional[List[str]] = None,
    pulse: bool = False,
    scan_dir: Optional[str] = None,
    status_only: bool = False,
    pull_only: bool = False,
    pull: bool = False,
    no_push: bool = False,
    no_ai_commit: bool = False,
    commit_message: Optional[str] = None,
    dry_run: bool = False,
    only: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
) -> BatchResult:
    """
    Process repositories using Go CLI.

    Args:
        repos: List of repo paths to process (not used directly - Go uses config)
        pulse: Process current directory only
        scan_dir: Scan directory for repos
        status_only: Only show status
        pull_only: Only pull
        pull: Pull before commit
        no_push: Don't push
        no_ai_commit: Don't use AI
        commit_message: Custom commit message
        dry_run: Dry run mode
        only: Only patterns
        exclude: Exclude patterns

    Returns:
        BatchResult with all repo results
    """
    # Build command
    if pulse:
        command = "pulse"
    elif status_only:
        command = "status"
    else:
        command = "commit"

    kwargs = {}

    if status_only:
        kwargs["status_only"] = True
    if pull_only:
        kwargs["pull_only"] = True
    if pull:
        kwargs["pull"] = True
    if no_push:
        kwargs["no_push"] = True
    if no_ai_commit:
        kwargs["no_ai_commit"] = True
    if dry_run:
        kwargs["dry_run"] = True
    if commit_message:
        kwargs["message"] = commit_message
    if scan_dir:
        kwargs["scan"] = scan_dir
    if only:
        kwargs["only"] = ",".join(only)
    if exclude:
        kwargs["exclude"] = ",".join(exclude)

    data = call_go(command, **kwargs)
    return BatchResult.from_dict(data)


def scan_repos(
    base_dir: Optional[str] = None,
    max_depth: int = 3,
    only: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
) -> List[Dict[str, str]]:
    """
    Scan for git repositories using Go CLI.

    Returns:
        List of repo dicts with path, name, display_name
    """
    kwargs = {"depth": max_depth}

    if base_dir:
        kwargs["dir"] = base_dir
    if only:
        kwargs["only"] = ",".join(only)
    if exclude:
        kwargs["exclude"] = ",".join(exclude)

    data = call_go("scan", **kwargs)
    return data.get("repos") or []


def get_repo_info() -> Dict[str, Any]:
    """
    Get repository info (like onefetch) using Go CLI.

    Returns:
        Dict with repo statistics
    """
    return call_go("info")


def get_config() -> Dict[str, Any]:
    """
    Get current configuration from Go CLI.

    Returns:
        Dict with config info
    """
    return call_go("init")


def run_exec(
    command: str,
    repos: Optional[List[str]] = None,
    parallel: int = 1,
    fail_fast: bool = False,
    only: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Run a command across repositories using Go CLI.

    Args:
        command: Command to run
        repos: List of repo paths (uses tracked repos if None)
        parallel: Number of parallel workers
        fail_fast: Stop on first error
        only: Only patterns
        exclude: Exclude patterns

    Returns:
        Dict with execution results
    """
    kwargs = {}

    if parallel > 1:
        kwargs["p"] = parallel
    if fail_fast:
        kwargs["fail_fast"] = True
    if only:
        kwargs["only"] = ",".join(only)
    if exclude:
        kwargs["exclude"] = ",".join(exclude)

    return call_go("exec", command, **kwargs)


def sync_all(
    only: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
) -> BatchResult:
    """
    Pull all tracked repositories.

    Returns:
        BatchResult with sync results
    """
    kwargs = {}
    if only:
        kwargs["only"] = ",".join(only)
    if exclude:
        kwargs["exclude"] = ",".join(exclude)

    data = call_go("sync-all", **kwargs)
    return BatchResult.from_dict(data)


# ============================================================================
# Direct passthrough functions (for commands that don't need Python UI)
# ============================================================================

def run_go_cli(args: List[str], capture: bool = False) -> int:
    """
    Run the Go CLI directly with given arguments.

    This is useful for commands that should just passthrough to Go
    without any Python processing.

    Args:
        args: Command line arguments
        capture: Whether to capture output (default: passthrough to terminal)

    Returns:
        Exit code from Go CLI
    """
    if GO_BINARY is None:
        print("Error: iskra Go binary not found")
        return 1

    cmd = [GO_BINARY] + args

    if capture:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout, end='')
        if result.stderr:
            print(result.stderr, end='')
        return result.returncode
    else:
        return subprocess.run(cmd).returncode
