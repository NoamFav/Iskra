"""
Iskra - the thing that commits your repos so you don't have to.

Look, I got tired of cd-ing into 50 repos and typing git add/commit/push
like some kind of caveman. So here we are.

This is the main entry point. It does the thing. You know the thing.
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime
from typing import Optional, Any, Dict

from rich.console import Console

from iskra.core.processing_stats import ProcessingStats
from iskra.config import ConfigManager, get_config
from iskra.core.repository_processor import RepositoryProcessor
from iskra.core.repository_selector import RepositorySelector
from iskra.core.ui_manager import UIManager
from iskra.core.command_router import CommandRouter
from iskra.ui.formatting import get_icon, style
from iskra.output.formatter import get_formatter, OutputPayload
from iskra.core.filters import RepoFilter


console = Console()


def build_repo_filters(args) -> Dict[str, Any]:
    """Turn CLI flags into filter kwargs. It's just a dict, chill."""
    filters: dict = {}

    if args.has_changes:
        filters["has_changes"] = True

    if args.dirty:
        filters["is_dirty"] = True

    if args.clean:
        filters["is_clean"] = True

    if args.behind_remote:
        filters["behind_remote"] = True

    if args.ahead_remote:
        filters["ahead_remote"] = True

    if args.conflicts:
        filters["has_conflicts"] = True

    if args.on_branch:
        filters["on_branch"] = args.on_branch

    return filters


