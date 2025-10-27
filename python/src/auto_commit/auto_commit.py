#!/usr/bin/env python3

import os
import subprocess
import argparse
import glob
import argcomplete
import time
import shutil
import random
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from rich.tree import Tree

# Remove the Live import as we'll use Progress and status instead
from rich.traceback import install as install_traceback
from rich.box import ROUNDED, DOUBLE
from rich.align import Align

# Install better traceback handling
install_traceback(show_locals=True)

# Initialize Rich console
console = Console()

# Use the built-in box styles from rich
from rich.box import ROUNDED, DOUBLE

# Icon mapping (will display as emoji in Rich)
ICONS = {
    "git": "",  # nf-dev-git
    "folder": "",  # nf-fa-folder
    "success": "",  # nf-fa-check_circle
    "error": "",  # nf-fa-times_circle
    "info": "",  # nf-fa-info_circle
    "warning": "",  # nf-fa-warning
    "exclude": "",  # nf-oct-file_submodule (close enough)
    "commit": "",  # nf-oct-git_commit
    "push": "",  # nf-oct-cloud_upload
    "pull": "",  # nf-oct-cloud_download
    "branch": "",  # nf-dev-git_branch
    "main_branch": "",  # nf-oct-git_branch
    "remote": "爵",  # nf-mdi-web
    "add": "",  # nf-fa-plus_circle
    "remove": "",  # nf-fa-minus_circle
    "separator": "─",
    "dot": "•",
    "file": "",  # nf-md-file
    "clock": "",  # nf-fa-clock
    "calendar": "",  # nf-fa-calendar
    "project": "",  # nf-fa-book
    "check": "",  # nf-fa-check
    "rocket": "",  # nf-fa-rocket
    "sparkles": "",  # nf-oct-sparkle
    "python": "",  # nf-seti-python
    "js": "",  # nf-seti-javascript
    "code": "",  # nf-fa-code
    "html": "",  # nf-dev-html5
    "css": "",  # nf-seti-css
    "database": "",  # nf-fa-database
    "config": "",  # nf-seti-config
    "image": "",  # nf-fa-picture_o
    "sound": "",  # nf-fa-volume_up
    "video": "",  # nf-fa-video_camera
    "archive": "",  # nf-fa-archive
    "text": "",  # nf-oct-file_text
}

# File type to icon mapping
FILE_ICONS = {
    # Programming languages
    "py": "python",
    "ipynb": "python",
    "js": "js",
    "jsx": "js",
    "ts": "js",
    "tsx": "js",
    "html": "html",
    "css": "css",
    "php": "code",
    "java": "code",
    "c": "code",
    "cpp": "code",
    "cs": "code",
    "go": "code",
    "rs": "code",
    "rb": "code",
    "swift": "code",
    "kt": "code",
    "sh": "code",
    # Data files
    "json": "database",
    "yml": "config",
    "yaml": "config",
    "xml": "database",
    "csv": "database",
    "sql": "database",
    # Config files
    "ini": "config",
    "cfg": "config",
    "conf": "config",
    "env": "config",
    "gitignore": "config",
    # Media files
    "jpg": "image",
    "jpeg": "image",
    "png": "image",
    "gif": "image",
    "svg": "image",
    "mp3": "sound",
    "wav": "sound",
    "mp4": "video",
    "mov": "video",
    # Archives
    "zip": "archive",
    "tar": "archive",
    "gz": "archive",
    "rar": "archive",
    # Documents
    "txt": "text",
    "md": "text",
    "pdf": "text",
    "doc": "text",
    "docx": "text",
}


def get_icon(name):
    """Get an icon based on name"""
    return ICONS.get(name, "📄")


def get_file_icon(filename):
    """Get an appropriate icon based on file extension"""
    if "." not in filename:
        return get_icon("file")

    extension = filename.split(".")[-1].lower()
    icon_type = FILE_ICONS.get(extension, "file")
    return get_icon(icon_type)


def print_header(text):
    """Print a fancy header with Rich"""
    console.print()
    panel = Panel(
        Align.center(f"[bold white]{text}[/]", vertical="middle"),
        border_style="cyan",
        box=DOUBLE,
        title="[bold blue]Git Project Manager[/]",
        title_align="center",
        subtitle=f"[bold cyan]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/]",
        subtitle_align="center",
        padding=(1, 4),
        width=shutil.get_terminal_size().columns - 2,
    )
    console.print(panel)
    console.print()


