from __future__ import annotations

import subprocess
from typing import List, Any


def _git(repo_path: str, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a git command in repo_path and return the CompletedProcess."""
    return subprocess.run(
        ["git", *args],
        cwd=repo_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


class RepoFilter:
    @staticmethod
    def has_changes(repo_path: str) -> bool:
        """True if there are any tracked or untracked changes."""
        proc = _git(repo_path, "status", "--porcelain")
        return bool(proc.stdout.strip())

    @staticmethod
    def behind_remote(repo_path: str) -> bool:
        """
        True if the current branch is behind its upstream.
        Uses the short status line: '## main...origin/main [behind 1]'.
        """
        proc = _git(repo_path, "status", "-sb")
        if not proc.stdout:
            return False
        first = proc.stdout.splitlines()[0]
        return "behind" in first

    @staticmethod
    def ahead_remote(repo_path: str) -> bool:
        """True if the current branch is ahead of its upstream."""
        proc = _git(repo_path, "status", "-sb")
        if not proc.stdout:
            return False
        first = proc.stdout.splitlines()[0]
        return "ahead" in first

    @staticmethod
    def on_branch(repo_path: str, pattern: str) -> bool:
        """
        True if current branch name contains `pattern`.
        You can pass 'main', 'feature/', 'release', etc.
        """
        proc = _git(repo_path, "rev-parse", "--abbrev-ref", "HEAD")
        branch = proc.stdout.strip()
        return pattern in branch

    @staticmethod
    def is_dirty(repo_path: str) -> bool:
        """Alias for has_changes, kept for semantics."""
        return RepoFilter.has_changes(repo_path)

    @staticmethod
    def is_clean(repo_path: str) -> bool:
        """True if working tree is clean (no changes, no untracked)."""
        return not RepoFilter.has_changes(repo_path)

    @staticmethod
    def has_conflicts(repo_path: str) -> bool:
        """True if there are merge conflicts (unmerged entries)."""
        proc = _git(repo_path, "diff", "--name-only", "--diff-filter=U")
        return bool(proc.stdout.strip())

    @classmethod
    def apply_filters(cls, repos: List[str], **filters: Any) -> List[str]:
        """
        Apply filters to a list of repo paths.

        Supported keys in **filters:
          - is_clean: bool
          - is_dirty: bool
          - has_changes: bool
          - ahead_remote: bool
          - behind_remote: bool
          - has_conflicts: bool
          - on_branch: str (pattern to match in branch name)

        Only truthy / non-None filters are applied.
        """
        result: List[str] = []

        for repo in repos:
            ok = True

            for name, value in filters.items():
                if value is None or value is False:
                    # ignore disabled filters
                    continue

                if name == "on_branch":
                    patterns = (
                        value
                        if isinstance(
                            value,
                            (
                                list,
                                tuple,
                            ),
                        )
                        else [str(value)]
                    )
                    if not any(cls.on_branch(repo, p) for p in patterns):
                        ok = False
                        break
                else:
                    # all other filters are bool predicates with (repo_path)
                    predicate = getattr(cls, name, None)
                    if predicate is None:
                        continue  # unknown filter name -> ignore silently
                    if not predicate(repo):
                        ok = False
                        break

            if ok:
                result.append(repo)

        return result
