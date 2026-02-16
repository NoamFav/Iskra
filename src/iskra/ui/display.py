"""
The display module. Makes things pretty in the terminal.

All the Rich formatting, progress bars, trees, colors, the whole visual circus.
Also the main repo processing loop lives here because separation of concerns
is for people with more patience than me.
"""

import os
import time
import subprocess
from dataclasses import dataclass
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from .formatting import get_icon, get_file_icon, style, get_color
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
    generate_smart_commit_message,
    git_diff_full,
    git_stash,
    git_stash_pop,
    check_for_conflicts,
    check_would_conflict_on_pull,
    is_ssh_remote,
    check_ssh_agent_has_keys,
    is_protected_branch,
    run_hook_command,
)
from ..core.ai_providers import AIConfig, generate_commit_message_with_ai


# The one console to rule them all
console = Console()


@dataclass
class RepositoryState:
    """Snapshot of a repo. Where it is, what branch, how dirty."""

    path: str
    name: str
    branch: str
    is_clean: bool
    status_output: str
    changes_count: int = 0

    @property
    def has_changes(self) -> bool:
        """The opposite of is_clean. Because naming is hard."""
        return not self.is_clean


@dataclass
class ProcessingResult:
    """Did it work? How long did it take? That's all you need to know."""

    success: bool
    elapsed_time: float


