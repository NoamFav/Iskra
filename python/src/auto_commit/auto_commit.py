#!/usr/bin/env python3
"""
Enhanced auto_commit.py with configuration system integration
"""

import os
import subprocess
import argparse
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from auto_commit.config import ConfigManager, get_config
from auto_commit.ui.display import process_repository
from auto_commit.ui.formatting import print_header, get_icon
from auto_commit.core.repo_scanner import find_git_repos
from auto_commit.core.constants import ICONS

console = Console()


def main():
    """Enhanced main function with configuration system"""
    parser = argparse.ArgumentParser(
        description="Auto-commit with configuration management",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Configuration
    parser.add_argument("--config", type=str, help="Path to config file")
    parser.add_argument("--profile", type=str, help="Use named profile")

    # Override config options
    parser.add_argument("--dir", type=str, help="Base directory (overrides config)")
    parser.add_argument(
        "--use-tracked",
        action="store_true",
        help="Use tracked repos instead of scanning",
    )

    # Git operations
    parser.add_argument("--pull", action="store_true", help="Pull before commit")
    parser.add_argument(
        "--no-push", action="store_true", help="Don't push after commit"
    )

    # Commit options
    parser.add_argument("--commit-message", type=str, default="auto-commit")
    parser.add_argument(
        "--no-ai-commit", action="store_true", help="Don't use AI for commit messages"
    )

    # Filtering
    parser.add_argument("--exclude", type=str, nargs="+", default=[])
    parser.add_argument("--only", type=str, nargs="+", default=[])

    # Safety and UI
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

    # Special handling
    parser.add_argument("--handle-gitignore", action="store_true")
    parser.add_argument("--remove-ds-store", action="store_true")

    args = parser.parse_args()

    # Load configuration
    if args.config:
        config_manager = ConfigManager(args.config)
    else:
        config_manager = get_config()

    # Apply command-line overrides to config
    config = config_manager.global_config

    if args.dir:
        config.base_dir = args.dir
    if args.pull:
        config.auto_pull = True
    if args.no_push:
        config.auto_push = False
    if args.no_ai_commit:
        config.use_ai_commit = False
    if args.dry_run:
        config.dry_run = True
    if args.yes:
        config.require_confirmation = False
    if args.show_diff:
        config.show_diff = True
    if args.exclude:
        config.exclude_patterns.extend(args.exclude)
    if args.only:
        config.only_patterns.extend(args.only)

    # Set working directory
    base_dir = os.path.expanduser(config.base_dir)
    orig_cwd = os.getcwd()

    # Print header
    print_header("Git Repository Manager")

    # Show dry-run warning
    if config.dry_run:
        console.print(
            Panel(
                "[bold yellow]DRY RUN MODE[/]\n"
                "No changes will be made to repositories",
                border_style="yellow",
                title="⚠️  Warning",
            )
        )

    # Show status-only warning
    if args.status_only:
        console.print(
            Panel(
                "[bold cyan]STATUS ONLY MODE[/]\n"
                "Will only display repository status",
                border_style="cyan",
                title="ℹ️  Info",
            )
        )

    # Get repositories
    if args.use_tracked:
        # Use tracked repositories from config
        tracked_repos = config_manager.get_all_repos(active_only=True)

        if not tracked_repos:
            console.print(
                f"[yellow]{get_icon('warning')} No tracked repositories found[/]"
            )
            console.print(
                f"\n[dim]Run 'auto-commit init' to scan and track repositories[/]"
            )
            return

        # Apply filters to tracked repos
        git_repos = []
        for repo_info in tracked_repos:
            repo_path = repo_info.path
            repo_name = repo_info.name

            # Apply exclude/only filters
            if config.only_patterns:
                from fnmatch import fnmatch

                if not any(fnmatch(repo_name, pat) for pat in config.only_patterns):
                    continue

            if config.exclude_patterns:
                from fnmatch import fnmatch

                if any(fnmatch(repo_name, pat) for pat in config.exclude_patterns):
                    continue

            git_repos.append((repo_path, repo_name))

        console.print(f"[bold blue]Using {len(git_repos)} tracked repositories[/]")
    else:
        # Scan for repositories
        console.print("[bold blue]Scanning for Git repositories...[/]")

        git_repo_paths = find_git_repos(
            base_dir=base_dir,
            only=config.only_patterns,
            exclude=config.exclude_patterns,
            max_depth=config.max_depth,
            followlinks=config.follow_symlinks,
        )

        git_repos = [(path, os.path.relpath(path, base_dir)) for path in git_repo_paths]

    if not git_repos:
        console.print(
            f"\n[yellow]{get_icon('warning')} No repositories found to process[/]"
        )
        return

    # Show summary
    summary_panel = Panel(
        f"{get_icon('folder')} Found [bold green]{len(git_repos)}[/] repositories to process",
        title="Repository Summary",
        border_style="blue",
    )
    console.print(summary_panel)

    # Require confirmation if enabled
    if config.require_confirmation and not args.yes:
        if not Confirm.ask(f"Process {len(git_repos)} repositories?", default=True):
            console.print("[yellow]Cancelled[/]")
            return

    # Process repositories
    console.print(f"[bold blue]Processing {len(git_repos)} repositories...[/]\n")
    success_count = 0

    for idx, (repo_path, display_name) in enumerate(git_repos, 1):
        console.print(f"\n[bold cyan]Repository {idx}/{len(git_repos)}:[/]")

        # Get repo-specific config (merges with global)
        repo_config = config_manager.merge_config(repo_path)

        # Check if we should skip this repo
        if config.skip_repos_without_changes:
            # Check if repo has changes
            os.chdir(repo_path)
            result = subprocess.run(
                ["git", "status", "--porcelain"], capture_output=True, text=True
            )
            if not result.stdout.strip():
                console.print(f"[dim]{get_icon('info')} No changes, skipping[/]")
                os.chdir(orig_cwd)
                continue

        # Create args object for process_repository
        class RepoArgs:
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

        # Process the repository
        ok = process_repository(
            entry_path=repo_path,
            entry=display_name,
            args=repo_args,
            task_id=None,
            progress=None,
            orig_cwd=orig_cwd,
        )

        if ok:
            success_count += 1

            # Update tracked repo info if using tracked repos
            if args.use_tracked:
                result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    capture_output=True,
                    text=True,
                    cwd=repo_path,
                )
                if result.returncode == 0:
                    config_manager.update_repo(
                        repo_path, last_commit=result.stdout.strip()
                    )

    # Final summary
    console.print()
    final_panel = Panel(
        f"{get_icon('sparkles')} [bold]{success_count}/{len(git_repos)}[/] repositories processed successfully {get_icon('sparkles')}",
        border_style="green" if success_count == len(git_repos) else "yellow",
        title="Processing Complete",
        title_align="center",
    )
    console.print(final_panel)

    # Log to file
    log_file = config_manager.get_log_file()
    with open(log_file, "a") as f:
        f.write(f"\n{'='*80}\n")
        f.write(f"Run at: {datetime.now().isoformat()}\n")
        f.write(f"Processed: {success_count}/{len(git_repos)} repositories\n")
        f.write(f"Base dir: {base_dir}\n")
        if config.dry_run:
            f.write("Mode: DRY RUN\n")
        f.write(f"{'='*80}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold red]Operation canceled by user[/]")
    except Exception:
        console.print_exception()