def generate_commit_message():
    """Generate an AI-like commit message."""
    prefixes = [
        "Update",
        "Enhance",
        "Fix",
        "Refactor",
        "Improve",
        "Optimize",
        "Add",
        "Remove",
        "Modify",
        "Restructure",
        "Clean up",
    ]
    areas = [
        "codebase",
        "functionality",
        "structure",
        "design",
        "performance",
        "documentation",
        "configuration",
        "dependencies",
        "features",
        "UI",
    ]
    details = [
        "for better maintainability",
        "to improve user experience",
        "for compatibility with latest standards",
        "to address technical debt",
        "for enhanced security",
        "to optimize resource usage",
        "based on feedback",
        "following best practices",
    ]

    return f"{random.choice(prefixes)} {random.choice(areas)} {random.choice(details)}"


def process_repository(entry_path, entry, args, task_id=None, progress=None):
    """Process a single git repository with visual enhancements using Rich."""
    # Set up the repository panel
    repo_panel = Panel(
        f"[bold cyan]{get_icon('project')} {entry}[/]",
        border_style="blue",
        title=f"[bold]Repository[/]",
        title_align="left",
        subtitle=f"[dim]{entry_path}[/]",
        subtitle_align="right",
    )
    console.print(repo_panel)

    # Start time
    start_time = time.time()

    if progress and task_id:
        progress.update(task_id, description=f"[cyan]Processing {entry}[/]")

    os.chdir(entry_path)

    try:
        # Get current branch information
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        current_branch = branch_result.stdout.strip()

        # Display branch info with appropriate styling
        branch_style = "magenta" if current_branch in ["main", "master"] else "yellow"
        branch_icon = (
            get_icon("main_branch")
            if current_branch in ["main", "master"]
            else get_icon("branch")
        )

        console.print(
            f"{branch_icon} On branch: [bold {branch_style}]{current_branch}[/]"
        )

        # Create status table
        status_table = Table(
            show_header=False, box=None, padding=(0, 1, 0, 1), collapse_padding=True
        )
        status_table.add_column("Icon", style="cyan")
        status_table.add_column("Status", style="white")
        status_table.add_column("Details", style="green")

        # Execute git operations
        if args.pull:
            with console.status(
                "[bold blue]Pulling latest changes...[/]", spinner="dots"
            ):
                pull_result = subprocess.run(
                    ["git", "pull"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True,
                )
            status_table.add_row(
                get_icon("pull"), "Pulled changes", pull_result.stdout.strip()
            )

        if args.handle_gitignore:
            # Ensure .gitignore includes .DS_Store
            gitignore_path = os.path.join(entry_path, ".gitignore")
            gitignore_updated = False

            if not os.path.exists(gitignore_path):
                with open(gitignore_path, "w") as f:
                    f.write(".DS_Store\n")
                gitignore_updated = True
            else:
                with open(gitignore_path, "r") as f:
                    lines = f.readlines()
                if ".DS_Store\n" not in lines and ".DS_Store" not in [
                    line.strip() for line in lines
                ]:
                    with open(gitignore_path, "a") as f:
                        f.write("\n.DS_Store\n")
                    gitignore_updated = True

            if gitignore_updated:
                subprocess.run(["git", "add", ".gitignore"], check=True)
                status_table.add_row(
                    get_icon("config"),
                    "Updated .gitignore",
                    "Added .DS_Store to ignore list",
                )

        if args.remove_ds_store:
            # Find and remove .DS_Store files
            ds_store_files = glob.glob("**/.DS_Store", recursive=True)

            if ds_store_files:
                with console.status(
                    f"[bold yellow]Removing {len(ds_store_files)} .DS_Store files...[/]",
                    spinner="dots",
                ):
                    for file in ds_store_files:
                        subprocess.run(["git", "rm", "--cached", file], check=False)
                        subprocess.run(["rm", file], check=False)

                status_table.add_row(
                    get_icon("remove"),
                    "Removed .DS_Store files",
                    f"{len(ds_store_files)} files removed",
                )

        # Display status table if it has rows
        if status_table.row_count > 0:
            console.print(status_table)

        # Use ai_commit or handle git operations manually
        if args.use_ai_commit:
            # Generate a commit message if set to auto-commit
            commit_message = (
                args.commit_message
                if args.commit_message != "auto-commit"
                else generate_commit_message()
            )

            console.print(
                f"\n[bold cyan]{get_icon('commit')} Using ai_commit command[/]"
            )
            console.print("[bold blue]Executing ai_commit...[/]")
            result = subprocess.run(
                ["ai_commit", commit_message],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            if result.returncode == 0:
                console.print(
                    f"[bold green]{get_icon('success')} ai_commit executed successfully[/]"
                )
                if result.stdout.strip():
                    console.print(
                        Panel(
                            result.stdout.strip(),
                            title="ai_commit output",
                            border_style="green",
                        )
                    )
            else:
                console.print(f"[bold red]{get_icon('error')} ai_commit failed[/]")
                if result.stderr.strip():
                    console.print(
                        Panel(result.stderr.strip(), title="Error", border_style="red")
                    )
        else:
            # Run manual git commands
            console.print("[bold blue]Staging changes...[/]")
            # Stage changes
            subprocess.run(["git", "add", "."], check=True)

            # Check if there are any changes to commit
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            if result.stdout.strip() == "":
                console.print(f"[dim]{get_icon('info')} No changes to commit[/]")
            else:
                # Get the changed files and create a tree view
                changes = result.stdout.strip().split("\n")

                # Create a tree of changes
                tree = Tree(f"[bold yellow]{len(changes)} files changed[/]")

                for change in changes:
                    if not change.strip():
                        continue

                    # Parse the status line
                    status_code = change[:2].strip()
                    file_path = change[3:].strip()

                    # Determine status text and style
                    if status_code == "M":
                        status_text = "Modified"
                        style = "blue"
                    elif status_code == "A":
                        status_text = "Added"
                        style = "green"
                    elif status_code == "D":
                        status_text = "Deleted"
                        style = "red"
                    elif status_code == "R":
                        status_text = "Renamed"
                        style = "magenta"
                    elif status_code == "??":
                        status_text = "Untracked"
                        style = "yellow"
                    else:
                        status_text = status_code
                        style = "white"

                    # Add to tree with appropriate icon
                    tree.add(
                        f"[{style}]{get_file_icon(file_path)} {file_path}[/] ([bold {style}]{status_text}[/])"
                    )

                console.print(tree)

                # Generate commit message if needed
                commit_message = (
                    args.commit_message
                    if args.commit_message != "auto-commit"
                    else generate_commit_message()
                )

                # Commit changes
                console.print(f"[bold blue]Committing changes: {commit_message}[/]")
                subprocess.run(
                    ["git", "commit", "-a", "-m", commit_message], check=True
                )

                # Get commit summary
                console.print(f"\n[bold green]{get_icon('commit')} Commit Summary[/]")

                show_result = subprocess.run(
                    ["git", "show", "--stat", "--oneline", "-1"],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )

                # Format commit info as a panel
                commit_panel = Panel(
                    show_result.stdout.strip(),
                    title="[bold green]Commit Details[/]",
                    border_style="green",
                    padding=(1, 2),
                )
                console.print(commit_panel)

                # Push changes
                console.print("[bold blue]Pushing to remote...[/]")
                push_result = subprocess.run(
                    ["git", "push"],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )

                # Display push results
                if push_result.stdout.strip():
                    console.print(
                        Panel(
                            push_result.stdout.strip(),
                            title=f"[bold cyan]{get_icon('push')} Push Results[/]",
                            border_style="cyan",
                            padding=(1, 2),
                        )
                    )
                else:
                    console.print(
                        f"[bold cyan]{get_icon('push')} Changes pushed to remote repository[/]"
                    )

        # Calculate and display processing time
        end_time = time.time()
        elapsed = end_time - start_time

        console.print(
            f"\n{get_icon('clock')} Processed in [bold cyan]{elapsed:.2f}[/] seconds"
        )

        # Success message
        console.print(
            f"[bold green]{get_icon('sparkles')} Successfully processed {entry} {get_icon('sparkles')}[/]"
        )

        if progress and task_id:
            progress.update(task_id, advance=1)

        return True

    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]{get_icon('error')} Error processing {entry}:[/]")
        console.print(Panel(str(e), title="Error Details", border_style="red"))

        if progress and task_id:
            progress.update(task_id, advance=1)

        return False
    finally:
        # Return to the original directory
        os.chdir(args.current_dir)
        console.print(
            f"[dim cyan]{get_icon('separator') * (shutil.get_terminal_size().columns // 2)}[/]"
        )


def main():
    """Enhanced main function with Rich UI components."""
    parser = argparse.ArgumentParser(
        description="A beautiful Git repository manager for multiple projects.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--handle-gitignore",
        action="store_true",
        help="Ensure .gitignore includes .DS_Store and update it if necessary.",
    )
    parser.add_argument(
        "--remove-ds-store",
        action="store_true",
        help="Remove .DS_Store files from the repository.",
    )
    parser.add_argument(
        "--commit-message",
        type=str,
        default="auto-commit",
        help="Commit message to use (or 'auto-commit' for AI-generated messages).",
    )
    parser.add_argument(
        "--exclude",
        type=str,
        nargs="+",
        default=[],
        help="List of directories to exclude.",
    )
    parser.add_argument(
        "--only",
        type=str,
        nargs="+",
        default=[],
        help="List of directories to include (if empty, include all).",
    )
    parser.add_argument(
        "--pull", action="store_true", help="Pull changes from the remote repository."
    )
    parser.add_argument(
        "--no-auto-commit",
        action="store_false",
        dest="use_ai_commit",
        default=True,
        help="Don't use the ai_commit command (use manual git commands instead).",
    )
    parser.add_argument(
        "--dir",
        type=str,
        default="~/Neoware",
        help="Base directory containing git repositories.",
    )

    args = parser.parse_args()
    args.current_dir = os.path.expanduser(args.dir)

    # Print a fancy header
    print_header("Git Repository Manager")

    # Show configuration as a table
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

    config_table.add_row("Base Directory", args.current_dir)
    config_table.add_row("Pull Changes", "Yes" if args.pull else "No")
    config_table.add_row("Handle .gitignore", "Yes" if args.handle_gitignore else "No")
    config_table.add_row("Remove .DS_Store", "Yes" if args.remove_ds_store else "No")
    config_table.add_row("Using ai_commit", "Yes" if args.use_ai_commit else "No")
    config_table.add_row(
        "Commit Message",
        "AI Generated" if args.commit_message == "auto-commit" else args.commit_message,
    )

    if args.exclude:
        config_table.add_row("Excluded Directories", ", ".join(args.exclude))
    if args.only:
        config_table.add_row("Including Only", ", ".join(args.only))

    console.print(config_table)

    # Scan for repositories
    # Scan for repositories without using status
    console.print("[bold blue]Scanning for Git repositories...[/]")
    entries = os.listdir(args.current_dir)
    git_repos = []
    excluded_repos = []

    for entry in entries:
        if entry in args.exclude:
            excluded_repos.append(entry)
            continue
        if args.only and entry not in args.only:
            continue

        entry_path = os.path.join(args.current_dir, entry)
        if os.path.isdir(entry_path) and os.path.isdir(
            os.path.join(entry_path, ".git")
        ):
            git_repos.append(entry)

    # Display summary
    summary_panel = Panel(
        f"{get_icon('folder')} Found [bold green]{len(git_repos)}[/] Git repositories to process\n"
        + (
            f"{get_icon('exclude')} Excluding [yellow]{len(excluded_repos)}[/] repositories"
            if excluded_repos
            else ""
        ),
        title="Repository Summary",
        border_style="blue",
    )
    console.print(summary_panel)
    argcomplete.autocomplete(parser)

    # Process repositories with progress bar
    if git_repos:
        # Process repositories without nested Progress
        success_count = 0

        # Create a simple progress display at the top
        console.print(f"[bold blue]Processing {len(git_repos)} repositories...[/]")

        for idx, entry in enumerate(git_repos, 1):
            entry_path = os.path.join(args.current_dir, entry)
            console.print(f"\n[bold cyan]Repository {idx}/{len(git_repos)}:[/]")
            if process_repository(entry_path, entry, args, None, None):
                success_count += 1

        # Final summary
        console.print()
        final_panel = Panel(
            f"{get_icon('sparkles')} [bold]{'All' if success_count == len(git_repos) else success_count}/{len(git_repos)}[/] repositories processed successfully {get_icon('sparkles')}",
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
