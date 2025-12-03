#!/usr/bin/env python3
""""""

import os
import subprocess
import argparse
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from iskra.config import ConfigManager, get_config
from iskra.ui.display import process_repository
from iskra.ui.formatting import print_header, get_icon
from iskra.core.repo_scanner import find_git_repos
from iskra.core.constants import ICONS

from iskra.output.formatter import (
    get_formatter,
    OutputPayload,
    RepoResult,
    RepoChanges,
    RepoRemote,
    RepoCommit,
)

# Initialize Rich console for terminal output
console = Console()


def main():
    """"""
    parser = argparse.ArgumentParser(
        description="Iskra - Intelligent Git automation with configuration management",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Configuration sources
    # Allow loading from custom config file or using system default
    parser.add_argument("--config", type=str, help="Path to config file")
    parser.add_argument("--profile", type=str, help="Use named profile")

    # Override config options
    # Command-line flags take precedence over config file settings
    parser.add_argument("--dir", type=str, help="Base directory (overrides config)")
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Scan for repos instead of using tracked repos",
    )

    # Git operations control
    # Fine-grained control over git workflow steps
    parser.add_argument("--pull", action="store_true", help="Pull before commit")
    parser.add_argument(
        "--no-push", action="store_true", help="Don't push after commit"
    )

    # Commit options
    # Customize commit behavior and message generation
    parser.add_argument("--commit-message", type=str, default="auto-commit")
    parser.add_argument(
        "--no-ai-commit", action="store_true", help="Don't use AI for commit messages"
    )

    # Filtering patterns
    # Glob-style patterns for selective repository processing
    parser.add_argument("--exclude", type=str, nargs="+", default=[])
    parser.add_argument("--only", type=str, nargs="+", default=[])

    # Safety and UI modes
    # Preview changes without applying them, or inspect status only
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without doing it",
    )
    parser.add_argument(
        "--status-only", action="store_true", help="Only show status, don't commit"
    )
    parser.add_argument(
        "-y", "--yes", action="store_true", help="Skip all confirmations"
    )
    parser.add_argument(
        "--show-diff", action="store_true", help="Show diff before committing"
    )

    # Special file handling
    # Automated cleanup and .gitignore management
    parser.add_argument("--handle-gitignore", action="store_true")
    parser.add_argument("--remove-ds-store", action="store_true")

    # Output mode control
    # Switch between human-friendly Rich UI and machine-readable JSON
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

    # Parse all command-line arguments
    args = parser.parse_args()

    # Determine output mode from flags
    json_mode = bool(getattr(args, "json", False))
    quiet = bool(getattr(args, "quiet", False))
    rich_enabled = not (json_mode or quiet)

    # Initialize appropriate output formatter
    formatter = get_formatter(json_mode=json_mode, quiet=quiet, console=console)

    # Load configuration from file or use system default
    # ConfigManager handles file discovery, parsing, and validation
    if args.config:
        config_manager = ConfigManager(args.config)
    else:
        config_manager = get_config()

    # Apply command-line overrides to configuration
    # This allows CLI flags to override config file settings
    config = config_manager.global_config

    # Directory override - useful for one-off operations
    if args.dir:
        config.base_dir = args.dir

    # Git operation overrides
    if args.pull:
        config.auto_pull = True
    if args.no_push:
        config.auto_push = False

    # AI commit message override
    if args.no_ai_commit:
        config.use_ai_commit = False

    # Safety mode overrides
    if args.dry_run:
        config.dry_run = True
    if args.yes:
        config.require_confirmation = False
    if args.show_diff:
        config.show_diff = True

    # Filter pattern overrides - extend existing patterns
    if args.exclude:
        config.exclude_patterns.extend(args.exclude)
    if args.only:
        config.only_patterns.extend(args.only)

    # Expand ~ in base directory path and store original working directory
    base_dir = os.path.expanduser(config.base_dir)
    orig_cwd = os.getcwd()

    # Display application header (Rich UI only)
    if rich_enabled:
        print_header("Git Repository Manager")

    # Show dry-run warning banner
    # Important visual indicator that no changes will be made
    if config.dry_run and rich_enabled:
        console.print(
            Panel(
                "[bold yellow]DRY RUN MODE[/]\n"
                "No changes will be made to repositories",
                border_style="yellow",
                title="⚠️  Warning",
            )
        )

    # Show status-only mode indicator
    # Clarifies that inspection only, no modifications
    if args.status_only and rich_enabled:
        console.print(
            Panel(
                "[bold cyan]STATUS ONLY MODE[/]\n"
                "Will only display repository status",
                border_style="cyan",
                title="ℹ️  Info",
            )
        )

    # Get repositories - smart default behavior
    # Prefer tracked repos unless --scan is explicitly requested
    tracked_repos = config_manager.get_all_repos(active_only=True)

    # Determine repository discovery method
    # --scan forces filesystem scan, otherwise use tracked repos if available
    if args.scan or not tracked_repos:
        # Scan filesystem for git repositories
        if rich_enabled:
            console.print("[bold blue]Scanning for Git repositories...[/]")

        # Find all git repositories matching filters
        # Respects max_depth, symlinks, include/exclude patterns
        git_repo_paths = find_git_repos(
            base_dir=base_dir,
            only=config.only_patterns,
            exclude=config.exclude_patterns,
            max_depth=config.max_depth,
            followlinks=config.follow_symlinks,
        )

        # Convert paths to (path, relative_name) tuples for display
        git_repos = [(path, os.path.relpath(path, base_dir)) for path in git_repo_paths]

        # Handle case where no repositories found during scan
        if not args.scan and not git_repos:
            if rich_enabled:
                console.print(
                    f"\n[yellow]{get_icon('warning')} No repositories found[/]"
                )
                console.print(f"[dim]Run 'iskra-init init' to track repositories[/]")

            # Emit empty result payload
            payload = OutputPayload(
                success=True,  # Not an error, just no repos
                operation="status" if args.status_only else "commit",
                repos_total=0,
                repos_success=0,
                repos_failed=0,
                results=[],
                errors=[],
            )
            formatter.emit(payload)
            return
    else:
        # Use tracked repositories from configuration
        if rich_enabled:
            console.print(
                f"[bold blue]Using {len(tracked_repos)} tracked repositories[/]"
            )

        # Apply filters to tracked repos
        # Filter in-memory rather than re-scanning filesystem
        git_repos = []
        for repo_info in tracked_repos:
            repo_path = repo_info.path
            repo_name = repo_info.name

            # Apply include patterns (whitelist)
            # If patterns specified, repo must match at least one
            if config.only_patterns:
                from fnmatch import fnmatch

                if not any(fnmatch(repo_name, pat) for pat in config.only_patterns):
                    continue

            # Apply exclude patterns (blacklist)
            # If repo matches any exclude pattern, skip it
            if config.exclude_patterns:
                from fnmatch import fnmatch

                if any(fnmatch(repo_name, pat) for pat in config.exclude_patterns):
                    continue

            git_repos.append((repo_path, repo_name))

        if rich_enabled:
            console.print(
                f"[bold green]Selected {len(git_repos)} repositories after filters[/]"
            )

    # Display processing summary
    # Provides overview before starting potentially lengthy operations
    if rich_enabled:
        summary_panel = Panel(
            f"{get_icon('folder')} Found [bold green]{len(git_repos)}[/] repositories to process",
            title="Repository Summary",
            border_style="blue",
        )
        console.print(summary_panel)

    # Require confirmation if enabled in config
    # Safety check before bulk operations unless --yes flag is set
    if config.require_confirmation and not args.yes:
        if rich_enabled:
            if not Confirm.ask(f"Process {len(git_repos)} repositories?", default=True):
                console.print("[yellow]Cancelled[/]")

                # User cancelled - emit cancellation payload
                payload = OutputPayload(
                    success=False,
                    operation="status" if args.status_only else "commit",
                    repos_total=len(git_repos),
                    repos_success=0,
                    repos_failed=0,
                    results=[],
                    errors=["cancelled_by_user"],
                )
                formatter.emit(payload)
                return
        else:
            # Non-interactive mode (JSON/quiet): treat as auto-yes
            # Cannot prompt for confirmation without Rich UI
            pass

    # Begin repository processing
    if rich_enabled:
        console.print(f"[bold blue]Processing {len(git_repos)} repositories...[/]\n")

    # Initialize result tracking
    success_count = 0
    repo_results = []

    # Process each repository sequentially
    # TODO: Consider adding parallel processing option for large repository sets
    for idx, (repo_path, display_name) in enumerate(git_repos, 1):
        if rich_enabled:
            console.print(f"\n[bold cyan]Repository {idx}/{len(git_repos)}:[/]")

        # Get repo-specific configuration merged with global config
        # Allows per-repository overrides of global settings
        repo_config = config_manager.merge_config(repo_path)

        # Optimization: Skip repositories without changes if configured
        # Avoids unnecessary processing for repos with no modifications
        if config.skip_repos_without_changes:
            # Check git status to detect changes
            os.chdir(repo_path)
            result = subprocess.run(
                ["git", "status", "--porcelain"], capture_output=True, text=True
            )
            if not result.stdout.strip():
                if rich_enabled:
                    console.print(f"[dim]{get_icon('info')} No changes, skipping[/]")
                os.chdir(orig_cwd)

                # Record as skipped in results
                repo_results.append(
                    RepoResult(
                        path=repo_path,
                        name=display_name,
                        status="skipped",
                    )
                )
                continue

        # Create arguments object for process_repository
        # Bridges between command-line args and function interface
        class RepoArgs:
            """"""

            def __init__(self, config, args_orig):
                self.pull = config.auto_pull
                self.handle_gitignore = args_orig.handle_gitignore
                self.remove_ds_store = args_orig.remove_ds_store
                self.use_ai_commit = config.use_ai_commit
                self.commit_message = args_orig.commit_message
                self.dry_run = config.dry_run
                self.status_only = args_orig.status_only
                self.show_diff = config.show_diff
                self.auto_push = config.auto_push

        repo_args = RepoArgs(repo_config, args)

        # Process the repository with all git operations
        # Returns True if successful, False if any operation failed
        ok = process_repository(
            entry_path=repo_path,
            entry=display_name,
            args=repo_args,
            task_id=None,  # Not using progress bar here
            progress=None,  # Sequential processing without progress widget
            orig_cwd=orig_cwd,
        )

        if ok:
            success_count += 1

            # Update tracked repo metadata if using tracked repos
            # Keeps configuration in sync with actual repository state
            if not args.scan and tracked_repos:
                result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    capture_output=True,
                    text=True,
                    cwd=repo_path,
                )
                if result.returncode == 0:
                    # Update last commit hash in config
                    config_manager.update_repo(
                        repo_path, last_commit=result.stdout.strip()
                    )

        # Record result for JSON output
        # Note: Could be enhanced with more detailed stats (files changed, etc.)
        repo_results.append(
            RepoResult(
                path=repo_path,
                name=display_name,
                status="success" if ok else "failed",
                # TODO: Fill branch/commit/remote info for richer output
            )
        )

    # Display final summary (Rich UI only)
    # Color-coded based on success rate: green if all succeeded, yellow otherwise
    if rich_enabled:
        console.print()
        final_panel = Panel(
            f"{get_icon('sparkles')} [bold]{success_count}/{len(git_repos)}[/] repositories processed successfully {get_icon('sparkles')}",
            border_style="green" if success_count == len(git_repos) else "yellow",
            title="Processing Complete",
            title_align="center",
        )
        console.print(final_panel)

    # Log operation to file for audit trail
    # Maintains historical record of all Iskra runs
    log_file = config_manager.get_log_file("iskra")

    with open(log_file, "a") as f:
        # Write structured log entry with divider
        f.write(f"\n{'='*80}\n")
        f.write(f"Run at: {datetime.now().isoformat()}\n")
        f.write(f"Processed: {success_count}/{len(git_repos)} repositories\n")
        f.write(f"Base dir: {base_dir}\n")
        if config.dry_run:
            f.write("Mode: DRY RUN\n")
        f.write(f"{'='*80}\n")

    # Build and emit final output payload
    # Success is True only if ALL repositories processed successfully
    payload = OutputPayload(
        success=(success_count == len(git_repos)),
        operation="status" if args.status_only else "commit",
        repos_total=len(git_repos),
        repos_success=success_count,
        repos_failed=len(git_repos) - success_count,
        results=repo_results,
        errors=[],  # Could be enhanced with per-repo error messages
    )
    formatter.emit(payload)


# Standard Python idiom for script execution
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        console.print("\n[bold red]Operation canceled by user[/]")
    except Exception:
        # Catch-all exception handler with Rich traceback
        console.print_exception()
