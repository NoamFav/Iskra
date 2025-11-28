#!/usr/bin/env python3
"""Main entry point for auto_commit."""

import os
import argparse
import argcomplete
from rich.console import Console
from rich.panel import Panel
from rich.traceback import install as install_traceback

from .ui.formatting import print_header, get_icon
from .ui.tables import create_config_table
from .ui.display import process_repository
from .core.repo_scanner import find_git_repos

# Install better traceback handling
install_traceback(show_locals=True)

# Initialize Rich console
console = Console()


def main():
    """Enhanced main function with recursive repo detection and Rich UI."""
    parser = argparse.ArgumentParser(
        description="A beautiful Git repository manager for multiple projects.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("--handle-gitignore", action="store_true")
    parser.add_argument("--remove-ds-store", action="store_true")
    parser.add_argument("--commit-message", type=str, default="auto-commit")
    parser.add_argument("--exclude", type=str, nargs="+", default=[])
    parser.add_argument("--only", type=str, nargs="+", default=[])
    parser.add_argument("--pull", action="store_true")
    parser.add_argument(
        "--no-auto-commit",
        action="store_false",
        dest="use_ai_commit",
        default=True,
    )
    parser.add_argument("--dir", type=str, default="~/Neoware")

    args = parser.parse_args()
    args.current_dir = os.path.expanduser(args.dir)
    orig_cwd = os.getcwd()

    print_header("Git Repository Manager")

    config_table = create_config_table(args, for_pull_repos=False)
    console.print(config_table)

    # Scan for Git repositories
    console.print("[bold blue]Scanning for Git repositories...[/]")

    git_repo_paths = find_git_repos(
        base_dir=args.current_dir,
        only=args.only,
        exclude=args.exclude,
        max_depth=3,
        followlinks=True,
    )

    git_repos = [
        (path, os.path.relpath(path, args.current_dir)) for path in git_repo_paths
    ]

    summary_panel = Panel(
        f"{get_icon('folder')} Found [bold green]{len(git_repos)}[/] Git repositories to process",
        title="Repository Summary",
        border_style="blue",
    )
    console.print(summary_panel)

    argcomplete.autocomplete(parser)

    if git_repos:
        console.print(f"[bold blue]Processing {len(git_repos)} repositories...[/]\n")
        success_count = 0

        for idx, (repo_path, display_name) in enumerate(git_repos, 1):
            console.print(f"\n[bold cyan]Repository {idx}/{len(git_repos)}:[/]")
            ok = process_repository(
                entry_path=repo_path,
                entry=display_name,
                args=args,
                task_id=None,
                progress=None,
                orig_cwd=orig_cwd,
            )
            if ok:
                success_count += 1

        console.print()
        final_panel = Panel(
            f"{get_icon('sparkles')} [bold]{success_count}/{len(git_repos)}[/] repositories processed successfully {get_icon('sparkles')}",
            border_style="green" if success_count == len(git_repos) else "yellow",
            title="Processing Complete",
            title_align="center",
        )
        console.print(final_panel)

    else:
        console.print(
            f"\n[bold yellow]{get_icon('warning')} No Git repositories found to process[/]"
        )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold red]Operation canceled by user[/]")
    except Exception as e:
        console.print_exception()
