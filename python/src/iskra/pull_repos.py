#!/usr/bin/env python3
"""
Main entry point for pull_repos (GitHub cloning).

This module provides a command-line interface for bulk cloning GitHub repositories
with filtering capabilities, progress visualization, and dual output modes (Rich UI
and JSON). It fetches repositories via GitHub's GraphQL API and manages the cloning
process with detailed status reporting.
"""

import os
import argparse
import argcomplete
from rich.console import Console
from rich.panel import Panel
from rich.traceback import install as install_traceback

from .ui.formatting import print_header, get_icon
from .ui.tables import create_config_table
from .github.api import get_github_repos
from .github.clone import process_repository
from .output.formatter import (
    get_formatter,
    OutputPayload,
    RepoResult,
    RepoStatusType,
    RepoRemote,
)

# Install enhanced traceback handler with local variable display
# Provides better debugging information when exceptions occur
install_traceback(show_locals=True)

# Initialize Rich console for terminal output
console = Console()


def main():
    """
    Main function with enhanced CLI and visualization.

    Orchestrates the complete workflow for bulk GitHub repository cloning:
    1. Parses command-line arguments with autocomplete support
    2. Configures output formatter (Rich UI or JSON)
    3. Displays configuration summary
    4. Fetches repositories from GitHub API with filters
    5. Processes each repository (clone/update)
    6. Reports results in requested format

    Exit Codes:
        0: All repositories processed successfully
        1: One or more repositories failed (or exception occurred)
        130: User interrupted with Ctrl+C

    Note:
        Authentication is handled via GITHUB_TOKEN environment variable.
        See github.api module for authentication details.
    """
    parser = argparse.ArgumentParser(
        description="Clone GitHub repositories with rich visual interface.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Base directory where repositories will be cloned
    # Defaults to ~/Neoware, expanduser() handles ~ expansion
    parser.add_argument(
        "--base-dir",
        type=str,
        default=os.path.expanduser("~/Neoware"),
        help="Base directory where repositories will be cloned.",
    )

    # API fetch limit to prevent excessive requests
    # GraphQL API pagination is handled internally
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Maximum number of repositories to fetch.",
    )

    # Fork filtering - useful for focusing on original repos only
    parser.add_argument(
        "--filter-forks", action="store_true", help="Filter out forked repositories."
    )

    # Star-based filtering for quality/popularity threshold
    # 0 means include all repositories regardless of stars
    parser.add_argument(
        "--only-stars",
        type=int,
        default=0,
        help="Only clone repositories with at least this many stars.",
    )

    # Exclusion patterns support glob syntax (*, ?, [])
    # Applied to repository names for flexible filtering
    parser.add_argument(
        "--exclude",
        type=str,
        nargs="+",
        default=[],
        help="List of repository name patterns to exclude (supports glob patterns).",
    )

    # JSON output mode for scripting and automation
    # Suppresses Rich UI and outputs structured data
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON instead of Rich UI.",
    )

    # Quiet mode - suppress all output except JSON
    # Useful for background processing and logging
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress Rich UI and output only JSON.",
    )

    # Parse arguments and enable bash/zsh autocomplete
    args = parser.parse_args()
    argcomplete.autocomplete(parser)

    # Extract base directory from parsed args
    base_dir = args.base_dir

    # Initialize output formatter based on requested mode
    # Formatter abstracts Rich/JSON output differences
    formatter = get_formatter(json_mode=args.json, quiet=args.quiet, console=console)

    # Display application header with branding
    # Only shown in Rich UI mode, suppressed for JSON/quiet
    print_header("GitHub Repository Clone Manager", title="GitHub Clone Manager")

    # Create and display configuration summary table
    # Shows all active filters and settings before processing
    config_table = create_config_table(args, for_pull_repos=True)
    console.print(config_table)

    # Ensure base directory exists, create if necessary
    # Parent directories are created automatically
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
        console.print(
            f"[cyan]{get_icon('folder')} Created base directory at {base_dir}"
        )

    # Fetch repositories from GitHub GraphQL API
    # Applies all configured filters (forks, stars, exclusions)
    # Returns list of repository dictionaries with metadata
    repositories = get_github_repos(
        limit=args.limit,
        filter_forks=args.filter_forks,
        only_stars=args.only_stars,
        exclude=args.exclude,
    )

    # Initialize result tracking variables
    repo_results: list[RepoResult] = []  # Detailed results for JSON output
    errors: list[str] = []  # Global error messages
    success_count = 0  # Counter for successful operations
    total = len(repositories)  # Total repositories to process

    # Display processing summary (Rich UI only)
    # Provides overview before starting lengthy clone operations
    if not (args.json or args.quiet):
        summary_panel = Panel(
            f"{get_icon('github')} Found [bold green]{total}[/] repositories to process\n"
            + f"{get_icon('folder')} Target directory: [bold blue]{base_dir}[/]",
            title="Repository Summary",
            border_style="blue",
        )
        console.print(summary_panel)

    # Process repositories if any were found
    if repositories:
        if not (args.json or args.quiet):
            console.print(f"[bold blue]Processing {total} repositories...[/]")

        # Process each repository sequentially
        # Enumeration starts at 1 for human-friendly progress display
        for idx, repo in enumerate(repositories, 1):
            # Process repository (clone or update)
            # Returns True if operation succeeded, False otherwise
            ok = process_repository(repo, base_dir, total, idx)

            if ok:
                success_count += 1

            # Determine status for result payload
            status: RepoStatusType = "success" if ok else "failed"

            # Extract repository name with fallback logic
            # Handles both 'name' and 'nameWithOwner' fields from API
            repo_name = repo.get("name", "")
            repo_short_name = repo_name or repo.get("nameWithOwner", "").split("/")[-1]

            # Construct full path where repository was/would be cloned
            repo_path = os.path.join(base_dir, repo_short_name)

            # Build result object for this repository
            # Note: For pure clone operations, branch/changes/commit remain default
            # These fields are populated by auto-commit operations in other modules
            repo_results.append(
                RepoResult(
                    path=repo_path,
                    name=repo_name or repo_short_name,
                    status=status,
                    # branch/changes/commit remain default for pure clone operations
                    # These would be populated if we were doing commit operations
                    remote=RepoRemote(
                        url=repo.get("url", ""),
                        ahead=0,  # Not checked during clone
                        behind=0,  # Not checked during clone
                    ),
                    # Error field tracks failure reason if operation failed
                    # Could be enhanced to capture specific error messages
                    error=None if ok else "clone_failed",
                )
            )

        # Display final summary (Rich UI only)
        # Uses color coding: green if all succeeded, yellow otherwise
        if not (args.json or args.quiet):
            console.print()
            final_panel = Panel(
                f"{get_icon('sparkles')} [bold]{success_count}/{total}[/] repositories "
                f"processed successfully {get_icon('sparkles')}",
                border_style="green" if success_count == total else "yellow",
                title="Processing Complete",
                title_align="center",
            )
            console.print(final_panel)
    else:
        # No repositories found after applying filters
        # Could be due to no repos in account or overly restrictive filters
        if not (args.json or args.quiet):
            console.print(
                f"[bold yellow]{get_icon('warning')} No repositories found to process[/]"
            )

    # Build final output payload for JSON/console emission
    # Success is True only if all repos succeeded AND at least one repo exists
    payload = OutputPayload(
        success=(success_count == total and total > 0),
        operation="pull",  # Operation type identifier
        repos_total=total,
        repos_success=success_count,
        repos_failed=total - success_count,
        results=repo_results,  # Detailed per-repo results
        errors=errors,  # Global errors (currently unused)
    )

    # Emit output via formatter (JSON or Rich depending on mode)
    formatter.emit(payload)


# Standard Python idiom for script execution
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully with user-friendly message
        console.print("\n[bold red]Operation canceled by user[/]")
    except Exception as e:
        # Catch-all exception handler with Rich traceback
        # install_traceback() ensures detailed error display
        console.print_exception()
