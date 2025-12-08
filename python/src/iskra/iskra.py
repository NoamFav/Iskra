import os
import sys
import subprocess
import argparse
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from iskra.config import ConfigManager, get_config
from iskra.ui.display import process_repository
from iskra.ui.formatting import print_header, get_icon
from iskra.core.repo_scanner import find_git_repos
from iskra.output.formatter import get_formatter, OutputPayload, RepoResult


console = Console()


@dataclass
class ProcessingStats:
    """Track repository processing statistics."""

    success_count: int = 0
    clean_count: int = 0
    dirty_count: int = 0


class CommandRouter:
    """Route and transform command-line arguments."""

    COMMAND_MAPPINGS = {
        "scan": ["--scan", "--status-only"],
        "pulse": ["--pulse"],
        "status": ["--status-only"],
        "sync": ["--pull", "--pull-only", "--pulse", "-y"],
        "sync-all": ["--pull", "--pull-only", "-y"],
    }

    @classmethod
    def route(cls, argv: list[str]) -> list[str]:
        """Transform command shortcuts into full argument lists."""
        if not argv:
            return argv

        cmd = argv[0]

        # Handle init subcommands separately
        if cmd == "init":
            from iskra import init as init_cli

            subcmd = ["init"] if len(argv) == 1 else argv[1:]
            sys.exit(init_cli.main(subcmd))
        if cmd == "clone":
            from iskra import clone_repos as clone_cli

            sys.exit(clone_cli.main(argv[1:]))
        if cmd == "gh":
            from iskra import gh as gh_cli

            sys.exit(gh_cli.main(argv[1:]))
        # Handle commit command (default behavior)
        if cmd == "commit":
            return argv[1:]

        # Map other commands
        if cmd in cls.COMMAND_MAPPINGS:
            return argv[1:] + cls.COMMAND_MAPPINGS[cmd]

        return argv


class RepositorySelector:
    """Select and filter repositories based on configuration."""

    def __init__(self, config_manager: ConfigManager, config, base_dir: str):
        self.config_manager = config_manager
        self.config = config
        self.base_dir = base_dir

    def get_repositories(
        self, scan: bool, pulse: bool
    ) -> tuple[list[tuple[str, str]], list]:
        """Get repositories to process based on mode."""
        if pulse:
            return self._get_pulse_repo(), []

        tracked_repos = self.config_manager.get_all_repos(active_only=True)

        if scan or not tracked_repos:
            return self._scan_repositories(), []

        return self._get_tracked_repositories(tracked_repos), tracked_repos

    def _get_pulse_repo(self) -> list[tuple[str, str]]:
        """Get the current repository for pulse mode."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError("not_in_git_repo")

        repo_root = result.stdout.strip()
        return [(repo_root, os.path.basename(repo_root))]

    def _scan_repositories(self) -> list[tuple[str, str]]:
        """Scan for repositories in the base directory."""
        git_repo_paths = find_git_repos(
            base_dir=self.base_dir,
            only=self.config.only_patterns,
            exclude=self.config.exclude_patterns,
            max_depth=self.config.max_depth,
            followlinks=self.config.follow_symlinks,
        )
        return [(path, os.path.relpath(path, self.base_dir)) for path in git_repo_paths]

    def _get_tracked_repositories(self, tracked_repos) -> list[tuple[str, str]]:
        """Get tracked repositories with filtering applied."""
        git_repos = []

        for repo_info in tracked_repos:
            if self._should_include_repo(repo_info.name):
                git_repos.append((repo_info.path, repo_info.name))

        return git_repos

    def _should_include_repo(self, repo_name: str) -> bool:
        """Check if repository passes include/exclude filters."""
        from fnmatch import fnmatch

        if self.config.only_patterns:
            if not any(fnmatch(repo_name, pat) for pat in self.config.only_patterns):
                return False

        if self.config.exclude_patterns:
            if any(fnmatch(repo_name, pat) for pat in self.config.exclude_patterns):
                return False

        return True


class RepositoryProcessor:
    """Process repositories with the given configuration."""

    def __init__(self, config_manager: ConfigManager, orig_cwd: str):
        self.config_manager = config_manager
        self.orig_cwd = orig_cwd

    def process_all(
        self,
        git_repos: list[tuple[str, str]],
        args,
        tracked_repos: list,
        rich_enabled: bool,
    ) -> tuple[list[RepoResult], ProcessingStats]:
        """Process all repositories and return results."""
        results = []
        stats = ProcessingStats()

        for idx, (repo_path, display_name) in enumerate(git_repos, 1):
            if rich_enabled and not args.compact:
                console.print(f"\n[bold cyan]Repository {idx}/{len(git_repos)}:[/]")

            result = self._process_single_repo(
                repo_path, display_name, args, tracked_repos
            )

            results.append(result)
            if result.status == "success":
                stats.success_count += 1

        return results, stats

    def _process_single_repo(
        self, repo_path: str, display_name: str, args, tracked_repos: list
    ) -> RepoResult:
        """Process a single repository."""
        config = self.config_manager.merge_config(repo_path)

        # Skip repos without changes if configured
        if config.skip_repos_without_changes and not self._has_changes(repo_path):
            if not args.quiet and not args.json:
                console.print(f"[dim]{get_icon('info')} No changes, skipping[/]")
            return RepoResult(path=repo_path, name=display_name, status="skipped")

        # Create repository-specific args
        repo_args = self._create_repo_args(config, args)

        # Process the repository
        success = process_repository(
            entry_path=repo_path,
            entry=display_name,
            args=repo_args,
            task_id=None,
            progress=None,
            orig_cwd=self.orig_cwd,
        )

        # Update tracked repo if successful
        if success and tracked_repos:
            self._update_tracked_repo(repo_path)

        return RepoResult(
            path=repo_path,
            name=display_name,
            status="success" if success else "failed",
        )

    def _has_changes(self, repo_path: str) -> bool:
        """Check if repository has uncommitted changes."""
        os.chdir(repo_path)
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
        )
        os.chdir(self.orig_cwd)
        return bool(result.stdout.strip())

    def _create_repo_args(self, config, args_orig):
        """Create repository-specific arguments."""

        class RepoArgs:
            def __init__(self, cfg, orig):
                self.pull = cfg.auto_pull
                self.handle_gitignore = orig.handle_gitignore
                self.remove_ds_store = orig.remove_ds_store
                self.use_ai_commit = cfg.use_ai_commit
                self.commit_message = orig.commit_message
                self.dry_run = cfg.dry_run
                self.status_only = orig.status_only
                self.compact = getattr(orig, "compact", False)
                self.show_diff = cfg.show_diff
                self.auto_push = cfg.auto_push
                self.pull_only = orig.pull_only

        return RepoArgs(config, args_orig)

    def _update_tracked_repo(self, repo_path: str):
        """Update tracked repository's last commit hash."""
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=repo_path,
        )
        if result.returncode == 0:
            self.config_manager.update_repo(
                repo_path, last_commit=result.stdout.strip()
            )


