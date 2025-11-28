#!/usr/bin/env python3
"""
Initialize Iskra configuration and scan for repositories
"""

import os
import subprocess
import argparse
from pathlib import Path
from typing import List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.prompt import Confirm, Prompt

from auto_commit.config import ConfigManager, RepoInfo, GlobalConfig
from auto_commit.core.repo_scanner import find_git_repos
from auto_commit.core.constants import ICONS
from auto_commit.ui.formatting import get_icon

console = Console()


def get_git_info(repo_path: str) -> dict:
    """Extract git information from a repository"""
    original_dir = os.getcwd()
    os.chdir(repo_path)

    try:
        # Get remote URL
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"], capture_output=True, text=True
        )
        remote_url = result.stdout.strip() if result.returncode == 0 else None

        # Get default branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True
        )
        default_branch = result.stdout.strip() if result.returncode == 0 else None

        # Get last commit hash
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
        os.chdir(original_dir)


def scan_repositories(base_dir: str, config: GlobalConfig) -> List[str]:
    """Scan for git repositories in base directory"""
    console.print(
        f"\n[bold blue]{get_icon('folder')} Scanning for repositories in {base_dir}...[/]"
    )

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
    """Display tracked repositories in a nice table"""
    table = Table(
        title=f"{get_icon('project')} Tracked Repositories",
        show_header=True,
        header_style="bold cyan",
    )

    table.add_column("Name", style="cyan")
    table.add_column("Path", style="white")
    table.add_column("Branch", style="yellow")
    table.add_column("Remote", style="blue")
    table.add_column("Status", style="green")

    for repo in repos:
        status = "✓ Active" if repo.active else "✗ Inactive"
        status_style = "green" if repo.active else "red"

        # Truncate remote URL for display
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


def init_command(args):
    """Initialize auto-commit configuration"""
    console.print(
        Panel(
            "[bold white]Iskra Initialization[/]",
            border_style="cyan",
            title="[bold blue]Setup[/]",
            subtitle=f"[dim]Version 1.0.0[/]",
        )
    )

    # Get or create config manager
    config_manager = ConfigManager()

    # Set base directory
    if args.base_dir:
        config_manager.global_config.base_dir = args.base_dir

    base_dir = Path(config_manager.global_config.base_dir).expanduser()

    # Confirm base directory
    if not args.yes:
        console.print(f"\n[bold]Base directory:[/] {base_dir}")
        if not Confirm.ask("Is this correct?", default=True):
            new_base = Prompt.ask("Enter base directory path")
            base_dir = Path(new_base).expanduser()
            config_manager.global_config.base_dir = str(base_dir)

    # Ensure base directory exists
    if not base_dir.exists():
        console.print(
            f"[yellow]{get_icon('warning')} Base directory does not exist: {base_dir}[/]"
        )
        if args.yes or Confirm.ask("Create it?", default=True):
            base_dir.mkdir(parents=True, exist_ok=True)
            console.print(f"[green]{get_icon('success')} Created directory[/]")
        else:
            console.print("[red]Cancelled[/]")
            return

    # Configure settings interactively if not using --yes
    if not args.yes:
        console.print("\n[bold cyan]Configuration Options[/]")

        # Max depth
        if Confirm.ask(
            f"Change max scan depth? (current: {config_manager.global_config.max_depth})",
            default=False,
        ):
            depth = Prompt.ask(
                "Max depth", default=str(config_manager.global_config.max_depth)
            )
            config_manager.global_config.max_depth = int(depth)

        # AI commit
        config_manager.global_config.use_ai_commit = Confirm.ask(
            "Use AI-generated commit messages?",
            default=config_manager.global_config.use_ai_commit,
        )

        # Auto push
        config_manager.global_config.auto_push = Confirm.ask(
            "Automatically push after commit?",
            default=config_manager.global_config.auto_push,
        )

        # Require confirmation
        config_manager.global_config.require_confirmation = Confirm.ask(
            "Require confirmation before operations?",
            default=config_manager.global_config.require_confirmation,
        )

    # Save global config
    config_manager.save_global_config(config_manager.global_config)

    # Scan for repositories
    repo_paths = scan_repositories(str(base_dir), config_manager.global_config)

    if not repo_paths:
        console.print(f"[yellow]{get_icon('warning')} No repositories found[/]")
        return

    # Display found repositories
    console.print(f"\n[bold]Found {len(repo_paths)} repositories:[/]")
    for i, path in enumerate(repo_paths[:5], 1):
        rel_path = os.path.relpath(path, base_dir)
        console.print(f"  {i}. {rel_path}")

    if len(repo_paths) > 5:
        console.print(f"  ... and {len(repo_paths) - 5} more")

    # Confirm tracking
    if not args.yes and not Confirm.ask(
        f"\nTrack these {len(repo_paths)} repositories?", default=True
    ):
        console.print("[yellow]Cancelled[/]")
        return

    # Track repositories with progress
    console.print()
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("Tracking repositories...", total=len(repo_paths))

        tracked_count = 0
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

            progress.update(task, advance=1)

    # Success message
    console.print(
        f"\n[bold green]{get_icon('success')} Successfully tracked {tracked_count} repositories![/]\n"
    )

    # Display tracked repos
    if args.show_repos or (
        not args.yes and Confirm.ask("Show tracked repositories?", default=True)
    ):
        display_repo_table(config_manager.get_all_repos())

    # Show config location
    console.print(f"\n[dim]Configuration saved to: {config_manager.config_dir}[/]")
    console.print(f"[dim]  • Config: {config_manager.config_file}[/]")
    console.print(f"[dim]  • Repos:  {config_manager.repos_file}[/]")
    console.print(f"[dim]  • Logs:   {config_manager.logs_dir}[/]")


