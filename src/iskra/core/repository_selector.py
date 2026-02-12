"""
Repository selector. Picks which repos to process based on mode and filters.
"""

from iskra.config import ConfigManager
import subprocess
import os

from iskra.core.repo_scanner import find_git_repos


class RepositorySelector:
    """Figure out which repos we're working with today."""

    def __init__(self, config_manager: ConfigManager, config, base_dir: str):
        self.config_manager = config_manager
        self.config = config
        self.base_dir = base_dir

    def get_repositories(
        self, scan: bool, pulse: bool
    ) -> tuple[list[tuple[str, str]], list]:
        """Get repos based on mode. Pulse = current, scan = find em, else tracked."""
        if pulse:
            return self._get_pulse_repo(), []

        tracked_repos = self.config_manager.get_all_repos(active_only=True)

        if scan or not tracked_repos:
            return self._scan_repositories(), []

        return self._get_tracked_repositories(tracked_repos), tracked_repos

    def _get_pulse_repo(self) -> list[tuple[str, str]]:
        """Just the repo we're standing in. Pulse mode."""
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
        """Walk the base dir and find all the repos."""
        git_repo_paths = find_git_repos(
            base_dir=self.base_dir,
            only=self.config.only_patterns,
            exclude=self.config.exclude_patterns,
            max_depth=self.config.max_depth,
            followlinks=self.config.follow_symlinks,
        )
        return [
            (
                path,
                os.path.relpath(
                    path,
                    self.base_dir,
                ),
            )
            for path in git_repo_paths
        ]

    def _get_tracked_repositories(
        self,
        tracked_repos,
    ) -> list[
        tuple[
            str,
            str,
        ]
    ]:
        """Get tracked repos, filtered by include/exclude patterns."""
        git_repos = []

        for repo_info in tracked_repos:
            if self._should_include_repo(repo_info.name):
                git_repos.append((repo_info.path, repo_info.name))

        return git_repos

    def _should_include_repo(self, repo_name: str) -> bool:
        """Does this repo pass the only/exclude filters?"""
        from fnmatch import fnmatch

        if self.config.only_patterns:
            if not any(
                fnmatch(
                    repo_name,
                    pat,
                )
                for pat in self.config.only_patterns
            ):
                return False

        if self.config.exclude_patterns:
            if any(
                fnmatch(
                    repo_name,
                    pat,
                )
                for pat in self.config.exclude_patterns
            ):
                return False

        return True
