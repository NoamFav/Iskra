import os
import subprocess
from rich.console import Console
from iskra.core.processing_stats import ProcessingStats
from iskra.output.formatter import RepoResult
from iskra.ui.display import process_repository
from iskra.config import ConfigManager
from iskra.ui.formatting import get_icon


class RepositoryProcessor:
    """Process repositories with the given configuration."""

    def __init__(
        self,
        config_manager: ConfigManager,
        orig_cwd: str,
        console: Console,
    ):
        self.config_manager = config_manager
        self.orig_cwd = orig_cwd
        self.console = console

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
                self.console.print(
                    f"\n[bold cyan]Repository {idx}/{len(git_repos)}:[/]",
                )

            result = self._process_single_repo(
                repo_path, display_name, args, tracked_repos
            )

            results.append(result)
            if result.status == "success":
                stats.success_count += 1

        return results, stats

    def _process_single_repo(
        self,
        repo_path: str,
        display_name: str,
        args,
        tracked_repos: list,
    ) -> RepoResult:
        """Process a single repository."""
        config = self.config_manager.merge_config(repo_path)

        # Skip repos without changes if configured
        if config.skip_repos_without_changes and not self._has_changes(
            repo_path,
        ):
            if not args.quiet and not args.json:
                self.console.print(
                    f"[dim]{get_icon('info')} No changes, skipping[/]",
                )
            return RepoResult(
                path=repo_path,
                name=display_name,
                status="skipped",
            )

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
                self.has_changes = orig.has_changes
                self.behind_remote = orig.behind_remote
                self.ahead_remote = orig.ahead_remote
                self.on_branch = orig.on_branch
                self.dirty = orig.dirty
                self.clean = orig.clean
                self.conflicts = orig.conflicts

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