class UIManager:
    """Manage user interface output and interaction."""

    def __init__(self, rich_enabled: bool):
        self.rich_enabled = rich_enabled

    def show_header(self):
        """Display application header."""
        if self.rich_enabled:
            print_header("Git Repository Manager")

    def show_mode_warnings(self, args):
        """Display mode warnings and information."""
        if not self.rich_enabled:
            return

        if args.dry_run:
            console.print(
                "[dim yellow]⚠[/]  [yellow]dry run mode[/] [dim]— no changes will be made[/]\n"
            )

        if args.status_only:
            mode_text = "[dim cyan]ℹ[/]  [cyan]status only mode[/]"
            if args.compact:
                mode_text += " [dim]— compact display for clean repos[/]"
            console.print(f"{mode_text}\n")

    def show_repository_summary(self, repo_count: int, message: str = ""):
        """Display repository count summary."""
        if not self.rich_enabled:
            return

        if message:
            console.print(f"[dim]{message}[/]\n")

        console.print(f"[white]Found[/] [bold]{repo_count}[/] [white]repositories[/]\n")

    def confirm_processing(self, repo_count: int) -> bool:
        """Ask user to confirm processing."""
        if not self.rich_enabled:
            return True

        from rich.prompt import Confirm

        if not Confirm.ask(f"Process {repo_count} repositories?", default=True):
            console.print("[dim yellow]cancelled[/]")
            return False

        return True

    def show_final_summary(self, args, stats, total: int):
        """Display final processing summary."""
        if not self.rich_enabled:
            return

        console.print()

        if args.status_only and args.compact:
            self._show_compact_summary(stats, total)
        else:
            self._show_standard_summary(stats.success_count, total)

    def _show_compact_summary(self, stats, total: int):
        """Show compact summary with clean/dirty breakdown."""
        console.print(f"[dim]Summary:[/]")
        console.print(f"  [green]✓[/] [dim]clean:[/] [green]{stats.clean_count}[/]")
        console.print(
            f"  [yellow]●[/] [dim]with changes:[/] [yellow]{stats.dirty_count}[/]"
        )
        console.print(f"  [dim]total:[/] [white]{total}[/]")
        console.print()

    def _show_standard_summary(self, success_count: int, total: int):
        """Show standard success summary."""
        all_success = success_count == total
        status = "✓" if all_success else "◆"
        color = "green" if all_success else "yellow"

        console.print(
            f"[{color}]{status}[/] "
            f"[white]Processed[/] [bold]{success_count}/{total}[/] "
            f"[dim]repositories[/]"
        )
        console.print()


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Iskra - Intelligent Git automation with configuration management",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Configuration
    parser.add_argument("--config", type=str, help="Path to config file")
    parser.add_argument("--profile", type=str, help="Use named profile")
    parser.add_argument("--dir", type=str, help="Base directory (overrides config)")

    # Operation modes
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

    # Git operations
    parser.add_argument("--pull", action="store_true", help="Pull before commit")
    parser.add_argument(
        "--no-push", action="store_true", help="Don't push after commit"
    )
    parser.add_argument("--commit-message", type=str, default="auto-commit")
    parser.add_argument(
        "--no-ai-commit", action="store_true", help="Don't use AI for commit messages"
    )

    # Filtering
    parser.add_argument("--exclude", type=str, nargs="+", default=[])
    parser.add_argument("--only", type=str, nargs="+", default=[])

    # Behavior
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

    # File handling
    parser.add_argument("--handle-gitignore", action="store_true")
    parser.add_argument("--remove-ds-store", action="store_true")

    # Output format
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON instead of Rich UI",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress Rich UI and output only JSON",
    )

    return parser


