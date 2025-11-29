#!/usr/bin/env python3
"""Main entry point for pull_repos (GitHub cloning)."""

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
    RepoChanges,
    RepoRemote,
    RepoCommit,
)

# Install better traceback handling
install_traceback(show_locals=True)

# Initialize Rich console
console = Console()


def main():
    """Main function with enhanced CLI and visualization"""
    parser = argparse.ArgumentParser(
        description="Clone GitHub repositories with rich visual interface.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--base-dir",
        type=str,
        default=os.path.expanduser("~/Neoware"),
        help="Base directory where repositories will be cloned.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Maximum number of repositories to fetch.",
    )

    parser.add_argument(
        "--filter-forks", action="store_true", help="Filter out forked repositories."
    )

    parser.add_argument(
        "--only-stars",
        type=int,
        default=0,
        help="Only clone repositories with at least this many stars.",
    )

    parser.add_argument(
        "--exclude",
        type=str,
        nargs="+",
        default=[],
        help="List of repository name patterns to exclude (supports glob patterns).",
    )

    parser.add_argument(
        "--json", action="store_true", help="Output the result in standard json format"
    )

    args = parser.parse_args()
    argcomplete.autocomplete(parser)

    base_dir = args.base_dir

    # Print the header
    print_header("GitHub Repository Clone Manager", title="GitHub Clone Manager")

    # Show configuration table
    config_table = create_config_table(args, for_pull_repos=True)
    console.print(config_table)

    # Ensure the base directory exists
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
        console.print(
            f"[cyan]{get_icon('folder')} Created base directory at {base_dir}"
        )

    # Get repositories from GitHub (with filters applied)
    repositories = get_github_repos(
        limit=args.limit,
        filter_forks=args.filter_forks,
        only_stars=args.only_stars,
        exclude=args.exclude,
    )

    # Show summary
    summary_panel = Panel(
        f"{get_icon('github')} Found [bold green]{len(repositories)}[/] repositories to process\n"
        + f"{get_icon('folder')} Target directory: [bold blue]{base_dir}[/]",
        title="Repository Summary",
        border_style="blue",
    )
    console.print(summary_panel)

    # Process repositories
    if repositories:
        console.print(f"[bold blue]Processing {len(repositories)} repositories...[/]")

        success_count = 0
        for idx, repo in enumerate(repositories, 1):
            if process_repository(repo, base_dir, len(repositories), idx):
                success_count += 1

        # Final summary
        console.print()
        final_panel = Panel(
            f"{get_icon('sparkles')} [bold]{success_count}/{len(repositories)}[/] repositories processed successfully {get_icon('sparkles')}",
            border_style="green" if success_count == len(repositories) else "yellow",
            title="Processing Complete",
            title_align="center",
        )
        console.print(final_panel)
    else:
        console.print(
            f"[bold yellow]{get_icon('warning')} No repositories found to process[/]"
        )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold red]Operation canceled by user[/]")
    except Exception as e:
        console.print_exception()
