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
    # Check if we should minimize output for clean repos
    minimize_clean = getattr(args, "status_only", False) and getattr(
        args, "compact", False
    )

    # We'll determine if repo is clean first, then decide on display
    os.chdir(entry_path)

    try:
        current_branch = get_current_branch()
        status_output = git_status_porcelain()
        is_clean = status_output == ""

        status_table = Table(
            show_header=False,
            box=None,
            padding=(0, 1, 0, 1),
            collapse_padding=True,
        )
        status_table.add_column("Icon", style="cyan")
        status_table.add_column("Status", style="white")
        status_table.add_column("Details", style="green")

        # Pull changes if requested (even in status-only mode)
        if args.pull:
            with console.status(
                "[bold blue]Pulling latest changes...[/]", spinner="dots"
            ):
                pull_result = git_pull()

            pull_stdout = pull_result.stdout.strip()
            pull_stderr = pull_result.stderr.strip()

            # Re-check status after pull
            status_output = git_status_porcelain()
            is_clean = status_output == ""

            # If we're in pull-only mode (sync/sync-all), just print a single line and bail
            if getattr(args, "pull_only", False):
                if (
                    "Already up to date" in pull_stdout
                    or "Already up to date" in pull_stderr
                    or pull_stdout == ""
                ):
                    console.print(
                        f"{get_icon('info')} [green]No new changes to pull[/] "
                        f"[dim]({entry})[/]"
                    )
                else:
                    console.print(
                        f"{get_icon('pull')} [bold]Pulled changes[/] "
                        f"[dim]({entry})[/]"
                    )

                if progress and task_id:
                    progress.update(task_id, advance=1)
                return True

            # Non-mute path: we’ll keep using status_table later
            # (define it once higher up in the function, NOT again later)
            status_table.add_row(
                (
                    get_icon("info")
                    if (
                        "Already up to date" in pull_stdout
                        or "Already up to date" in pull_stderr
                        or pull_stdout == ""
                    )
                    else get_icon("pull")
                ),
                "No new changes" if is_clean else "Pulled changes",
                (
                    "Repository is already up to date"
                    if is_clean
                    else (pull_stdout if pull_stdout else pull_stderr)
                ),
            )

        # For status-only mode with clean repos, show minimal info
        if minimize_clean and is_clean:
            console.print(
                f"[dim]{get_icon('check')} {entry:<40} [green]✓ Clean[/green] [dim cyan]({current_branch})[/dim cyan][/dim]"
            )
            if progress and task_id:
                progress.update(task_id, advance=1)
            return True

        # Full panel for repos with changes or when doing actual work
        repo_panel = Panel(
            f"[bold cyan]{get_icon('project')} {entry}[/]",
            border_style="yellow" if not is_clean else "blue",
            title=f"[bold]Repository[/]",
            title_align="left",
            subtitle=f"[dim]{entry_path}[/]",
            subtitle_align="right",
        )
        console.print(repo_panel)

        start_time = time.time()

        if progress and task_id:
            progress.update(task_id, description=f"[cyan]Processing {entry}[/]")

        # Branch info (already fetched above)
        branch_style = "magenta" if current_branch in ["main", "master"] else "yellow"

        branch_icon = (
            get_icon("main_branch")
            if current_branch in ["main", "master"]
            else get_icon("branch")
        )

        console.print(
            f"{branch_icon} On branch: [bold {branch_style}]{current_branch}[/]"
        )

        # Show current status
        if is_clean:
            console.print(f"[dim]{get_icon('info')} No changes in repository[/]")
        else:
            changes = status_output.split("\n")
            tree = Tree(f"[bold yellow]{len(changes)} files changed[/]")

            for change in changes:
                if not change.strip():
                    continue

                status_code = change[:2].strip()
                file_path = change[3:].strip()

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

                tree.add(
                    f"[{style}]{get_file_icon(file_path)} {file_path}[/] "
                    f"([bold {style}]{status_text}[/])"
                )

            console.print(tree)

        if args.status_only:
            console.print(
                f"\n[bold cyan]{get_icon('info')} Status-only mode: skipping commit/push[/]"
            )

            end_time = time.time()
            elapsed = end_time - start_time
            console.print(
                f"\n{get_icon('clock')} Processed in [bold cyan]{elapsed:.2f}[/] seconds"
            )

            if progress and task_id:
                progress.update(task_id, advance=1)

            return True

        # Only proceed with commits if NOT in status-only mode
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

        if status_table.row_count > 0:
            console.print(status_table)

        # Only commit if there are changes
        if status_output != "":
            if args.use_ai_commit:
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
                            Panel(
                                result.stderr.strip(), title="Error", border_style="red"
                            )
                        )
            else:
                console.print("[bold blue]Staging changes...[/]")
                git_add_all()

                commit_message = (
                    args.commit_message
                    if args.commit_message != "auto-commit"
                    else generate_commit_message()
                )

                console.print(f"[bold blue]Committing changes: {commit_message}[/]")
                git_commit(commit_message)

                console.print(f"\n[bold green]{get_icon('commit')} Commit Summary[/]")

                show_result = git_show_last_commit()

                commit_panel = Panel(
                    show_result.stdout.strip(),
                    title="[bold green]Commit Details[/]",
                    border_style="green",
                    padding=(1, 2),
                )
                console.print(commit_panel)

                if hasattr(args, "auto_push") and args.auto_push:
                    console.print("[bold blue]Pushing to remote...[/]")
                    push_result = git_push()

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

        end_time = time.time()
        elapsed = end_time - start_time

        console.print(
            f"\n{get_icon('clock')} Processed in [bold cyan]{elapsed:.2f}[/] seconds"
        )

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

        if orig_cwd:
            os.chdir(orig_cwd)

        separator_count = shutil.get_terminal_size().columns // 2
        console.print(f"[dim cyan]{get_icon('separator') * separator_count}[/]")