def apply_config_overrides(config, args):
    """Apply command-line argument overrides to configuration."""
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
    log_file: str | os.PathLike, args, stats: ProcessingStats, total: int, base_dir: str
):
    """Write processing log entry."""
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


def main(argv: Optional[list[str]] = None):
    """Main entry point for the Iskra application."""
    if argv is None:
        argv = sys.argv[1:]

    # Route commands
    argv = CommandRouter.route(argv)

    # Parse arguments
    parser = create_argument_parser()
    args = parser.parse_args(argv)

    # Setup output formatting
    json_mode = bool(getattr(args, "json", False))
    quiet = bool(getattr(args, "quiet", False))
    rich_enabled = not (json_mode or quiet)
    formatter = get_formatter(json_mode=json_mode, quiet=quiet, console=console)

    # Load configuration
    config_manager = get_config() if not args.config else ConfigManager(args.config)
    config = config_manager.global_config
    apply_config_overrides(config, args)

    base_dir = os.path.expanduser(config.base_dir)
    orig_cwd = os.getcwd()

    # Initialize UI
    ui = UIManager(rich_enabled)
    ui.show_header()
    ui.show_mode_warnings(args)

    # Select repositories
    try:
        selector = RepositorySelector(config_manager, config, base_dir)
        git_repos, tracked_repos = selector.get_repositories(args.scan, args.pulse)
    except RuntimeError as e:
        if str(e) == "not_in_git_repo":
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
        raise

    # Handle empty repository list
    if not git_repos:
        if rich_enabled:
            console.print(f"\n[yellow]{get_icon('warning')} No repositories found[/]")
            if not args.scan:
                console.print("[dim]Run 'iskra init' to track repositories[/]")

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

    # Show repository summary
    if tracked_repos and rich_enabled:
        ui.show_repository_summary(
            len(git_repos),
            f"Using {len(tracked_repos)} tracked repositories\n"
            f"Selected {len(git_repos)} repositories after filters",
        )
    else:
        ui.show_repository_summary(len(git_repos))

    # Confirm processing
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

    # Process repositories
    if rich_enabled:
        mode = "compact mode" if (args.compact and args.status_only) else ""
        console.print(
            f"[bold blue]Processing {len(git_repos)} repositories {mode}...[/]\n"
        )

    processor = RepositoryProcessor(config_manager, orig_cwd)
    repo_results, stats = processor.process_all(
        git_repos, args, tracked_repos, rich_enabled
    )

    # Calculate clean/dirty counts for compact mode
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

    # Show final summary
    ui.show_final_summary(args, stats, len(git_repos))

    # Write log
    log_file = config_manager.get_log_file("iskra")
    write_log_entry(log_file, args, stats, len(git_repos), base_dir)

    # Emit final payload
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
        console.print("\n[bold red]Operation canceled by user[/]")
    except Exception:
        console.print_exception()
