"""Display utilities for repository processing."""

import os
import time
import shutil
import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from .formatting import get_icon, get_file_icon
from ..core.git_operations import (
    get_current_branch,
    git_pull,
    handle_gitignore,
    remove_ds_store_files,
    git_add_all,
    git_status_porcelain,
    git_commit,
    git_push,
    git_show_last_commit,
    generate_commit_message,
)

console = Console()


def process_repository(
    entry_path, entry, args, task_id=None, progress=None, orig_cwd=None
):
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
        current_branch = get_current_branch()

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
                pull_result = git_pull()
            status_table.add_row(
                get_icon("pull"), "Pulled changes", pull_result.stdout.strip()
            )

        if args.handle_gitignore:
            gitignore_updated = handle_gitignore(entry_path)
            if gitignore_updated:
                status_table.add_row(
                    get_icon("config"),
                    "Updated .gitignore",
                    "Added .DS_Store to ignore list",
                )

        if args.remove_ds_store:
            ds_store_count = remove_ds_store_files()
            if ds_store_count > 0:
                status_table.add_row(
                    get_icon("remove"),
                    "Removed .DS_Store files",
                    f"{ds_store_count} files removed",
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
            git_add_all()

            # Check if there are any changes to commit
            status_output = git_status_porcelain()

            if status_output == "":
                console.print(f"[dim]{get_icon('info')} No changes to commit[/]")
            else:
                # Get the changed files and create a tree view
                changes = status_output.split("\n")

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
                git_commit(commit_message)

                # Get commit summary
                console.print(f"\n[bold green]{get_icon('commit')} Commit Summary[/]")

                show_result = git_show_last_commit()

                # Format commit info as a panel
                commit_panel = Panel(
                    show_result.stdout.strip(),
                    title="[bold green]Commit Details[/]",
                    border_style="green",
                    padding=(1, 2),
                )
                console.print(commit_panel)

                # Push changes
                if hasattr(args, "auto_push") and args.auto_push:
                    console.print("[bold blue]Pushing to remote...[/]")
                    push_result = git_push()

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
                elif hasattr(args, "auto_push"):
                    console.print(
                        f"[dim]{get_icon('info')} Skipping push (auto_push disabled)[/]"
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
        if orig_cwd:
            os.chdir(orig_cwd)
        console.print(
            f"[dim cyan]{get_icon('separator') * (shutil.get_terminal_size().columns // 2)}[/]"
        )
