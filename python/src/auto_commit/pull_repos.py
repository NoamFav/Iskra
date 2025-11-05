#!/usr/bin/env python3

import os
import subprocess
import argcomplete
import argparse
import json
import time
from datetime import datetime
import shutil
import fnmatch
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from rich.traceback import install as install_traceback
from rich.box import ROUNDED, DOUBLE
from rich.align import Align

# Install better traceback handling
install_traceback(show_locals=True)

# Initialize Rich console
console = Console()

HEAVY_DIRS = {
    "node_modules",
    "dist",
    "build",
    "target",
    "__pycache__",
    ".tox",
    ".mypy_cache",
    ".idea",
    ".vscode",
    ".venv",
    "venv",
}

# Icon mapping (using emoji for universal compatibility)
ICONS = {
    "git": "",  # nf-dev-git
    "folder": "",  # nf-fa-folder
    "success": "",  # nf-fa-check_circle
    "error": "",  # nf-fa-times_circle
    "info": "",  # nf-fa-info_circle
    "warning": "",  # nf-fa-warning
    "exclude": "",  # nf-oct-file_submodule (used as "ignore/exclude")
    "clone": "",  # nf-oct-cloud_download (close to clone)
    "separator": "─",  # plain separator, fits aesthetic
    "dot": "•",  # minimalist bullet
    "file": "",  # nf-md-file
    "clock": "",  # nf-fa-clock_o
    "calendar": "",  # nf-fa-calendar
    "project": "",  # nf-fa-book (good for code/project repo)
    "check": "",  # nf-fa-check
    "rocket": "",  # nf-fa-rocket
    "sparkles": "",  # nf-oct-sparkle (stylish)
    "star": "",  # nf-fa-star
    "github": "",  # nf-fa-github
    "fork": "",  # nf-fa-code_fork
    "user": "",  # nf-fa-user
    "globe": "",  # nf-fa-globe
    "code": "",  # nf-fa-code
    "lock": "",  # nf-fa-lock
    "unlock": "",  # nf-fa-unlock
    "public": "",  # same as unlock
    "private": "",  # same as lock
}


def get_icon(name):
    """Get an icon based on name"""
    return ICONS.get(name, "📄")


def print_header(text):
    """Print a fancy header with Rich"""
    console.print()
    panel = Panel(
        Align.center(f"[bold white]{text}[/]", vertical="middle"),
        border_style="cyan",
        box=DOUBLE,
        title="[bold blue]GitHub Clone Manager[/]",
        title_align="center",
        subtitle=f"[bold cyan]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/]",
        subtitle_align="center",
        padding=(1, 4),
        width=shutil.get_terminal_size().columns - 2,
    )
    console.print(panel)
    console.print()


def _match_any(repo_name: str, patterns) -> bool:
    """Match repository name against glob patterns."""
    if not patterns:
        return False
    for pat in patterns:
        if fnmatch.fnmatch(repo_name, pat):
            return True
    return False


def get_github_repos(limit=1000, filter_forks=False, only_stars=0, exclude=None):
    """Get list of repositories from GitHub CLI with detailed information"""
    try:
        # Define fields to extract
        fields = [
            "nameWithOwner",
            "name",
            "description",
            "isPrivate",
            "isFork",
            "stargazerCount",
            "url",
        ]
        fields_arg = ",".join(fields)

        console.print(
            f"[bold blue]{get_icon('github')} Fetching repositories from GitHub...[/]"
        )

        # Run the `gh repo list` command with JSON output
        command = ["gh", "repo", "list", "--limit", str(limit), "--json", fields_arg]

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )

        # Parse JSON output
        repos = json.loads(result.stdout.strip())

        # Apply filters
        if filter_forks:
            repos = [repo for repo in repos if not repo.get("isFork", False)]

        if only_stars > 0:
            repos = [
                repo
                for repo in repos
                if repo.get("stargazerCount", 0) >= only_stars
            ]

        if exclude:
            repos = [
                repo for repo in repos
                if not _match_any(repo["nameWithOwner"], exclude)
            ]

        console.print(
            f"[bold green]{get_icon('success')} Found {len(repos)} repositories."
        )
        return repos
    except subprocess.CalledProcessError as e:
        console.print(
            f"[bold red]{get_icon('error')} Error fetching repositories from GitHub:"
        )
        console.print(Panel(str(e), title="Error Details", border_style="red"))
        return []
    except json.JSONDecodeError as e:
        console.print(f"[bold red]{get_icon('error')} Error parsing GitHub response:")
        console.print(Panel(str(e), title="JSON Error", border_style="red"))
        return []


