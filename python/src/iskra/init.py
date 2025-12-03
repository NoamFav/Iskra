#!/usr/bin/env python3
""""""

import os
import subprocess
import argparse
from pathlib import Path
from typing import List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.prompt import Confirm, Prompt

from iskra.config import ConfigManager, RepoInfo, GlobalConfig
from iskra.core.repo_scanner import find_git_repos
from iskra.ui.formatting import get_icon

from iskra.output.formatter import (
    get_formatter,
    OutputPayload,
    RepoResult,
    RepoRemote,
    RepoCommit,
)

# Initialize Rich console for pretty terminal output
console = Console()


def get_git_info(repo_path: str) -> dict:
    """"""
    # Store original directory to restore later
    original_dir = os.getcwd()
    os.chdir(repo_path)

    try:
        # Get remote URL - typically points to GitHub, GitLab, etc.
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"], capture_output=True, text=True
        )
        remote_url = result.stdout.strip() if result.returncode == 0 else None

        # Get default branch - the branch HEAD currently points to
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True
        )
        default_branch = result.stdout.strip() if result.returncode == 0 else None

        # Get last commit hash - unique identifier for the latest commit
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True
        )
        last_commit = result.stdout.strip() if result.returncode == 0 else None

        return {
            "remote_url": remote_url,
            "default_branch": default_branch,
            "last_commit": last_commit,
        }
    finally:
        # Always restore original directory, even if git commands fail
        os.chdir(original_dir)


def scan_repositories(base_dir: str, config: GlobalConfig) -> List[str]:
    """"""
    console.print(
        f"\n[bold blue]{get_icon('folder')} Scanning for repositories in {base_dir}...[/]"
    )

    # Delegate actual scanning to core module with configured filters
    repos = find_git_repos(
        base_dir=base_dir,
        only=config.only_patterns,
        exclude=config.exclude_patterns,
        max_depth=config.max_depth,
        followlinks=config.follow_symlinks,
    )

    console.print(
        f"[bold green]{get_icon('success')} Found {len(repos)} repositories[/]\n"
    )
    return repos


def display_repo_table(repos: List[RepoInfo]):
    """"""
    table = Table(
        title=f"{get_icon('project')} Tracked Repositories",
        show_header=True,
        header_style="bold cyan",
    )

    # Define table columns with appropriate styling
    table.add_column("Name", style="cyan")
    table.add_column("Path", style="white")
    table.add_column("Branch", style="yellow")
    table.add_column("Remote", style="blue")
    table.add_column("Status", style="green")

    for repo in repos:
        # Format active status with appropriate icon and color
        status = "✓ Active" if repo.active else "✗ Inactive"
        status_style = "green" if repo.active else "red"

        # Truncate remote URL for display readability
        remote = repo.remote_url or "N/A"
        if len(remote) > 50:
            remote = remote[:47] + "..."

        table.add_row(
            repo.name,
            repo.path,
            repo.default_branch or "N/A",
            remote,
            f"[{status_style}]{status}[/]",
        )

    console.print(table)