class RepositoryDisplay:
    """Pretty printer for repo stuff. Colors, icons, trees, the works."""

    def __init__(self, console: Console):
        """Gimme a console and I'll make it pretty."""
        self.console = console

    def show_minimal_clean(self, name: str, branch: str) -> None:
        """One liner for clean repos. Nothing to see here."""
        self.console.print(
            f"  [dim cyan]•[/] [white]{name:<40}[/] "
            f"[dim green]✓[/] "
            f"[dim]{branch}[/]"
        )

    def show_repository_header(self, state: RepositoryState, path: str) -> None:
        """Show the repo name with a dirty/clean indicator. Filled = dirty."""
        status_indicator = "●" if state.has_changes else "○"
        status_color = "yellow" if state.has_changes else "green"

        self.console.print()
        self.console.print(
            f"[bold white]{get_icon('project')} {state.name}[/]  "
            f"[{status_color}]{status_indicator}[/]"
        )
        self.console.print(f"[dim]{path}[/]")

    def show_branch_info(self, branch: str) -> None:
        """Show what branch we're on. main/master get special treatment."""
        is_main = branch in ["main", "master"]
        style = "magenta" if is_main else "cyan"
        icon = get_icon("main_branch") if is_main else get_icon("branch")

        self.console.print(f"  {icon} [dim]on[/] [{style}]{branch}[/]")

    def show_clean_status(self) -> None:
        """Nothing to commit. Good job or whatever."""
        self.console.print(
            "  [dim green]✓[/] [dim]working tree clean[/]",
        )

    def show_changes_tree(self, status_output: str) -> None:
        """Pretty tree of what files changed. M for modified, A for added, etc."""
        changes = [c for c in status_output.split("\n") if c.strip()]
        tree = Tree(f"[bold yellow]{len(changes)} files changed[/]")

        for change in changes:
            status_code = change[:2].strip()
            file_path = change[3:].strip()
            status_text, style = self._get_status_display(status_code)

            tree.add(
                f"[{style}]{get_file_icon(file_path)} {file_path}[/] "
                f"([bold {style}]{status_text}[/])"
            )

        self.console.print(tree)

    def _get_status_display(self, status_code: str) -> tuple[str, str]:
        """Turn git's cryptic status codes into words humans understand."""
        status_map = {
            "M": ("Modified", "blue"),
            "A": ("Added", "green"),
            "D": ("Deleted", "red"),
            "R": ("Renamed", "magenta"),
            "??": ("Untracked", "yellow"),
        }
        return status_map.get(status_code, (status_code, "white"))

    def show_status_only_message(self) -> None:
        """We're just looking, not touching."""
        self.console.print(
            "\n  [dim cyan]ℹ[/] [dim]status only mode[/]",
        )

    def show_pull_only_message(self, name: str, has_changes: bool) -> None:
        """Tell em if we got new stuff from remote or not."""
        if has_changes:
            self.console.print(
                f"  [cyan]↓[/] [white]pulled changes[/] [dim]({name})[/]"
            )
        else:
            self.console.print(
                f"  [dim green]✓[/] [dim]already up to date[/] [dim]({
                    name
                })[/]"
            )

    def show_commit_panel(self, commit_output: str, is_ai: bool = False) -> None:
        """Show the commit hash and message. Fancy formatting included."""
        lines = commit_output.strip().split("\n")

        # Extract commit hash and message
        commit_hash = None
        commit_msg = None

        for line in lines:
            if line.startswith("commit "):
                commit_hash = line.split()[1][:7]  # Short hash
            elif (
                commit_msg is None
                and line.strip()
                and not line.startswith(("commit", "Author:", "Date:"))
            ):
                commit_msg = line.strip()

        # Build the display
        self.console.print()

        if is_ai:
            self.console.print(
                "  [cyan][/] [bold]AI Generated Commit[/]",
            )
        else:
            self.console.print(
                "  [cyan]✓[/] [bold]Committed[/]",
            )

        if commit_hash:
            self.console.print(
                f"    [dim]hash:[/] [cyan]{commit_hash}[/]",
            )

        if commit_msg:
            # Wrap long messages nicely
            if len(commit_msg) > 60:
                self.console.print(
                    f"    [dim]msg:[/]  [white]{commit_msg[:60]}...[/]",
                )
            else:
                self.console.print(
                    f"    [dim]msg:[/]  [white]{commit_msg}[/]",
                )

    def show_ai_commit_thinking(self, changes_count: int) -> None:
        """Robot is thinking... analyzing your garbage code..."""
        self.console.print()
        self.console.print(
            f"  [cyan]◆[/] [dim]analyzing {
                changes_count
            } change{
                's' if changes_count != 1 else ''
            }...[/]"
        )

    def show_push_result(self, push_output: str) -> None:
        """Pushed to remote. Show which branch got the goods."""
        lines = push_output.split("\n")
        branch_line = None

        for line in lines:
            if "->" in line and "refs/heads" in line:
                branch_line = line.strip()
                break

        self.console.print()
        self.console.print("  [cyan]↑[/] [white]Pushed to remote[/]")

        if branch_line:
            # Clean up the branch display
            parts = branch_line.split("->")
            if len(parts) == 2:
                remote_branch = parts[1].strip().replace("refs/heads/", "")
                self.console.print(f"    [dim]→ {remote_branch}[/]")

    def show_elapsed_time(self, elapsed: float) -> None:
        """How long did that take? Let's flex."""
        self.console.print(f"\n  [dim]completed in {elapsed:.2f}s[/]")

    def show_success(self, name: str) -> None:
        """Green checkmark. We did it. Celebrate."""
        self.console.print("  [green]✓[/] [white]success[/]")

    def show_error(self, name: str, error: str) -> None:
        """Red X. Something broke. Show what went wrong."""
        self.console.print(f"  [red]✗[/] [red]error:[/] {name}")
        error_lines = error.split("\n")
        for line in error_lines[:3]:
            self.console.print(f"    [dim red]{line}[/]")

    def show_separator(self) -> None:
        """Blank line. Riveting stuff."""
        self.console.print()


