import os
import time
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich import box

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


@dataclass
class RepositoryState:
    """Represents the current state of a repository."""

    path: str
    name: str
    branch: str
    is_clean: bool
    status_output: str
    changes_count: int = 0

    @property
    def has_changes(self) -> bool:
        return not self.is_clean


@dataclass
class ProcessingResult:
    """Result of processing a repository."""

    success: bool
    elapsed_time: float


class RepositoryDisplay:
    """Handles display output for repository processing."""

    def __init__(self, console: Console):
        self.console = console

    def show_minimal_clean(self, name: str, branch: str):
        """Show minimal one-line output for clean repositories."""
        self.console.print(
            f"  [dim cyan]•[/] [white]{name:<40}[/] "
            f"[dim green]✓[/] "
            f"[dim]{branch}[/]"
        )

    def show_repository_header(self, state: RepositoryState, path: str):
        """Display repository header with modern minimal design."""
        # Use subtle color gradient effect
        status_indicator = "●" if state.has_changes else "○"
        status_color = "yellow" if state.has_changes else "green"

        self.console.print()
        self.console.print(
            f"[bold white]{get_icon('project')} {state.name}[/]  "
            f"[{status_color}]{status_indicator}[/]"
        )
        self.console.print(f"[dim]{path}[/]")

    def show_branch_info(self, branch: str):
        """Display current branch information."""
        is_main = branch in ["main", "master"]
        style = "magenta" if is_main else "cyan"
        icon = get_icon("main_branch") if is_main else get_icon("branch")

        self.console.print(f"  {icon} [dim]on[/] [{style}]{branch}[/]")

    def show_clean_status(self):
        """Display status for clean repository."""
        self.console.print(f"  [dim green]✓[/] [dim]working tree clean[/]")

    def show_changes_tree(self, status_output: str):
        """Display list of changed files with modern styling."""
        changes = [c for c in status_output.split("\n") if c.strip()]

        self.console.print(f"  [dim]Changes:[/] [yellow]{len(changes)}[/]")
        self.console.print()

        for change in changes[:15]:  # Limit to first 15 for cleaner display
            status_code = change[:2].strip()
            file_path = change[3:].strip()
            status_text, style = self._get_status_display(status_code)

            # Clean, minimal file listing
            self.console.print(
                f"    [{style}]{status_text[0]}[/] "
                f"[dim]{get_file_icon(file_path)}[/] "
                f"{file_path}"
            )

        if len(changes) > 15:
            self.console.print(f"    [dim]... and {len(changes) - 15} more[/]")

    def _get_status_display(self, status_code: str) -> tuple[str, str]:
        """Get display text and style for a status code."""
        status_map = {
            "M": ("Modified", "blue"),
            "A": ("Added", "green"),
            "D": ("Deleted", "red"),
            "R": ("Renamed", "magenta"),
            "??": ("Untracked", "yellow"),
        }
        return status_map.get(status_code, (status_code, "white"))

    def show_status_only_message(self):
        """Display message for status-only mode."""
        self.console.print(f"\n  [dim cyan]ℹ[/] [dim]status only mode[/]")

    def show_pull_only_message(self, name: str, has_changes: bool):
        """Display message for pull-only mode."""
        if has_changes:
            self.console.print(
                f"  [cyan]↓[/] [white]pulled changes[/] [dim]({name})[/]"
            )
        else:
            self.console.print(
                f"  [dim green]✓[/] [dim]already up to date[/] [dim]({name})[/]"
            )

    def show_commit_panel(self, commit_output: str):
        """Display commit details in minimal format."""
        lines = commit_output.strip().split("\n")

        self.console.print(f"\n  [dim]Commit:[/]")
        for line in lines[:5]:  # Show first 5 lines
            self.console.print(f"    [dim]{line}[/]")

    def show_push_result(self, push_output: str):
        """Display push result."""
        self.console.print(f"  [cyan]↑[/] [dim]pushed to remote[/]")

    def show_elapsed_time(self, elapsed: float):
        """Display processing time."""
        self.console.print(f"\n  [dim]completed in {elapsed:.2f}s[/]")

    def show_success(self, name: str):
        """Display success message."""
        self.console.print(f"  [green]✓[/] [dim]success[/]")

    def show_error(self, name: str, error: str):
        """Display error message."""
        self.console.print(f"  [red]✗[/] [red]error:[/] {name}")
        # Show error without heavy box
        error_lines = error.split("\n")
        for line in error_lines[:3]:  # Show first 3 lines
            self.console.print(f"    [dim red]{line}[/]")

    def show_separator(self):
        """Display subtle separator line."""
        self.console.print()


