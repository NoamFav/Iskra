"""Git operation utilities."""

import os
import glob
import random
import subprocess


def generate_commit_message():
    """Generate an AI-like commit message."""
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

    return f"{random.choice(prefixes)} {random.choice(areas)} {random.choice(details)}"


def handle_gitignore(entry_path):
    """Ensure .gitignore includes .DS_Store, returns True if updated."""
    gitignore_path = os.path.join(entry_path, ".gitignore")
    gitignore_updated = False

    if not os.path.exists(gitignore_path):
        with open(gitignore_path, "w") as f:
            f.write(".DS_Store\n")
        gitignore_updated = True
    else:
        with open(gitignore_path, "r") as f:
            lines = f.readlines()
        if ".DS_Store\n" not in lines and ".DS_Store" not in [
            line.strip() for line in lines
        ]:
            with open(gitignore_path, "a") as f:
                f.write("\n.DS_Store\n")
            gitignore_updated = True

    if gitignore_updated:
        subprocess.run(["git", "add", ".gitignore"], check=True)

    return gitignore_updated


def remove_ds_store_files():
    """Find and remove .DS_Store files, returns count of files removed."""
    ds_store_files = glob.glob("**/.DS_Store", recursive=True)

    if ds_store_files:
        for file in ds_store_files:
            subprocess.run(["git", "rm", "--cached", file], check=False)
            subprocess.run(["rm", file], check=False)

    return len(ds_store_files)


def get_current_branch():
    """Get the current git branch name."""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def git_pull():
    """Execute git pull and return result."""
    return subprocess.run(
        ["git", "pull"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )


def git_add_all():
    """Stage all changes."""
    subprocess.run(["git", "add", "."], check=True)


def git_status_porcelain():
    """Get git status in porcelain format."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def git_commit(message):
    """Commit changes with the given message."""
    subprocess.run(["git", "commit", "-a", "-m", message], check=True)


def git_push():
    """Push changes to remote."""
    return subprocess.run(
        ["git", "push"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def git_show_last_commit():
    """Get the last commit details."""
    return subprocess.run(
        ["git", "show", "--stat", "--oneline", "-1"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