class GitOperationsHandler:
    """Git operations but with pretty output. Pull, commit, push, the usual."""

    def __init__(self, display: RepositoryDisplay):
        """Give me a display and I'll show you some git magic."""
        self.display = display

    def pull_changes(self, args) -> tuple[bool, str]:
        """Pull from remote. Returns whether we got new stuff."""
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

    def add_pull_status_to_table(
        self,
        table: Table,
        has_changes: bool,
        message: str,
    ) -> None:
        """Add a row to the status table for pull results."""
        icon = "↓" if has_changes else "○"
        status = "pulled" if has_changes else "up to date"

        table.add_row(icon, status, "")

    def handle_file_cleanup(self, args, table: Table) -> bool:
        """Clean up .DS_Store and fix .gitignore. macOS users, you're welcome."""
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

    def commit_with_ai(
        self,
        commit_message: str,
        changes_count: int,
        ai_provider: str = "ollama",
        ai_config: Optional[AIConfig] = None,
    ) -> tuple[bool, Optional[str]]:
        """Let the robots write your commit message. They're probably better at it."""
        self.display.show_ai_commit_thinking(changes_count)

        # For non-ollama providers, generate message and commit manually
        if ai_provider.lower() in ("openai", "claude") and ai_config:
            with console.status(
                f"[dim]generating commit with {ai_provider}...[/]",
                spinner="dots",
            ):
                diff = git_diff_full()
                branch = get_current_branch()
                generated_msg = generate_commit_message_with_ai(
                    diff, branch, ai_config
                )

            if generated_msg:
                console.print(f"  [cyan]✓[/] [dim]AI generated: {generated_msg}[/]")
                git_add_all()
                git_commit(generated_msg)
                show_result = git_show_last_commit()
                return True, show_result.stdout
            else:
                console.print(f"  [yellow]⚠[/] [yellow]{ai_provider} failed[/]")
                return False, None

        # Default: use ollama via ai_commit binary
        with console.status(
            "[dim]generating commit with AI...[/]",
            spinner="dots",
        ):
            result = subprocess.run(
                ["ai_commit", commit_message],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

        if result.returncode == 0:
            # Get the actual commit details
            show_result = git_show_last_commit()
            return True, show_result.stdout
        else:
            console.print("  [red]✗[/] [red]AI commit failed[/]")
            if result.stderr.strip():
                console.print(f"    [dim red]{result.stderr.strip()[:100]}[/]")
            return False, None

    def commit_standard(self, commit_message: str) -> str:
        """Stage everything and commit. Old school."""
        console.print("\n  [dim]staging changes...[/]")
        git_add_all()

        console.print("  [dim]committing...[/]")
        git_commit(commit_message)

        show_result = git_show_last_commit()
        return show_result.stdout

    def push_if_enabled(self, args) -> Optional[str]:
        """Push if we're supposed to. Otherwise just chill."""
        if not hasattr(args, "auto_push"):
            return None

        if args.auto_push:
            with console.status("[dim]pushing...[/]", spinner="dots"):
                push_result = git_push()
            return push_result.stdout
        else:
            console.print("\n  [dim cyan]ℹ[/] [dim]auto-push disabled[/]")
            return None


class RepositoryProcessor:
    """
    The big boss. Orchestrates the whole show.
    Pull, stash, commit, push, hooks, the whole pipeline.
    """

    def __init__(self):
        """Set up the display and git handlers. Let's do this."""
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
        """
        The main event. Process a repo through the whole pipeline.
        Pull, commit, push, whatever's configured. Returns True if we made it.

        I'm losing my mind this function is 200 lines long but it works so
        don't touch it please I'm begging you.
        """
        start_time = time.time()
        stashed = False

        try:
            os.chdir(entry_path)

            # Get initial repository state
            state = self._get_repository_state(entry_path, entry)

            # Handle compact display for clean repos
            if self._should_show_minimal(args, state):
                self.display.show_minimal_clean(state.name, state.branch)
                self._update_progress(progress, task_id)
                return True

            # Check SSH keys if enabled and using SSH remote
            if getattr(args, "check_ssh_keys", True):
                self._check_ssh_keys()

            # Check for existing conflicts
            if getattr(args, "warn_conflicts", True):
                conflicts = check_for_conflicts()
                if conflicts:
                    console.print(
                        f"  [red]⚠[/] [red]Merge conflicts detected "
                        f"in {len(conflicts)} file(s)[/]"
                    )
                    for f in conflicts[:3]:
                        console.print(f"    [dim red]• {f}[/]")
                    if len(conflicts) > 3:
                        console.print(
                            f"    [dim red]... and {len(conflicts) - 3} more[/]"
                        )
                    return False

            # Process pull operation
            status_table = self._create_status_table()

            if args.pull:
                # Auto-stash if enabled and there are changes
                if getattr(args, "auto_stash", False) and state.has_changes:
                    stashed = git_stash()
                    if stashed:
                        console.print("  [cyan]⎘[/] [dim]stashed local changes[/]")

                # Check for potential conflicts before pulling
                if getattr(args, "warn_conflicts", True):
                    if check_would_conflict_on_pull():
                        console.print(
                            "  [yellow]⚠[/] [yellow]Pull would cause conflicts[/]"
                        )
                        console.print(
                            "    [dim]Resolve manually or use --no-conflict-check[/]"
                        )
                        if stashed:
                            git_stash_pop()
                        return False

                state = self._handle_pull(args, state, status_table)

                # Restore stashed changes
                if stashed:
                    if git_stash_pop():
                        console.print("  [cyan]⎘[/] [dim]restored stashed changes[/]")
                    else:
                        console.print(
                            "  [yellow]⚠[/] [yellow]Could not restore stash "
                            "(may have conflicts)[/]"
                        )
                    stashed = False
                    # Refresh state after stash pop
                    state = self._get_repository_state(state.path, state.name)

                # Early exit for pull-only mode
                if getattr(args, "pull_only", False):
                    has_changes = state.status_output != ""
                    self.display.show_pull_only_message(
                        state.name,
                        has_changes,
                    )
                    self._update_progress(progress, task_id)
                    return True

            # Show full repository display
            self.display.show_repository_header(state, entry_path)

            if progress and task_id:
                progress.update(
                    task_id,
                    description=f"[dim]processing {entry}[/]",
                )

            self.display.show_branch_info(state.branch)

            # Protected branch warning
            protected_branches = getattr(
                args, "protected_branches", ["main", "master", "production"]
            )
            if is_protected_branch(state.branch, protected_branches):
                console.print(
                    f"  [yellow]⚠[/] [yellow]Protected branch: {state.branch}[/]"
                )
                if getattr(args, "require_confirmation_for_protected", True):
                    if not getattr(args, "yes", False):
                        console.print(
                            "    [dim]Use -y to confirm operations on "
                            "protected branches[/]"
                        )
                        return False

            # Show repository status
            if state.is_clean:
                self.display.show_clean_status()
            else:
                self.display.show_changes_tree(state.status_output)

            # Show diff if requested
            if getattr(args, "show_diff", False) and state.has_changes:
                self._show_diff()

            # Status-only mode: show status and exit
            if args.status_only:
                self.display.show_status_only_message()
                elapsed = time.time() - start_time
                self.display.show_elapsed_time(elapsed)
                self._update_progress(progress, task_id)
                return True

            # Dry-run mode: show what would be done and exit
            if getattr(args, "dry_run", False):
                console.print("\n  [cyan]ℹ[/] [cyan]Dry run mode[/]")
                if state.has_changes:
                    console.print("    [dim]Would commit changes[/]")
                    if getattr(args, "auto_push", True):
                        console.print("    [dim]Would push to remote[/]")
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
                # Run pre-commit hook if defined
                pre_commit = getattr(args, "pre_commit_command", None)
                if pre_commit:
                    console.print(f"  [dim]running pre-commit: {pre_commit}[/]")
                    retcode, stdout, stderr = run_hook_command(pre_commit, entry_path)
                    if retcode != 0:
                        console.print("  [red]✗[/] [red]pre-commit hook failed[/]")
                        if stderr:
                            console.print(f"    [dim red]{stderr[:200]}[/]")
                        return False

                commit_message = self._get_commit_message(args, state.status_output)

                if args.use_ai_commit:
                    # Build AI config from args - this is fine everything is fine
                    ai_config = AIConfig(
                        provider=getattr(args, "ai_provider", "ollama"),
                        openai_api_key=getattr(args, "openai_api_key", None),
                        openai_model=getattr(args, "openai_model", "gpt-4o-mini"),
                        claude_api_key=getattr(args, "claude_api_key", None),
                        claude_model=getattr(args, "claude_model", "claude-sonnet-4-20250514"),
                    )
                    success, commit_output = self.git_ops.commit_with_ai(
                        commit_message,
                        state.changes_count,
                        ai_provider=ai_config.provider,
                        ai_config=ai_config,
                    )
                    if not success:
                        # Fall back to smart commit message
                        console.print(
                            "  [yellow]↻[/] [dim]falling back to smart commit[/]"
                        )
                        fallback_msg = generate_smart_commit_message(
                            state.status_output
                        )
                        commit_output = self.git_ops.commit_standard(fallback_msg)
                    if commit_output:
                        self.display.show_commit_panel(
                            commit_output,
                            is_ai=True,
                        )
                else:
                    commit_output = self.git_ops.commit_standard(
                        commit_message,
                    )
                    self.display.show_commit_panel(commit_output, is_ai=False)

                # Run post-commit hook if defined
                post_commit = getattr(args, "post_commit_command", None)
                if post_commit:
                    console.print(f"  [dim]running post-commit: {post_commit}[/]")
                    retcode, stdout, stderr = run_hook_command(post_commit, entry_path)
                    if retcode != 0:
                        console.print(
                            "  [yellow]⚠[/] [yellow]post-commit hook failed[/]"
                        )
                        if stderr:
                            console.print(f"    [dim yellow]{stderr[:200]}[/]")

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
            # Restore stash if we failed mid-process
            if stashed:
                git_stash_pop()
            if orig_cwd:
                os.chdir(orig_cwd)
            self.display.show_separator()

    def _check_ssh_keys(self) -> None:
        """Warn if SSH remote but no keys loaded. Save yourself the pain."""
        if is_ssh_remote() and not check_ssh_agent_has_keys():
            console.print(
                "  [yellow]⚠[/] [yellow]SSH remote but no keys in agent[/]"
            )
            console.print("    [dim]Run: ssh-add ~/.ssh/id_rsa[/]")

    def _show_diff(self) -> None:
        """Show the diff. Green = added, red = removed. You know the drill."""
        diff_output = git_diff_full()
        if diff_output:
            console.print("\n  [bold]Diff:[/]")
            # Limit diff output to avoid overwhelming the terminal
            lines = diff_output.split("\n")
            for line in lines[:50]:
                if line.startswith("+") and not line.startswith("+++"):
                    console.print(f"    [green]{line}[/]")
                elif line.startswith("-") and not line.startswith("---"):
                    console.print(f"    [red]{line}[/]")
                elif line.startswith("@@"):
                    console.print(f"    [cyan]{line}[/]")
                else:
                    console.print(f"    [dim]{line}[/]")
            if len(lines) > 50:
                console.print(f"    [dim]... ({len(lines) - 50} more lines)[/]")

    def _get_repository_state(self, path: str, name: str) -> RepositoryState:
        """Snapshot the repo state. Branch, changes, the usual suspects."""
        branch = get_current_branch()
        status_output = git_status_porcelain()
        is_clean = status_output == ""
        changes_count = len(
            [c for c in status_output.split("\n") if c.strip()],
        )

        return RepositoryState(
            path=path,
            name=name,
            branch=branch,
            is_clean=is_clean,
            status_output=status_output,
            changes_count=changes_count,
        )

    def _should_show_minimal(self, args, state: RepositoryState) -> bool:
        """Should we just show one line? Yes if status-only + compact + clean."""
        return (
            getattr(args, "status_only", False)
            and getattr(args, "compact", False)
            and state.is_clean
        )

    def _create_status_table(self) -> Table:
        """Make a little table for status stuff. Icon, text, details."""
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
        """Do the pull, update the table, return fresh state."""
        has_changes, message = self.git_ops.pull_changes(args)
        self.git_ops.add_pull_status_to_table(table, has_changes, message)

        # Refresh state after pull
        return self._get_repository_state(state.path, state.name)

    def _get_commit_message(self, args, status_output: str = "") -> str:
        """Get the commit message. Use custom if provided, otherwise get smart."""
        if args.commit_message != "auto-commit":
            return args.commit_message
        # Use smart commit message instead of random
        return generate_smart_commit_message(status_output)

    def _update_progress(self, progress, task_id) -> None:
        """Bump the progress bar if we have one."""
        if progress and task_id:
            progress.update(task_id, advance=1)


# The public API. Just this one function. Keep it simple.


def process_repository(
    entry_path: str,
    entry: str,
    args,
    task_id=None,
    progress=None,
    orig_cwd: str = None,
) -> bool:
    """
    Process a repo. The main entry point everyone uses.
    Does pull/commit/push based on args. Returns True if it worked.
    """
    processor = RepositoryProcessor()
    return processor.process(
        entry_path,
        entry,
        args,
        task_id,
        progress,
        orig_cwd,
    )
