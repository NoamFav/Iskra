"""
Display utilities for repository processing.

Provides the core repository processing workflow with rich visual feedback,
status tracking, and error handling. This is the heart of Iskra's git
automation, orchestrating git operations while providing detailed progress
information through Rich UI components.

Workflow:
    1. Display repository header with path
    2. Show current branch information
    3. Execute pre-commit operations (pull, cleanup)
    4. Stage and commit changes (AI or manual)
    5. Push to remote (if configured)
    6. Display timing and success status

Visual Components:
    - Repository panel: Shows repo name and path
    - Status table: Tracks operation results
    - File tree: Displays changed files with icons
    - Commit panel: Shows commit details
    - Progress indicators: Spinners and status messages
"""

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

# Global console instance for consistent output
console = Console()


def process_repository(
    entry_path, entry, args, task_id=None, progress=None, orig_cwd=None
):
    """
        Process a single git repository with visual enhancements using Rich.

        Executes the complete git automation workflow for one repository,
        including pulling changes, staging modifications, committing with
        AI-generated or custom messages, and optionally pushing to remote.
        Provides detailed visual feedback throughout the process.

        Args:
            entry_path: Absolute path to the repository directory
            entry: Display name for the repository (typically dirname)
            args: Configuration object with operation flags:
                - pull: Pull from remote before committing
                - handle_gitignore: Auto-update .gitignore
                - remove_ds_store: Remove macOS .DS_Store files
                - use_ai_commit: Generate commit message with AI
                - commit_message: Custom message or "auto-commit" for AI
                - auto_push: Push after committing
                - dry_run: Preview without making changes
                - show_diff: Display changes before committing
                - status_only: Show status without committing
            task_id: Optional progress bar task ID for parallel processing
            progress: Optional Rich Progress object for task updates
            orig_cwd: Original working directory to restore after processing

        Returns:
            True if processing succeeded
            False if any operation failed

        Side Effects:
            - Changes current working directory to entry_path
            - Executes git commands (unless dry_run)
            - Prints Rich UI elements to console
            - Restores original working directory in finally block

        Workflow Steps:
            1. Display repository header panel
            2. Change to repository directory
            3. Display current branch with appropriate styling
            4. Execute pre-commit operations:
               - Pull latest changes (if args.pull)
               - Update .gitignore (if args.handle_gitignore)
               - Remove .DS_Store files (if args.remove_ds_store)
            5. Stage and commit changes:
               - Use ai_commit binary (if args.use_ai_commit)
               - Or manual git add/commit workflow
            6. Display commit details
            7. Push to remote (if args.auto_push)
            8. Show timing and success status

        Error Handling:
            - Catches subprocess.CalledProcessError for git failures
            - Displays error details in styled panel
            - Returns False to indicate failure
            - Always restores working directory

        Performance Tracking:
            - Measures elapsed time with start_time/end_time
            - Displays processing duration to 2 decimal places
            - Useful for identifying slow operations

        Visual Feedback:
            - Repository panel with name and path
            - Branch information with color coding
            - Status table for operation results
            - File tree showing changes with icons
            - Commit details panel
            - Push results panel
            - Processing time
            - Success/failure indicators
            - Visual separator at end

        Example Usage:
    ```python
            from iskra.ui.display import process_repository

            class Args:
                pull = True
                use_ai_commit = True
                commit_message = "auto-commit"
                auto_push = True
                handle_gitignore = False
                remove_ds_store = False

            success = process_repository(
                entry_path="/path/to/repo",
                entry="my-repo",
                args=Args(),
                orig_cwd=os.getcwd()
            )
    ```

        Integration:
            This function is called by auto_commit.py for each repository
            being processed. It can run sequentially or with progress bars
            for batch processing.

        Note:
            The function temporarily changes the working directory. Always
            pass orig_cwd to ensure proper restoration, especially when
            processing multiple repositories sequentially.
    """
    # Display repository header with name and path
    # Creates visual separation between repositories in batch processing
    repo_panel = Panel(
        f"[bold cyan]{get_icon('project')} {entry}[/]",
        border_style="blue",
        title=f"[bold]Repository[/]",
        title_align="left",
        subtitle=f"[dim]{entry_path}[/]",  # Full path shown dimmed
        subtitle_align="right",
    )
    console.print(repo_panel)

    # Start timing for performance tracking
    start_time = time.time()

    # Update progress bar if using parallel processing
    if progress and task_id:
        progress.update(task_id, description=f"[cyan]Processing {entry}[/]")

    # Change to repository directory for git operations
    # All git commands expect to run from repo root
    os.chdir(entry_path)

    try:
        # === BRANCH INFORMATION ===
        # Get current branch name (main, master, feature/xyz, etc.)
        current_branch = get_current_branch()

        # Style branch name based on importance
        # Main/master branches get magenta (primary), others get yellow (secondary)
        branch_style = "magenta" if current_branch in ["main", "master"] else "yellow"

        # Use different icon for main branches vs feature branches
        branch_icon = (
            get_icon("main_branch")
            if current_branch in ["main", "master"]
            else get_icon("branch")
        )

        console.print(
            f"{branch_icon} On branch: [bold {branch_style}]{current_branch}[/]"
        )

        # === STATUS TABLE SETUP ===
        # Create table for tracking operation results
        # Hidden header, compact layout for clean display
        status_table = Table(
            show_header=False,  # No column headers
            box=None,  # No border lines
            padding=(0, 1, 0, 1),  # Minimal padding
            collapse_padding=True,  # Tight layout
        )
        status_table.add_column("Icon", style="cyan")
        status_table.add_column("Status", style="white")
        status_table.add_column("Details", style="green")

        # === PRE-COMMIT OPERATIONS ===

        # Pull latest changes from remote
        # Ensures we're committing on top of latest work
        if args.pull:
            with console.status(
                "[bold blue]Pulling latest changes...[/]", spinner="dots"
            ):
                pull_result = git_pull()
            status_table.add_row(
                get_icon("pull"), "Pulled changes", pull_result.stdout.strip()
            )

        # Handle .gitignore file
        # Automatically adds .DS_Store and other common patterns
        if args.handle_gitignore:
            gitignore_updated = handle_gitignore(entry_path)
            if gitignore_updated:
                status_table.add_row(
                    get_icon("config"),
                    "Updated .gitignore",
                    "Added .DS_Store to ignore list",
                )

        # Remove macOS .DS_Store files
        # Prevents committing OS-specific metadata
        if args.remove_ds_store:
            ds_store_count = remove_ds_store_files()
            if ds_store_count > 0:
                status_table.add_row(
                    get_icon("remove"),
                    "Removed .DS_Store files",
                    f"{ds_store_count} files removed",
                )

        # Display status table only if operations were performed
        # Keeps output clean when no pre-commit actions taken
        if status_table.row_count > 0:
            console.print(status_table)

        # === COMMIT WORKFLOW ===

        if args.use_ai_commit:
            # === AI-POWERED COMMIT PATH ===
            # Use bundled ai_commit binary for intelligent commit messages

            # Determine commit message
            # Use custom message if provided, otherwise AI generates one
            commit_message = (
                args.commit_message
                if args.commit_message != "auto-commit"
                else generate_commit_message()
            )

            console.print(
                f"\n[bold cyan]{get_icon('commit')} Using ai_commit command[/]"
            )
            console.print("[bold blue]Executing ai_commit...[/]")

            # Execute ai_commit binary
            # Binary handles staging, commit message generation, and committing
            result = subprocess.run(
                ["ai_commit", commit_message],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Display ai_commit results
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
            # === MANUAL GIT WORKFLOW ===
            # Standard git add/commit/push workflow without AI

            # Stage all changes
            console.print("[bold blue]Staging changes...[/]")
            git_add_all()

            # Check for changes to commit
            # git status --porcelain returns empty string if clean
            status_output = git_status_porcelain()

            if status_output == "":
                # No changes - nothing to commit
                console.print(f"[dim]{get_icon('info')} No changes to commit[/]")
            else:
                # === CHANGES DETECTED ===

                # Parse changed files from status output
                changes = status_output.split("\n")

                # Create visual tree of changes with icons
                tree = Tree(f"[bold yellow]{len(changes)} files changed[/]")

                for change in changes:
                    if not change.strip():
                        continue

                    # Parse git status line format: "XY filename"
                    # X = staged status, Y = unstaged status
                    status_code = change[:2].strip()
                    file_path = change[3:].strip()

                    # Map status codes to human-readable text and colors
                    # M = Modified, A = Added, D = Deleted, R = Renamed, ?? = Untracked
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
                        # Unknown status code - display as-is
                        status_text = status_code
                        style = "white"

                    # Add file to tree with appropriate icon and styling
                    tree.add(
                        f"[{style}]{get_file_icon(file_path)} {file_path}[/] "
                        f"([bold {style}]{status_text}[/])"
                    )

                # Display the tree of changes
                console.print(tree)

                # Generate or use custom commit message
                commit_message = (
                    args.commit_message
                    if args.commit_message != "auto-commit"
                    else generate_commit_message()
                )

                # Commit the staged changes
                console.print(f"[bold blue]Committing changes: {commit_message}[/]")
                git_commit(commit_message)

                # === COMMIT SUMMARY ===
                # Display details of the commit just created
                console.print(f"\n[bold green]{get_icon('commit')} Commit Summary[/]")

                # Get commit details with git show
                show_result = git_show_last_commit()

                # Format commit info in a styled panel
                commit_panel = Panel(
                    show_result.stdout.strip(),
                    title="[bold green]Commit Details[/]",
                    border_style="green",
                    padding=(1, 2),
                )
                console.print(commit_panel)

                # === PUSH TO REMOTE ===
                # Upload commits to remote repository if configured
                if hasattr(args, "auto_push") and args.auto_push:
                    console.print("[bold blue]Pushing to remote...[/]")
                    push_result = git_push()

                    # Display push results
                    # Show detailed output if available, otherwise generic success
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
                    # auto_push attribute exists but is False
                    console.print(
                        f"[dim]{get_icon('info')} Skipping push (auto_push disabled)[/]"
                    )

        # === COMPLETION STATUS ===

        # Calculate and display processing time
        end_time = time.time()
        elapsed = end_time - start_time

        console.print(
            f"\n{get_icon('clock')} Processed in [bold cyan]{elapsed:.2f}[/] seconds"
        )

        # Success message with sparkles for celebration
        console.print(
            f"[bold green]{get_icon('sparkles')} Successfully processed {entry} {get_icon('sparkles')}[/]"
        )

        # Update progress bar if using parallel processing
        if progress and task_id:
            progress.update(task_id, advance=1)

        return True

    except subprocess.CalledProcessError as e:
        # === ERROR HANDLING ===
        # Git command failed - display error details

        console.print(f"[bold red]{get_icon('error')} Error processing {entry}:[/]")
        console.print(Panel(str(e), title="Error Details", border_style="red"))

        # Update progress bar even on failure
        if progress and task_id:
            progress.update(task_id, advance=1)

        return False

    finally:
        # === CLEANUP ===
        # Always restore original working directory
        # Critical for sequential processing of multiple repos
        if orig_cwd:
            os.chdir(orig_cwd)

        # Visual separator between repositories
        # Creates clear boundaries in batch processing output
        separator_count = shutil.get_terminal_size().columns // 2
        console.print(f"[dim cyan]{get_icon('separator') * separator_count}[/]")
