""""""

import os
import fnmatch
from .constants import HEAVY_DIRS


def _match_any(path_rel: str, patterns) -> bool:
    """"""
    # Fast path: no patterns means no match possible
    if not patterns:
        return False

    # Normalize path separators to forward slashes
    # Makes patterns portable across Windows/Unix
    norm = path_rel.replace(os.sep, "/")

    # Extract basename (rightmost component)
    # "apps/my-project" → "my-project"
    base = os.path.basename(norm)

    # Extract top-level component (first segment)
    # "apps/my-project" → "apps"
    # "standalone" → "standalone"
    top = norm.split("/", 1)[0] if "/" in norm else norm

    # Test against all patterns
    for pat in patterns:
        # Check all three representations
        # Short-circuit on first match for efficiency
        if (
            fnmatch.fnmatch(norm, pat)  # Full path match
            or fnmatch.fnmatch(base, pat)  # Basename match
            or fnmatch.fnmatch(top, pat)  # Top-level match
        ):
            return True

    # No pattern matched any representation
    return False


def find_git_repos(
    base_dir: str,
    only=None,
    exclude=None,
    max_depth: int = 4,
    followlinks: bool = True,
):
    """"""
    # Expand ~ to user's home directory
    # "~/projects" → "/home/username/projects"
    base_dir = os.path.expanduser(base_dir)

    # Normalize pattern lists to empty lists if None
    # Simplifies later logic (no None checks needed)
    only = list(only or [])
    exclude = list(exclude or [])

    # Storage for discovered repositories
    repos_abs = []  # Absolute paths (final output)
    repos_rel = []  # Relative paths (for filtering)

    # === RECURSIVE DIRECTORY TRAVERSAL ===

    # os.walk yields (root, dirs, files) for each directory
    # - root: Current directory absolute path
    # - dirs: Subdirectory names (modifiable to prune)
    # - files: File names in current directory
    for root, dirs, files in os.walk(base_dir, followlinks=followlinks):
        # Calculate relative path for pattern matching
        rel = os.path.relpath(root, base_dir)

        # Calculate current depth
        # "." = depth 0 (base_dir itself)
        # "apps" = depth 1
        # "apps/project" = depth 2
        depth = 0 if rel == "." else rel.count(os.sep) + 1

        # === PERFORMANCE OPTIMIZATION: PRUNE HEAVY DIRECTORIES ===

        # Remove heavy directories from dirs list IN-PLACE
        # os.walk won't descend into removed directories
        # Heavy dirs: node_modules, .venv, target, build, etc.
        dirs[:] = [d for d in dirs if d not in HEAVY_DIRS]

        # === DEPTH CONTROL ===

        # Stop descending if we've reached max depth
        if depth > max_depth:
            dirs[:] = []  # Clear dirs to stop recursion
            continue

        # === REPOSITORY DETECTION ===

        # Check for .git directory (standard repo) OR .git file (worktree/submodule)
        is_repo = (".git" in dirs) or (".git" in files)

        if is_repo:
            # Repository found!
            repos_abs.append(root)

            # Store relative path for filtering
            # Use basename if at base_dir itself
            repos_rel.append(rel if rel != "." else os.path.basename(root))

            # Don't descend into repository
            # Prevents detecting nested .git in submodules as separate repos
            dirs[:] = []
            continue

    # === FILTERING ===

    filtered = []
    for abs_path, rel_path in zip(repos_abs, repos_rel):
        # Apply 'only' filter (whitelist)
        # If 'only' patterns specified, repo must match at least one
        if only and not _match_any(rel_path, only):
            continue

        # Apply 'exclude' filter (blacklist)
        # If repo matches any exclude pattern, skip it
        if exclude and _match_any(rel_path, exclude):
            continue

        # Repository passed all filters
        filtered.append(abs_path)

    # Return sorted list for consistent, predictable output
    # Alphabetical sorting aids in debugging and log analysis
    return sorted(filtered)


def find_repo_in_subdirs(base_dir, repo_short_name):
    """"""
    # Check directly in base_dir first (common case)
    # Most efficient: single path construction and check
    direct_path = os.path.join(base_dir, repo_short_name)
    if os.path.isdir(direct_path):
        return direct_path

    # Search in immediate subdirectories (one level deep)
    # Handles categorized structures: base_dir/category/repo
    for entry in os.listdir(base_dir):
        subdir_path = os.path.join(base_dir, entry)

        # Only check directories, skip heavy directories
        # Heavy directory check prevents descending into node_modules, etc.
        if os.path.isdir(subdir_path) and entry not in HEAVY_DIRS:
            repo_path = os.path.join(subdir_path, repo_short_name)

            # Check if repository exists in this subdirectory
            if os.path.isdir(repo_path):
                return repo_path

    # Repository not found in base_dir or any immediate subdirectory
    return None