def list_command(args):
    """List all tracked repositories"""
    config_manager = ConfigManager()
    repos = config_manager.get_all_repos(active_only=not args.all)

    if not repos:
        console.print(f"[yellow]{get_icon('warning')} No tracked repositories found[/]")
        console.print(f"\n[dim]Run 'iskra init' to scan and track repositories[/]")
        return

    display_repo_table(repos)


def add_command(args):
    """Add a repository to tracking"""
    config_manager = ConfigManager()
    repo_path = Path(args.path).expanduser().resolve()

    # Check if it's a git repo
    if not (repo_path / ".git").exists() and not (repo_path / ".git").is_file():
        console.print(f"[red]{get_icon('error')} Not a git repository: {repo_path}[/]")
        return

    # Get git info
    git_info = get_git_info(str(repo_path))

    repo_info = RepoInfo(
        path=str(repo_path),
        name=repo_path.name,
        remote_url=git_info.get("remote_url"),
        default_branch=git_info.get("default_branch"),
        last_commit=git_info.get("last_commit"),
    )

    if config_manager.add_repo(repo_info):
        console.print(
            f"[green]{get_icon('success')} Added repository: {repo_path.name}[/]"
        )
    else:
        console.print(f"[yellow]{get_icon('warning')} Repository already tracked[/]")


def remove_command(args):
    """Remove a repository from tracking"""
    config_manager = ConfigManager()
    repo_path = Path(args.path).expanduser().resolve()

    if config_manager.remove_repo(str(repo_path)):
        console.print(
            f"[green]{get_icon('success')} Removed repository: {repo_path}[/]"
        )
    else:
        console.print(f"[yellow]{get_icon('warning')} Repository not tracked[/]")


def main():
    """Main entry point for init commands"""
    parser = argparse.ArgumentParser(
        description="Initialize and manage Iskra configuration",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Init command
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

    # List command
    list_parser = subparsers.add_parser("list", help="List tracked repositories")
    list_parser.add_argument(
        "--all", action="store_true", help="Include inactive repos"
    )

    # Add command
    add_parser = subparsers.add_parser("add", help="Add a repository to tracking")
    add_parser.add_argument("path", help="Path to git repository")

    # Remove command
    remove_parser = subparsers.add_parser(
        "remove", help="Remove a repository from tracking"
    )
    remove_parser.add_argument("path", help="Path to git repository")

    args = parser.parse_args()

    if args.command == "init":
        init_command(args)
    elif args.command == "list":
        list_command(args)
    elif args.command == "add":
        add_command(args)
    elif args.command == "remove":
        remove_command(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold red]Operation cancelled by user[/]")
    except Exception:
        console.print_exception()