def create_argument_parser() -> argparse.ArgumentParser:
    """All the flags. So many flags. Why do we need so many flags. Could be the Olympics"""
    parser = argparse.ArgumentParser(
        description="Iskra - "
        + "Intelligent Git automation with configuration management",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # where stuff lives
    parser.add_argument("--config", type=str, help="Path to config file")
    parser.add_argument("--profile", type=str, help="Use named profile")
    parser.add_argument("--dir", type=str, help="Base directory (overrides config)")

    # what to do
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Scan for repos instead of using tracked repos",
    )
    parser.add_argument(
        "--pulse", action="store_true", help="Do action only on current repo"
    )
    parser.add_argument(
        "--status-only", action="store_true", help="Only show status, don't commit"
    )
    parser.add_argument(
        "--pull-only", action="store_true", help="Only do pull and stop directly"
    )

    # git stuff
    parser.add_argument("--pull", action="store_true", help="Pull before commit")
    parser.add_argument(
        "--no-push", action="store_true", help="Don't push after commit"
    )
    parser.add_argument("--commit-message", type=str, default="auto-commit")
    parser.add_argument(
        "--no-ai-commit", action="store_true", help="Don't use AI for commit messages"
    )

    # filtering - because you don't want ALL the repos probably
    parser.add_argument("--exclude", type=str, nargs="+", default=[])
    parser.add_argument("--only", type=str, nargs="+", default=[])
    parser.add_argument(
        "--has-changes", "-c", action="store_true", help="Has uncommitted changes"
    )
    parser.add_argument(
        "--behind-remote", action="store_true", help="Behind remote (needs pull)"
    )
    parser.add_argument(
        "--ahead-remote", action="store_true", help="Ahead remote (needs push)"
    )
    parser.add_argument(
        "--on-branch", type=str, nargs="+", default=[], help="On specific branch"
    )
    parser.add_argument(
        "--dirty", action="store_true", help="Has untracked/modified files"
    )
    parser.add_argument("--clean", action="store_true", help="No changes at all")
    parser.add_argument("--conflicts", action="store_true", help="Has merge conflicts")

    # safety nets for the paranoid (me)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without doing it",
    )
    parser.add_argument(
        "--compact", action="store_true", help="Minimize output for clean repositories"
    )
    parser.add_argument(
        "-y", "--yes", action="store_true", help="Skip all confirmations"
    )
    parser.add_argument(
        "--show-diff", action="store_true", help="Show diff before committing"
    )

    # macos garbage handlers
    parser.add_argument("--handle-gitignore", action="store_true")
    parser.add_argument("--remove-ds-store", action="store_true")

    # output format for the robots
    parser.add_argument(
        "--json", action="store_true", help="Output machine-readable JSON"
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress Rich UI")

    return parser


def apply_config_overrides(config, args) -> None:
    """CLI args beat config file. That's just how it works."""
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


def write_log_entry(
    log_file: str | os.PathLike,
    args,
    stats: ProcessingStats,
    total: int,
    base_dir: str,
) -> None:
    """Scribble what we did into a log file. For posterity or whatever."""
    with open(log_file, "a") as f:
        f.write(f"\n{'='*80}\n")
        f.write(f"Run at: {datetime.now().isoformat()}\n")
        f.write(f"Processed: {stats.success_count}/{total} repositories\n")
        f.write(f"Base dir: {base_dir}\n")

        if args.dry_run:
            f.write("Mode: DRY RUN\n")
        if args.status_only:
            f.write("Mode: STATUS ONLY\n")
        if args.compact:
            f.write("Display: COMPACT\n")

        f.write(f"{'='*80}\n")


def main(argv: Optional[list[str]] = None) -> None:
    """
    The main function. It does everything.
    Parse args, load config, find repos, process them, done.
    This is like 150 lines because I couldn't be bothered to split it up.
    Sue me.
    """
    if argv is None:
        argv = sys.argv[1:]

    # route to subcommands if needed
    argv = CommandRouter.route(argv)

    parser = create_argument_parser()
    args = parser.parse_args(argv)

    # figure out output mode
    json_mode = bool(getattr(args, "json", False))
    quiet = bool(getattr(args, "quiet", False))
    rich_enabled = not (json_mode or quiet)
    formatter = get_formatter(json_mode=json_mode, quiet=quiet, console=console)

    # load the config
    config_manager = get_config() if not args.config else ConfigManager(args.config)
    config = config_manager.global_config
    apply_config_overrides(config, args)

    base_dir = os.path.expanduser(config.base_dir)
    orig_cwd = os.getcwd()

    # pretty UI stuff
    ui = UIManager(rich_enabled, console)
    ui.show_header()
    ui.show_mode_warnings(args)

    # find the repos
    try:
        selector = RepositorySelector(config_manager, config, base_dir)
        git_repos, tracked_repos = selector.get_repositories(args.scan, args.pulse)
    except RuntimeError as e:
        if str(e) == "not_in_git_repo":
            if rich_enabled:
                console.print(style("iskra --pulse: not inside a git repository", "error"))
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
        raise

    # apply filters if any
    repo_filter_kwargs = build_repo_filters(args)
    if repo_filter_kwargs:
        repo_paths = [path for path, _ in git_repos]
        filtered_paths = set(RepoFilter.apply_filters(repo_paths, **repo_filter_kwargs))
        git_repos = [(p, m) for (p, m) in git_repos if p in filtered_paths]

    # nobody home?
    if not git_repos:
        if rich_enabled:
            console.print(f"\n{style(get_icon('warning') + ' No repositories found', 'warning')}")
            if not args.scan:
                console.print(style("Run 'iskra init' to track repositories", "dim"))
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

    # show what we found
    if tracked_repos and rich_enabled:
        ui.show_repository_summary(
            len(git_repos),
            f"Using {len(tracked_repos)} tracked repositories\n"
            f"Selected {len(git_repos)} repositories after filters",
        )
    else:
        ui.show_repository_summary(len(git_repos))

    # you sure about this?
    if config.require_confirmation and not args.yes:
        if not ui.confirm_processing(len(git_repos)):
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

    # ok let's actually do the thing
    if rich_enabled:
        mode = "compact mode" if (args.compact and args.status_only) else ""
        console.print(
            f"{style(f'Processing {len(git_repos)} repositories {mode}...', 'info')}\n"
        )

    processor = RepositoryProcessor(config_manager, orig_cwd, console)
    repo_results, stats = processor.process_all(
        git_repos, args, tracked_repos, rich_enabled
    )

    # compact mode needs these counts
    if args.status_only and args.compact:
        for repo_path, _ in git_repos:
            os.chdir(repo_path)
            status_output = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
            ).stdout.strip()
            if status_output:
                stats.dirty_count += 1
            else:
                stats.clean_count += 1
            os.chdir(orig_cwd)

    # show the results
    ui.show_final_summary(args, stats, len(git_repos))

    # log it
    log_file = config_manager.get_log_file("iskra")
    write_log_entry(log_file, args, stats, len(git_repos), base_dir)

    # emit for json mode
    payload = OutputPayload(
        success=(stats.success_count == len(git_repos)),
        operation="status" if args.status_only else "commit",
        repos_total=len(git_repos),
        repos_success=stats.success_count,
        repos_failed=len(git_repos) - stats.success_count,
        results=repo_results,
        errors=[],
    )
    formatter.emit(payload)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print(f"\n{style('Operation canceled by user', 'error')}")
    except Exception:
        console.print_exception()
