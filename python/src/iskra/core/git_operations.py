"""Git operation utilities."""

import os
import glob
import random
import subprocess


def generate_commit_message():
    """
    Generate an AI-like commit message.

    Constructs a commit message by randomly combining a prefix action,
    a target area, and a detail explanation. This creates professional-sounding
    commit messages that follow conventional commit patterns.

    Returns:
        str: A randomly generated commit message in the format:
             "{prefix} {area} {detail}"

    Example:
        >>> generate_commit_message()
        'Optimize performance for enhanced security'
    """
    # Action verbs commonly used in professional commit messages
    prefixes = [
        "Update",
        "Enhance",
        "Fix",
        "Refactor",
        "Improve",
        "Optimize",
        "Add",
        "Remove",
        "Modify",
        "Restructure",
        "Clean up",
    ]

    # Common areas of a codebase that are modified
    areas = [
        "codebase",
        "functionality",
        "structure",
        "design",
        "performance",
        "documentation",
        "configuration",
        "dependencies",
        "features",
        "UI",
    ]

    # Reasoning or context for the change
    details = [
        "for better maintainability",
        "to improve user experience",
        "for compatibility with latest standards",
        "to address technical debt",
        "for enhanced security",
        "to optimize resource usage",
        "based on feedback",
        "following best practices",
    ]

    # Combine random selections from each category
    return f"{random.choice(prefixes)} {random.choice(areas)} {random.choice(details)}"


def handle_gitignore(entry_path):
    """
    Ensure .gitignore includes .DS_Store, returns True if updated.

    Checks if a .gitignore file exists in the specified path and ensures
    it contains an entry for .DS_Store (macOS system file). Creates the
    .gitignore if it doesn't exist, or appends .DS_Store if missing.
    Automatically stages the .gitignore file if modified.

    Args:
        entry_path: The directory path where .gitignore should exist

    Returns:
        bool: True if .gitignore was created or modified, False if no changes needed

    Side Effects:
        - Creates .gitignore file if missing
        - Appends .DS_Store entry if not present
        - Stages modified .gitignore with git add
    """
    gitignore_path = os.path.join(entry_path, ".gitignore")
    gitignore_updated = False

    # Create .gitignore with .DS_Store entry if file doesn't exist
    if not os.path.exists(gitignore_path):
        with open(gitignore_path, "w") as f:
            f.write(".DS_Store\n")
        gitignore_updated = True
    else:
        # Read existing .gitignore content
        with open(gitignore_path, "r") as f:
            lines = f.readlines()

        # Check if .DS_Store is already present (with or without newline)
        if ".DS_Store\n" not in lines and ".DS_Store" not in [
            line.strip() for line in lines
        ]:
            # Append .DS_Store entry if missing
            with open(gitignore_path, "a") as f:
                f.write("\n.DS_Store\n")
            gitignore_updated = True

    # Stage the .gitignore file if it was modified
    if gitignore_updated:
        subprocess.run(["git", "add", ".gitignore"], check=True)

    return gitignore_updated


def remove_ds_store_files():
    """
    Find and remove .DS_Store files, returns count of files removed.

    Recursively searches for all .DS_Store files in the repository,
    removes them from Git's cache, and deletes them from the filesystem.
    Useful for cleaning up macOS system files from version control.

    Returns:
        int: The number of .DS_Store files found and removed

    Note:
        Uses check=False for git rm to avoid errors if files aren't tracked.
        Both git cache removal and filesystem deletion are attempted for each file.
    """
    # Find all .DS_Store files recursively from current directory
    ds_store_files = glob.glob("**/.DS_Store", recursive=True)

    if ds_store_files:
        for file in ds_store_files:
            # Remove from Git index (check=False to ignore if not tracked)
            subprocess.run(["git", "rm", "--cached", file], check=False)
            # Delete from filesystem (check=False to ignore if already deleted)
            subprocess.run(["rm", file], check=False)

    return len(ds_store_files)


def get_current_branch():
    """
    Get the current git branch name.

    Retrieves the name of the currently checked out Git branch using
    git rev-parse. This is a reliable way to determine the active branch.

    Returns:
        str: The name of the current branch (e.g., 'main', 'develop', 'feature/new-ui')

    Raises:
        subprocess.CalledProcessError: If not in a Git repository or Git command fails
    """
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def git_pull():
    """
    Execute git pull and return result.

    Fetches and integrates changes from the remote repository into the
    current branch. Captures both stdout and stderr for result inspection.

    Returns:
        subprocess.CompletedProcess: Object containing return code, stdout, and stderr

    Raises:
        subprocess.CalledProcessError: If git pull fails (e.g., merge conflicts)
    """
    return subprocess.run(
        ["git", "pull"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )


def git_add_all():
    """
    Stage all changes.

    Stages all modified, new, and deleted files in the working directory
    for the next commit. Equivalent to running 'git add .' in the terminal.

    Raises:
        subprocess.CalledProcessError: If git add fails
    """
    subprocess.run(["git", "add", "."], check=True)


def git_status_porcelain():
    """
    Get git status in porcelain format.

    Returns the status of the working tree in a machine-readable format.
    Porcelain format is stable across Git versions and easier to parse
    programmatically than standard git status output.

    Returns:
        str: Git status in porcelain format (empty string if no changes)

    Note:
        Does not raise exception on failure, check result manually if needed.
        Format: Two-character status code followed by filename per line.
    """
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def git_commit(message):
    """
    Commit changes with the given message.

    Creates a commit with all staged changes (using -a flag to automatically
    stage modified/deleted files) and the provided commit message.

    Args:
        message: The commit message to use

    Raises:
        subprocess.CalledProcessError: If commit fails (e.g., nothing to commit)
    """
    subprocess.run(["git", "commit", "-a", "-m", message], check=True)


def git_push():
    """
    Push changes to remote.

    Pushes committed changes from the current branch to the corresponding
    remote branch. Combines stdout and stderr into a single stream for
    unified error/success message handling.

    Returns:
        subprocess.CompletedProcess: Object containing the command result

    Raises:
        subprocess.CalledProcessError: If push fails (e.g., rejected, no upstream)
    """
    return subprocess.run(
        ["git", "push"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # Combine stderr into stdout
        text=True,
    )


def git_show_last_commit():
    """
    Get the last commit details.

    Displays information about the most recent commit including the commit
    hash, author, date, message, and file statistics (lines added/removed).
    Uses --oneline for compact format and --stat for change summary.

    Returns:
        subprocess.CompletedProcess: Object with commit details in stdout

    Raises:
        subprocess.CalledProcessError: If command fails or no commits exist

    Output Format:
        abc1234 Commit message (2 files changed, 15 insertions(+), 3 deletions(-))
    """
    return subprocess.run(
        ["git", "show", "--stat", "--oneline", "-1"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
