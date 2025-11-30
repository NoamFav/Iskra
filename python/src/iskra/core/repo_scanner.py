"""Repository scanning and discovery utilities."""

import os
import fnmatch
from .constants import HEAVY_DIRS


def _match_any(path_rel: str, patterns) -> bool:
    """Match against full relative path, repo basename, and top component (bucket)."""
    if not patterns:
        return False
    norm = path_rel.replace(os.sep, "/")
    base = os.path.basename(norm)
    top = norm.split("/", 1)[0] if "/" in norm else norm
    for pat in patterns:
        if (
            fnmatch.fnmatch(norm, pat)
            or fnmatch.fnmatch(base, pat)
            or fnmatch.fnmatch(top, pat)
        ):
            return True
    return False


def find_git_repos(
    base_dir: str,
    only=None,
    exclude=None,
    max_depth: int = 4,
    followlinks: bool = True,
):
    """
    Recursively find git repos under base_dir up to max_depth.

    Detects repos if either:
      - a '.git' **directory** exists, OR
      - a '.git' **file** exists (worktrees / linked gitdir)

    Filters with glob patterns:
      --only PAT ...   (keep if any pattern matches)
      --exclude PAT ... (drop if any pattern matches)
    Patterns are matched against:
      - relative path from base_dir (e.g. '00-apps/Zvezda' or 'zsh')
      - repo basename (e.g. 'Zvezda', 'zsh')
      - top component (bucket) when present (e.g. '00-apps')
    """
    base_dir = os.path.expanduser(base_dir)
    only = list(only or [])
    exclude = list(exclude or [])

    repos_abs = []
    repos_rel = []

    for root, dirs, files in os.walk(base_dir, followlinks=followlinks):
        rel = os.path.relpath(root, base_dir)
        depth = 0 if rel == "." else rel.count(os.sep) + 1

        # prune heavy dirs
        dirs[:] = [d for d in dirs if d not in HEAVY_DIRS]

        # respect max depth
        if depth > max_depth:
            dirs[:] = []
            continue

        # detect repo by .git dir OR .git file
        is_repo = (".git" in dirs) or (".git" in files)
        if is_repo:
            repos_abs.append(root)
            repos_rel.append(rel if rel != "." else os.path.basename(root))
            # don't descend inside a repo
            dirs[:] = []
            continue

    # apply only/exclude
    filtered = []
    for abs_path, rel_path in zip(repos_abs, repos_rel):
        if only and not _match_any(rel_path, only):
            continue
        if exclude and _match_any(rel_path, exclude):
            continue
        filtered.append(abs_path)

    return sorted(filtered)


def find_repo_in_subdirs(base_dir, repo_short_name):
    """
    Search for a repository in base_dir and its subdirectories.
    Returns the path if found, None otherwise.
    """
    # Check directly in base_dir
    direct_path = os.path.join(base_dir, repo_short_name)
    if os.path.isdir(direct_path):
        return direct_path

    # Search in subdirectories (one level deep)
    for entry in os.listdir(base_dir):
        subdir_path = os.path.join(base_dir, entry)
        if os.path.isdir(subdir_path) and entry not in HEAVY_DIRS:
            repo_path = os.path.join(subdir_path, repo_short_name)
            if os.path.isdir(repo_path):
                return repo_path

    return None