def init_command(args, formatter, json_mode: bool, quiet: bool):
    """"""
    # Determine if Rich UI is enabled based on output mode
    rich_enabled = not (json_mode or quiet)

    if rich_enabled:
        # Display welcome banner with version info
        console.print(
            Panel(
                "[bold white]Iskra Initialization[/]",
                border_style="cyan",
                title="[bold blue]Setup[/]",
                subtitle=f"[dim]Version 1.0.0[/]",
            )
        )

    # Load existing config or create new one
    config_manager = ConfigManager()

    # Override base directory from command line if provided
    if args.base_dir:
        config_manager.global_config.base_dir = args.base_dir

    base_dir = Path(config_manager.global_config.base_dir).expanduser()

    # Confirm base directory with user unless --yes flag is set
    if rich_enabled and not args.yes:
        console.print(f"\n[bold]Base directory:[/] {base_dir}")
        if not Confirm.ask("Is this correct?", default=True):
            new_base = Prompt.ask("Enter base directory path")
            base_dir = Path(new_base).expanduser()
            config_manager.global_config.base_dir = str(base_dir)

    # Ensure base directory exists, create if necessary
    if not base_dir.exists():
        if rich_enabled:
            console.print(
                f"[yellow]{get_icon('warning')} Base directory does not exist: {base_dir}[/]"
            )
        # Auto-create in --yes mode or with user confirmation
        if args.yes or not rich_enabled or Confirm.ask("Create it?", default=True):
            base_dir.mkdir(parents=True, exist_ok=True)
            if rich_enabled:
                console.print(f"[green]{get_icon('success')} Created directory[/]")
        else:
            # User declined to create directory - abort initialization
            if rich_enabled:
                console.print("[red]Cancelled[/]")
            payload = OutputPayload(
                success=False,
                operation="init",
                repos_total=0,
                repos_success=0,
                repos_failed=0,
                results=[],
                errors=["base_dir_missing"],
            )
            formatter.emit(payload)
            return

    # Configure settings interactively if not using --yes flag
    if rich_enabled and not args.yes:
        console.print("\n[bold cyan]Configuration Options[/]")

        # Max depth - how deep to recurse when scanning for repos
        if Confirm.ask(
            f"Change max scan depth? (current: {config_manager.global_config.max_depth})",
            default=False,
        ):
            depth = Prompt.ask(
                "Max depth", default=str(config_manager.global_config.max_depth)
            )
            config_manager.global_config.max_depth = int(depth)

        # AI commit - whether to use AI for generating commit messages
        config_manager.global_config.use_ai_commit = Confirm.ask(
            "Use AI-generated commit messages?",
            default=config_manager.global_config.use_ai_commit,
        )

        # Auto push - automatically push commits to remote
        config_manager.global_config.auto_push = Confirm.ask(
            "Automatically push after commit?",
            default=config_manager.global_config.auto_push,
        )

        # Require confirmation - safety check before destructive operations
        config_manager.global_config.require_confirmation = Confirm.ask(
            "Require confirmation before operations?",
            default=config_manager.global_config.require_confirmation,
        )

    # Persist global configuration to disk
    config_manager.save_global_config(config_manager.global_config)

    # Scan for repositories - use Rich version if UI enabled, silent otherwise
    if rich_enabled:
        repo_paths = scan_repositories(str(base_dir), config_manager.global_config)
    else:
        # Direct scan without UI feedback for JSON/quiet modes
        repo_paths = find_git_repos(
            base_dir=str(base_dir),
            only=config_manager.global_config.only_patterns,
            exclude=config_manager.global_config.exclude_patterns,
            max_depth=config_manager.global_config.max_depth,
            followlinks=config_manager.global_config.follow_symlinks,
        )

    # Handle case where no repositories were found
    if not repo_paths:
        if rich_enabled:
            console.print(f"[yellow]{get_icon('warning')} No repositories found[/]")
        payload = OutputPayload(
            success=True,  # Not an error - just no repos to track
            operation="init",
            repos_total=0,
            repos_success=0,
            repos_failed=0,
            results=[],
            errors=[],
        )
        formatter.emit(payload)
        return

    # Display found repositories preview (first 5)
    if rich_enabled:
        console.print(f"\n[bold]Found {len(repo_paths)} repositories:[/]")
        for i, path in enumerate(repo_paths[:5], 1):
            rel_path = os.path.relpath(path, base_dir)
            console.print(f"  {i}. {rel_path}")

        if len(repo_paths) > 5:
            console.print(f"  ... and {len(repo_paths) - 5} more")

    # Confirm tracking with user unless auto-accepted
    if (
        rich_enabled
        and not args.yes
        and not Confirm.ask(
            f"\nTrack these {len(repo_paths)} repositories?", default=True
        )
    ):
        console.print("[yellow]Cancelled[/]")
        payload = OutputPayload(
            success=False,
            operation="init",
            repos_total=len(repo_paths),
            repos_success=0,
            repos_failed=0,
            results=[],
            errors=["cancelled_by_user"],
        )
        formatter.emit(payload)
        return

    # Track repositories with progress indicator
    tracked_count = 0
    tracked_results = []

    if rich_enabled:
        # Rich progress bar for visual feedback
        console.print()
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            task = progress.add_task("Tracking repositories...", total=len(repo_paths))

            for repo_path in repo_paths:
                name = os.path.basename(repo_path)
                # Extract git metadata for this repository
                git_info = get_git_info(repo_path)

                # Create repository info object
                repo_info = RepoInfo(
                    path=repo_path,
                    name=name,
                    remote_url=git_info.get("remote_url"),
                    default_branch=git_info.get("default_branch"),
                    last_commit=git_info.get("last_commit"),
                )

                # Add to config and track success
                if config_manager.add_repo(repo_info):
                    tracked_count += 1
                    tracked_results.append(
                        RepoResult(
                            path=repo_info.path,
                            name=repo_info.name,
                            status="success",
                            branch=repo_info.default_branch or "",
                            remote=RepoRemote(
                                url=repo_info.remote_url or "",
                                ahead=0,
                                behind=0,
                            ),
                            commit=RepoCommit(
                                hash=repo_info.last_commit or "",
                                message="",
                                author="",
                                timestamp="",
                            ),
                        )
                    )

                progress.update(task, advance=1)
    else:
        # Silent tracking for JSON/quiet modes
        for repo_path in repo_paths:
            name = os.path.basename(repo_path)
            git_info = get_git_info(repo_path)

            repo_info = RepoInfo(
                path=repo_path,
                name=name,
                remote_url=git_info.get("remote_url"),
                default_branch=git_info.get("default_branch"),
                last_commit=git_info.get("last_commit"),
            )

            if config_manager.add_repo(repo_info):
                tracked_count += 1
                tracked_results.append(
                    RepoResult(
                        path=repo_info.path,
                        name=repo_info.name,
                        status="success",
                        branch=repo_info.default_branch or "",
                        remote=RepoRemote(
                            url=repo_info.remote_url or "",
                            ahead=0,
                            behind=0,
                        ),
                        commit=RepoCommit(
                            hash=repo_info.last_commit or "",
                            message="",
                            author="",
                            timestamp="",
                        ),
                    )
                )

    # Display success message and optional repo table
    if rich_enabled:
        console.print(
            f"\n[bold green]{get_icon('success')} Successfully tracked {tracked_count} repositories![/]\n"
        )

        # Show tracked repos table if requested or confirmed
        if args.show_repos or (
            not args.yes and Confirm.ask("Show tracked repositories?", default=True)
        ):
            display_repo_table(config_manager.get_all_repos())

        # Display config file locations for reference
        console.print(f"\n[dim]Configuration saved to: {config_manager.config_dir}[/]")
        console.print(f"[dim]  • Config: {config_manager.config_file}[/]")
        console.print(f"[dim]  • Repos:  {config_manager.repos_file}[/]")
        console.print(f"[dim]  • Logs:   {config_manager.logs_dir}[/]")

    # Emit JSON payload for machine consumption
    payload = OutputPayload(
        success=(tracked_count > 0),
        operation="init",
        repos_total=len(repo_paths),
        repos_success=tracked_count,
        repos_failed=len(repo_paths) - tracked_count,
        results=tracked_results,
        errors=[],
    )
    formatter.emit(payload)