class GitOperationsHandler:
    """Handles Git operations for repository processing."""

    def __init__(self, display: RepositoryDisplay):
        self.display = display

    def pull_changes(self, args) -> tuple[bool, str]:
        """Pull changes from remote. Returns (has_new_changes, message)."""
        with console.status("[dim]pulling...[/]", spinner="dots"):
            result = git_pull()

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        is_up_to_date = (
            "Already up to date" in stdout
            or "Already up to date" in stderr
            or stdout == ""
        )

        return not is_up_to_date, stdout if stdout else stderr

    def add_pull_status_to_table(self, table: Table, has_changes: bool, message: str):
        """Add pull operation status to table."""
        icon = "↓" if has_changes else "○"
        status = "pulled" if has_changes else "up to date"

        table.add_row(icon, status, "")

    def handle_file_cleanup(self, args, table: Table) -> bool:
        """Handle gitignore and DS_Store cleanup. Returns True if changes made."""
        changes_made = False

        if args.handle_gitignore:
            if handle_gitignore(os.getcwd()):
                table.add_row("•", "updated .gitignore", "")
                changes_made = True

        if args.remove_ds_store:
            count = remove_ds_store_files()
            if count > 0:
                table.add_row("•", f"removed {count} .DS_Store files", "")
                changes_made = True

        return changes_made

    def commit_with_ai(self, commit_message: str) -> bool:
        """Commit using ai_commit command. Returns success status."""
        console.print(f"\n  [cyan]◆[/] [dim]using ai_commit[/]")

        result = subprocess.run(
            ["ai_commit", commit_message],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        if result.returncode == 0:
            console.print(f"  [green]✓[/] [dim]ai commit successful[/]")
            return True
        else:
            console.print(f"  [red]✗[/] [red]ai commit failed[/]")
            if result.stderr.strip():
                console.print(f"    [dim red]{result.stderr.strip()[:100]}[/]")
            return False

    def commit_standard(self, commit_message: str):
        """Perform standard git commit."""
        console.print(f"  [dim]staging...[/]")
        git_add_all()

        console.print(f"  [dim]committing:[/] {commit_message}")
        git_commit(commit_message)

        show_result = git_show_last_commit()
        self.display.show_commit_panel(show_result.stdout)

    def push_if_enabled(self, args) -> Optional[str]:
        """Push changes if auto_push is enabled. Returns push output."""
        if not hasattr(args, "auto_push"):
            return None

        if args.auto_push:
            console.print(f"  [dim]pushing...[/]")
            push_result = git_push()
            return push_result.stdout
        else:
            console.print(f"  [dim]skipping push[/]")
            return None


class RepositoryProcessor:
    """Main processor for repository operations."""

    def __init__(self):
        self.display = RepositoryDisplay(console)
        self.git_ops = GitOperationsHandler(self.display)

    def process(
        self,
        entry_path: str,
        entry: str,
        args,
        task_id=None,
        progress=None,
        orig_cwd: Optional[str] = None,
    ) -> bool:
        """Process a single repository."""
        start_time = time.time()

        try:
            os.chdir(entry_path)

            # Get initial repository state
            state = self._get_repository_state(entry_path, entry)

            # Handle compact display for clean repos
            if self._should_show_minimal(args, state):
                self.display.show_minimal_clean(state.name, state.branch)
                self._update_progress(progress, task_id)
                return True

            # Process pull operation
            status_table = self._create_status_table()

            if args.pull:
                state = self._handle_pull(args, state, status_table)

                # Early exit for pull-only mode
                if getattr(args, "pull_only", False):
                    has_changes = state.status_output != ""
                    self.display.show_pull_only_message(state.name, has_changes)
                    self._update_progress(progress, task_id)
                    return True

            # Show full repository display
            self.display.show_repository_header(state, entry_path)

            if progress and task_id:
                progress.update(task_id, description=f"[dim]processing {entry}[/]")

            self.display.show_branch_info(state.branch)

            # Show repository status
            if state.is_clean:
                self.display.show_clean_status()
            else:
                self.display.show_changes_tree(state.status_output)

            # Status-only mode: show status and exit
            if args.status_only:
                self.display.show_status_only_message()
                elapsed = time.time() - start_time
                self.display.show_elapsed_time(elapsed)
                self._update_progress(progress, task_id)
                return True

            # Perform file cleanup operations
            self.git_ops.handle_file_cleanup(args, status_table)

            # Display status table if it has entries
            if status_table.row_count > 0:
                console.print()
                console.print(status_table)

            # Commit changes if present
            if state.has_changes:
                commit_message = self._get_commit_message(args)

                if args.use_ai_commit:
                    success = self.git_ops.commit_with_ai(commit_message)
                    if not success:
                        return False
                else:
                    self.git_ops.commit_standard(commit_message)

                # Push if enabled
                push_output = self.git_ops.push_if_enabled(args)
                if push_output is not None:
                    self.display.show_push_result(push_output)

            # Show completion messages
            elapsed = time.time() - start_time
            self.display.show_elapsed_time(elapsed)
            self.display.show_success(entry)

            self._update_progress(progress, task_id)
            return True

        except subprocess.CalledProcessError as e:
            self.display.show_error(entry, str(e))
            self._update_progress(progress, task_id)
            return False

        finally:
            if orig_cwd:
                os.chdir(orig_cwd)
            self.display.show_separator()

    def _get_repository_state(self, path: str, name: str) -> RepositoryState:
        """Get current repository state."""
        branch = get_current_branch()
        status_output = git_status_porcelain()
        is_clean = status_output == ""
        changes_count = len([c for c in status_output.split("\n") if c.strip()])

        return RepositoryState(
            path=path,
            name=name,
            branch=branch,
            is_clean=is_clean,
            status_output=status_output,
            changes_count=changes_count,
        )

    def _should_show_minimal(self, args, state: RepositoryState) -> bool:
        """Determine if minimal display should be used."""
        return (
            getattr(args, "status_only", False)
            and getattr(args, "compact", False)
            and state.is_clean
        )

    def _create_status_table(self) -> Table:
        """Create a minimal status table for operations."""
        table = Table(
            show_header=False,
            box=None,
            padding=(0, 1),
            collapse_padding=True,
            show_edge=False,
        )
        table.add_column("", style="cyan", width=2)
        table.add_column("", style="dim white")
        table.add_column("", style="dim")
        return table

    def _handle_pull(
        self, args, state: RepositoryState, table: Table
    ) -> RepositoryState:
        """Handle pull operation and update state."""
        has_changes, message = self.git_ops.pull_changes(args)
        self.git_ops.add_pull_status_to_table(table, has_changes, message)

        # Refresh state after pull
        return self._get_repository_state(state.path, state.name)

    def _get_commit_message(self, args) -> str:
        """Get commit message from args or generate one."""
        if args.commit_message != "auto-commit":
            return args.commit_message
        return generate_commit_message()

    def _update_progress(self, progress, task_id):
        """Update progress bar if available."""
        if progress and task_id:
            progress.update(task_id, advance=1)


# Public API - maintain backward compatibility
def process_repository(
    entry_path, entry, args, task_id=None, progress=None, orig_cwd=None
):
    """
    Process a single repository.

    This is the main entry point for repository processing, maintaining
    backward compatibility with existing code.
    """
    processor = RepositoryProcessor()
    return processor.process(entry_path, entry, args, task_id, progress, orig_cwd)
