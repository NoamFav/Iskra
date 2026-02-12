"""
Repo filters. For when you have 50 repos but only want the dirty ones.

has_changes, behind_remote, on_branch, all that jazz.
Basically WHERE clauses for your git repos.
"""

from __future__ import annotations

import subprocess
from typing import List, Any


def _git(repo_path: str, *args: str) -> subprocess.CompletedProcess[str]:
    """Run git in a repo. Returns the result whether it worked or not."""
    return subprocess.run(
        ["git", *args],
        cwd=repo_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


class RepoFilter:
    """Filter repos by various git states. Like a bouncer for your repos."""

    @staticmethod
    def has_changes(repo_path: str) -> bool:
        """Got uncommitted stuff? Let's find out."""
        proc = _git(repo_path, "status", "--porcelain")
        return bool(proc.stdout.strip())

    @staticmethod
    def behind_remote(repo_path: str) -> bool:
        """Are we behind? Did someone push while we were slacking?"""
        proc = _git(repo_path, "status", "-sb")
        if not proc.stdout:
            return False
        first = proc.stdout.splitlines()[0]
        return "behind" in first

    @staticmethod
    def ahead_remote(repo_path: str) -> bool:
        """Did we forget to push? Classic."""
        proc = _git(repo_path, "status", "-sb")
        if not proc.stdout:
            return False
        first = proc.stdout.splitlines()[0]
        return "ahead" in first

    @staticmethod
    def on_branch(repo_path: str, pattern: str) -> bool:
        """Check if branch name contains the pattern. Simple string match."""
        proc = _git(repo_path, "rev-parse", "--abbrev-ref", "HEAD")
        branch = proc.stdout.strip()
        return pattern in branch

    @staticmethod
    def is_dirty(repo_path: str) -> bool:
        """Same as has_changes. Two names, one function. Deal with it."""
        return RepoFilter.has_changes(repo_path)

    @staticmethod
    def is_clean(repo_path: str) -> bool:
        """Nothing to commit, nothing to worry about."""
        return not RepoFilter.has_changes(repo_path)

    @staticmethod
    def has_conflicts(repo_path: str) -> bool:
        """Oh no, merge conflicts. Everyone's favorite."""
        proc = _git(repo_path, "diff", "--name-only", "--diff-filter=U")
        return bool(proc.stdout.strip())

    @classmethod
    def apply_filters(cls, repos: List[str], **filters: Any) -> List[str]:
        """
        Run all the filter checks on repos. Only the worthy survive.
        Pass is_dirty=True, behind_remote=True, on_branch='main', whatever.
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