def list_command(args, formatter, json_mode: bool, quiet: bool):
    """"""
    rich_enabled = not (json_mode or quiet)
    config_manager = ConfigManager()
    # Load repos, optionally filtering to active only
    repos = config_manager.get_all_repos(active_only=not args.all)

    # Handle empty repository list
    if not repos:
        if rich_enabled:
            console.print(
                f"[yellow]{get_icon('warning')} No tracked repositories found[/]"
            )
            console.print(f"\n[dim]Run 'iskra init' to scan and track repositories[/]")

        payload = OutputPayload(
            success=True,
            operation="status",
            repos_total=0,
            repos_success=0,
            repos_failed=0,
            results=[],
            errors=[],
        )
        formatter.emit(payload)
        return

    # Display Rich table if UI is enabled
    if rich_enabled:
        display_repo_table(repos)

    # Build result list for JSON output
    results = []
    for repo in repos:
        results.append(
            RepoResult(
                path=repo.path,
                name=repo.name,
                status="success" if repo.active else "skipped",
                branch=repo.default_branch or "",
                remote=RepoRemote(
                    url=repo.remote_url or "",
                    ahead=0,
                    behind=0,
                ),
                commit=RepoCommit(
                    hash=repo.last_commit or "",
                    message="",
                    author="",
                    timestamp=repo.last_updated or "",
                ),
            )
        )

    # Emit payload (JSON or Rich depending on formatter)
    payload = OutputPayload(
        success=True,
        operation="status",
        repos_total=len(repos),
        repos_success=len(repos),
        repos_failed=0,
        results=results,
        errors=[],
    )
    formatter.emit(payload)


