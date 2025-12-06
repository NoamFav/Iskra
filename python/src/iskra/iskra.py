import os
import sys
import subprocess
import argparse
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from iskra.config import ConfigManager, get_config
from iskra.ui.display import process_repository
from iskra.ui.formatting import print_header, get_icon
from iskra.core.repo_scanner import find_git_repos

from iskra.output.formatter import (
    get_formatter,
    OutputPayload,
    RepoResult,
)


console = Console()


def main(argv: list[str] | None = None):
    if argv is None:
        argv = sys.argv[1:]

    if argv:
        cmd = argv[0]

        if cmd == "init":
            from iskra import init as init_cli

            if len(argv) == 1:
                # `iskra init` -> `init` subcommand
                return init_cli.main(["init"])
            else:
                # `iskra init add ...` -> `add ...`
                # `iskra init list`   -> `list`
                # `iskra init remove` -> `remove`
                return init_cli.main(argv[1:])

        if cmd == "scan":
            # `iskra scan` == `iskra --scan --status-only`
            argv = argv[1:] + ["--scan", "--status-only"]

        elif cmd == "pulse":
            # `iskra pulse` == `iskra --pulse`
            argv = argv[1:] + ["--pulse"]

        elif cmd == "commit":
            # `iskra commit` == default behavior
            argv = argv[1:]

        elif cmd == "status":
            argv = argv[1:] + ["--status-only"]

    parser = argparse.ArgumentParser(
        description="Iskra - Intelligent Git automation with configuration management",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("--config", type=str, help="Path to config file")
    parser.add_argument("--profile", type=str, help="Use named profile")

    parser.add_argument("--dir", type=str, help="Base directory (overrides config)")
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Scan for repos instead of using tracked repos",
    )

    parser.add_argument("--pull", action="store_true", help="Pull before commit")
    parser.add_argument(
        "--no-push", action="store_true", help="Don't push after commit"
    )

    parser.add_argument("--commit-message", type=str, default="auto-commit")
    parser.add_argument(
        "--no-ai-commit", action="store_true", help="Don't use AI for commit messages"
    )

    parser.add_argument("--exclude", type=str, nargs="+", default=[])
    parser.add_argument("--only", type=str, nargs="+", default=[])

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without doing it",
    )
    parser.add_argument(
        "--status-only", action="store_true", help="Only show status, don't commit"
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Minimize output for clean repositories (one line per clean repo)",
    )
    parser.add_argument(
        "-y", "--yes", action="store_true", help="Skip all confirmations"
    )
    parser.add_argument(
        "--show-diff", action="store_true", help="Show diff before committing"
    )

    parser.add_argument("--handle-gitignore", action="store_true")
    parser.add_argument("--remove-ds-store", action="store_true")

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON instead of Rich UI.",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress Rich UI and output only JSON.",
    )
    parser.add_argument(
        "--pulse",
        action="store_true",
        help="Do action only on current repo",
    )

    args = parser.parse_args(argv)
    json_mode = bool(getattr(args, "json", False))
    quiet = bool(getattr(args, "quiet", False))
    rich_enabled = not (json_mode or quiet)
    formatter = get_formatter(json_mode=json_mode, quiet=quiet, console=console)

    if args.config:
        config_manager = ConfigManager(args.config)
    else:
        config_manager = get_config()

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

    base_dir = os.path.expanduser(config.base_dir)
    orig_cwd = os.getcwd()

    if rich_enabled:
        print_header("Git Repository Manager")

    if config.dry_run and rich_enabled:
        console.print(
            Panel(
                "[bold yellow]DRY RUN MODE[/]\n"
                "No changes will be made to repositories",
                border_style="yellow",
                title="⚠️  Warning",
            )
        )

    if args.status_only and rich_enabled:
        mode_text = "[bold cyan]STATUS ONLY MODE[/]\n"
        if args.compact:
            mode_text += "Clean repositories will be shown in compact format"
        else:
            mode_text += "Will only display repository status"

        console.print(
            Panel(
                mode_text,
                border_style="cyan",
                title="ℹ️  Info",
            )
        )

    if args.pulse:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            if rich_enabled:
                console.print("[red]iskra --pulse: not inside a git repository[/]")
            payload = OutputPayload(
                success=False,
                operation="status" if args.status_only else "commit",
                repos_total=0,
                repos_success=0,
                repos_failed=0,
                results=[],
                errors=["not_in_git_repo"],
            )
            formatter.emit(payload)
            return

        repo_root = result.stdout.strip()
        git_repos = [(repo_root, os.path.basename(repo_root))]
        tracked_repos = []
    else:
        tracked_repos = config_manager.get_all_repos(active_only=True)

        if args.scan or not tracked_repos:

            if rich_enabled:
                console.print("[bold blue]Scanning for Git repositories...[/]")

            git_repo_paths = find_git_repos(
                base_dir=base_dir,
                only=config.only_patterns,
                exclude=config.exclude_patterns,
                max_depth=config.max_depth,
                followlinks=config.follow_symlinks,
            )

            git_repos = [
                (path, os.path.relpath(path, base_dir)) for path in git_repo_paths
            ]

            if not args.scan and not git_repos:
                if rich_enabled:
                    console.print(
                        f"\n[yellow]{get_icon('warning')} No repositories found[/]"
                    )
                    console.print(f"[dim]Run 'iskra init' to track repositories[/]")

                payload = OutputPayload(
                    success=True,
                    operation="status" if args.status_only else "commit",
                    repos_total=0,
                    repos_success=0,
                    repos_failed=0,
                    results=[],
                    errors=[],
                )
                formatter.emit(payload)
                return
        else:

            if rich_enabled:
                console.print(
                    f"[bold blue]Using {len(tracked_repos)} tracked repositories[/]"
                )

            git_repos = []
            for repo_info in tracked_repos:
                repo_path = repo_info.path
                repo_name = repo_info.name

                if config.only_patterns:
                    from fnmatch import fnmatch

                    if not any(fnmatch(repo_name, pat) for pat in config.only_patterns):
                        continue

                if config.exclude_patterns:
                    from fnmatch import fnmatch

                    if any(fnmatch(repo_name, pat) for pat in config.exclude_patterns):
                        continue

                git_repos.append((repo_path, repo_name))

            if rich_enabled:
                console.print(
                    f"[bold green]Selected {len(git_repos)} repositories after filters[/]"
                )

    if rich_enabled:
        summary_panel = Panel(
            f"{get_icon('folder')} Found [bold green]{len(git_repos)}[/] repositories to process",
            title="Repository Summary",
            border_style="blue",
        )
        console.print(summary_panel)

    if config.require_confirmation and not args.yes:
        if rich_enabled:
            if not Confirm.ask(f"Process {len(git_repos)} repositories?", default=True):
                console.print("[yellow]Cancelled[/]")

                payload = OutputPayload(
                    success=False,
                    operation="status" if args.status_only else "commit",
                    repos_total=len(git_repos),
                    repos_success=0,
                    repos_failed=0,
                    results=[],
                    errors=["cancelled_by_user"],
                )
                formatter.emit(payload)
                return
        else:

            pass

    if rich_enabled:
        if args.compact and args.status_only:
            console.print(
                f"[bold blue]Processing {len(git_repos)} repositories (compact mode)...[/]\n"
            )
        else:
            console.print(
                f"[bold blue]Processing {len(git_repos)} repositories...[/]\n"
            )

    success_count = 0
    clean_count = 0
    dirty_count = 0
    repo_results = []

    for idx, (repo_path, display_name) in enumerate(git_repos, 1):
        if rich_enabled and not args.compact:
            console.print(f"\n[bold cyan]Repository {idx}/{len(git_repos)}:[/]")

        repo_config = config_manager.merge_config(repo_path)

        if config.skip_repos_without_changes:

            os.chdir(repo_path)
            result = subprocess.run(
                ["git", "status", "--porcelain"], capture_output=True, text=True
            )
            if not result.stdout.strip():
                if rich_enabled:
                    console.print(f"[dim]{get_icon('info')} No changes, skipping[/]")
                os.chdir(orig_cwd)

                repo_results.append(
                    RepoResult(
                        path=repo_path,
                        name=display_name,
                        status="skipped",
                    )
                )
                continue

        class RepoArgs:

            def __init__(self, config, args_orig):
                self.pull = config.auto_pull
                self.handle_gitignore = args_orig.handle_gitignore
                self.remove_ds_store = args_orig.remove_ds_store
                self.use_ai_commit = config.use_ai_commit
                self.commit_message = args_orig.commit_message
                self.dry_run = config.dry_run
                self.status_only = args_orig.status_only
                self.compact = getattr(args_orig, "compact", False)
                self.show_diff = config.show_diff
                self.auto_push = config.auto_push

        repo_args = RepoArgs(repo_config, args)

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

            if not args.scan and tracked_repos:
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

        repo_results.append(
            RepoResult(
                path=repo_path,
                name=display_name,
                status="success" if ok else "failed",
            )
        )

    if rich_enabled:
        console.print()

        # Summary table with clean vs dirty breakdown
        if args.status_only and args.compact:
            # Count clean vs dirty repos
            for repo_path, _ in git_repos:
                os.chdir(repo_path)
                status_output = subprocess.run(
                    ["git", "status", "--porcelain"], capture_output=True, text=True
                ).stdout.strip()
                if status_output:
                    dirty_count += 1
                else:
                    clean_count += 1
                os.chdir(orig_cwd)

            summary_table = Table(show_header=False, box=None, padding=(0, 2))
            summary_table.add_column("Label", style="cyan")
            summary_table.add_column("Count", style="bold")

            summary_table.add_row(
                f"{get_icon('check')} Clean repositories:",
                f"[green]{clean_count}[/green]",
            )
            summary_table.add_row(
                f"{get_icon('warning')} Repositories with changes:",
                f"[yellow]{dirty_count}[/yellow]",
            )
            summary_table.add_row(
                f"{get_icon('folder')} Total processed:",
                f"[blue]{len(git_repos)}[/blue]",
            )

            console.print(
                Panel(
                    summary_table,
                    title="Summary",
                    border_style="blue",
                )
            )
        else:
            final_panel = Panel(
                f"{get_icon('sparkles')} [bold]{success_count}/{len(git_repos)}[/] repositories processed successfully {get_icon('sparkles')}",
                border_style="green" if success_count == len(git_repos) else "yellow",
                title="Processing Complete",
                title_align="center",
            )
            console.print(final_panel)

    log_file = config_manager.get_log_file("iskra")

    with open(log_file, "a") as f:

        f.write(f"\n{'='*80}\n")
        f.write(f"Run at: {datetime.now().isoformat()}\n")
        f.write(f"Processed: {success_count}/{len(git_repos)} repositories\n")
        f.write(f"Base dir: {base_dir}\n")
        if config.dry_run:
            f.write("Mode: DRY RUN\n")
        if args.status_only:
            f.write("Mode: STATUS ONLY\n")
        if args.compact:
            f.write("Display: COMPACT\n")
        f.write(f"{'='*80}\n")

    payload = OutputPayload(
        success=(success_count == len(git_repos)),
        operation="status" if args.status_only else "commit",
        repos_total=len(git_repos),
        repos_success=success_count,
        repos_failed=len(git_repos) - success_count,
        results=repo_results,
        errors=[],
    )
    formatter.emit(payload)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:

        console.print("\n[bold red]Operation canceled by user[/]")
    except Exception:

        console.print_exception()
