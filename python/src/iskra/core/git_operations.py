""""""

import os
import glob
import random
import subprocess


def generate_commit_message():
    """"""
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
    """"""
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
    """"""
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
    """"""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def git_pull():
    """"""
    return subprocess.run(
        ["git", "pull"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )


def git_add_all():
    """"""
    subprocess.run(["git", "add", "."], check=True)


def git_status_porcelain():
    """"""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def git_commit(message):
    """"""
    subprocess.run(["git", "commit", "-a", "-m", message], check=True)


def git_push():
    """"""
    return subprocess.run(
        ["git", "push"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # Combine stderr into stdout
        text=True,
    )


def git_show_last_commit():
    """"""
    return subprocess.run(
        ["git", "show", "--stat", "--oneline", "-1"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