def add_command(args, formatter, json_mode: bool, quiet: bool):
    """"""
    rich_enabled = not (json_mode or quiet)
    config_manager = ConfigManager()
    # Expand ~ and resolve to absolute path for consistency
    repo_path = Path(args.path).expanduser().resolve()

    # Validate that path contains a git repository
    # Check for both .git directory and .git file (submodules)
    if not (repo_path / ".git").exists() and not (repo_path / ".git").is_file():
        if rich_enabled:
            console.print(
                f"[red]{get_icon('error')} Not a git repository: {repo_path}[/]"
            )
        payload = OutputPayload(
            success=False,
            operation="init",
            repos_total=1,
            repos_success=0,
            repos_failed=1,
            results=[
                RepoResult(
                    path=str(repo_path),
                    name=repo_path.name,
                    status="failed",
                )
            ],
            errors=["not_a_git_repository"],
        )
        formatter.emit(payload)
        return

    # Extract git metadata from the repository
    git_info = get_git_info(str(repo_path))

    # Create repository info object with extracted metadata
    repo_info = RepoInfo(
        path=str(repo_path),
        name=repo_path.name,
        remote_url=git_info.get("remote_url"),
        default_branch=git_info.get("default_branch"),
        last_commit=git_info.get("last_commit"),
    )

    # Attempt to add repository to config
    # Returns False if already tracked
    added = config_manager.add_repo(repo_info)

    if rich_enabled:
        if added:
            console.print(
                f"[green]{get_icon('success')} Added repository: {repo_path.name}[/]"
            )
        else:
            console.print(
                f"[yellow]{get_icon('warning')} Repository already tracked[/]"
            )

    # Emit result payload
    payload = OutputPayload(
        success=bool(added),
        operation="init",
        repos_total=1,
        repos_success=1 if added else 0,
        repos_failed=0 if added else 1,
        results=[
            RepoResult(
                path=repo_info.path,
                name=repo_info.name,
                status="success" if added else "failed",
                branch=repo_info.default_branch or "",
                remote=RepoRemote(
                    url=repo_info.remote_url or "",
                    ahead=0,
                    behind=0,
                ),
                commit=RepoCommit(
                    hash=repo_info.last_commit or "",
                    message="",
                    author="",
                    timestamp="",
                ),
            )
        ],
        errors=[] if added else ["already_tracked"],
    )
    formatter.emit(payload)


def remove_command(args, formatter, json_mode: bool, quiet: bool):
    """"""
    rich_enabled = not (json_mode or quiet)
    config_manager = ConfigManager()
    # Expand and resolve path for consistent lookup
    repo_path = Path(args.path).expanduser().resolve()

    # Attempt to remove from config
    # Returns False if not currently tracked
    removed = config_manager.remove_repo(str(repo_path))

    if rich_enabled:
        if removed:
            console.print(
                f"[green]{get_icon('success')} Removed repository: {repo_path}[/]"
            )
        else:
            console.print(f"[yellow]{get_icon('warning')} Repository not tracked[/]")

    # Emit result payload
    payload = OutputPayload(
        success=bool(removed),
        operation="init",
        repos_total=1,
        repos_success=1 if removed else 0,
        repos_failed=0 if removed else 1,
        results=[
            RepoResult(
                path=str(repo_path),
                name=repo_path.name,
                status="success" if removed else "failed",
            )
        ],
        errors=[] if removed else ["not_tracked"],
    )
    formatter.emit(payload)


def main():
    """"""
    parser = argparse.ArgumentParser(
        description="Initialize and manage Iskra configuration",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Global output flags available to all commands
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON instead of Rich UI.",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress Rich UI and output only JSON.",
    )

    # Create subparser for commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Init command - full initialization workflow
    init_parser = subparsers.add_parser(
        "init", help="Initialize configuration and scan for repos"
    )
    init_parser.add_argument("--base-dir", type=str, help="Base directory to scan")
    init_parser.add_argument(
        "-y", "--yes", action="store_true", help="Accept all defaults"
    )
    init_parser.add_argument(
        "--show-repos", action="store_true", help="Show tracked repos after init"
    )

    # List command - display tracked repositories
    list_parser = subparsers.add_parser("list", help="List tracked repositories")
    list_parser.add_argument(
        "--all", action="store_true", help="Include inactive repos"
    )

    # Add command - track a single repository
    add_parser = subparsers.add_parser("add", help="Add a repository to tracking")
    add_parser.add_argument("path", help="Path to git repository")

    # Remove command - untrack a repository
    remove_parser = subparsers.add_parser(
        "remove", help="Remove a repository from tracking"
    )
    remove_parser.add_argument("path", help="Path to git repository")

    # Parse command-line arguments
    args = parser.parse_args()

    # Determine output mode from flags
    json_mode = bool(getattr(args, "json", False))
    quiet = bool(getattr(args, "quiet", False))
    # Initialize appropriate formatter (Rich or JSON)
    formatter = get_formatter(json_mode=json_mode, quiet=quiet, console=console)

    # Dispatch to appropriate command handler
    if args.command == "init":
        init_command(args, formatter, json_mode, quiet)
    elif args.command == "list":
        list_command(args, formatter, json_mode, quiet)
    elif args.command == "add":
        add_command(args, formatter, json_mode, quiet)
    elif args.command == "remove":
        remove_command(args, formatter, json_mode, quiet)
    else:
        # No command specified - display help
        # No JSON emission here intentionally - help is for humans
        console.print(parser.format_help())


# Standard Python idiom for script execution
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        console.print("\n[bold red]Operation cancelled by user[/]")
    except Exception:
        # Catch-all for unexpected errors - print traceback with Rich
        console.print_exception()