def process_repository(repo_info, base_dir, total, current):
    """Clone a repository with visual enhancements"""
    # Extract repository information
    repo_name = repo_info["nameWithOwner"]
    repo_dir = os.path.join(base_dir, repo_name.split("/")[-1])

    # Create a panel for repository info
    is_private = repo_info.get("isPrivate", False)
    is_fork = repo_info.get("isFork", False)
    stars = repo_info.get("stargazerCount", 0)
    description = repo_info.get("description", "No description available")
    url = repo_info.get("url", "")

    # Set icon based on repository type
    repo_icon = get_icon("lock") if is_private else get_icon("unlock")
    fork_text = f" ({get_icon('fork')} Fork)" if is_fork else ""
    star_text = f" {get_icon('star')} {stars}" if stars > 0 else ""

    # Create a repository panel with rich formatting
    repo_panel = Panel(
        f"[dim cyan]{description}[/]\n[blue]{url}[/]",
        title=f"[bold]{repo_icon} {repo_name}{fork_text}{star_text}[/]",
        title_align="left",
        border_style="blue" if not is_private else "magenta",
        subtitle=f"[dim]Repository {current} of {total}[/]",
        subtitle_align="right",
        padding=(1, 2),
    )
    console.print(repo_panel)

    start_time = time.time()

    if os.path.isdir(repo_dir):
        console.print(
            f"[yellow]{get_icon('warning')} Repository already exists, skipping..."
        )
    else:
        try:
            # Clone the repository
            with console.status(
                f"[bold blue]Cloning {repo_name}...[/]", spinner="dots"
            ):
                subprocess.run(
                    ["gh", "repo", "clone", repo_name],
                    cwd=base_dir,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

            # Calculate cloning time
            end_time = time.time()
            elapsed = end_time - start_time

            console.print(
                f"[bold green]{get_icon('success')} Successfully cloned in {elapsed:.2f} seconds."
            )

            # Show repository structure if successful
            if os.path.isdir(repo_dir):
                file_count = sum(len(files) for _, _, files in os.walk(repo_dir))
                dir_count = sum(len(dirs) for _, dirs, _ in os.walk(repo_dir))

                # Display repository stats
                stats_table = Table(show_header=False, box=None, pad_edge=False)
                stats_table.add_column("", style="cyan")
                stats_table.add_column("", style="white")

                stats_table.add_row(
                    f"{get_icon('folder')} Directories:", f"{dir_count}"
                )
                stats_table.add_row(f"{get_icon('file')} Files:", f"{file_count}")
                stats_table.add_row(
                    f"{get_icon('code')} Repository size:",
                    f"{get_repo_size_str(repo_dir)}",
                )

                console.print(stats_table)

        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]{get_icon('error')} Error cloning repository:")
            console.print(Panel(e.stderr, title="Error Details", border_style="red"))

    console.print(
        f"[dim cyan]{get_icon('separator') * (shutil.get_terminal_size().columns // 2)}[/]"
    )
    console.print()

    return True


def get_repo_size_str(repo_dir):
    """Get the size of a repository in human-readable format"""
    total_size = 0
    for dirpath, _, filenames in os.walk(repo_dir):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)

    # Convert bytes to appropriate unit
    units = ["B", "KB", "MB", "GB", "TB"]
    size = total_size
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    return f"{size:.2f} {units[unit_index]}"


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

    args = parser.parse_args()
    argcomplete.autocomplete(parser)
    
    base_dir = args.base_dir

    # Print the header
    print_header("GitHub Repository Clone Manager")

    # Show configuration table
    config_table = Table(
        title="Configuration",
        title_style="bold cyan",
        box=ROUNDED,
        border_style="cyan",
        show_header=True,
        header_style="bold cyan",
    )

    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="green")

    config_table.add_row("Base Directory", base_dir)
    config_table.add_row("Repo Limit", str(args.limit))
    config_table.add_row("Filter Forks", "Yes" if args.filter_forks else "No")
    config_table.add_row("Minimum Stars", str(args.only_stars))

    if args.exclude:
        config_table.add_row("Excluded Patterns", ", ".join(args.exclude))

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