"""
Git operations. All the subprocess.run calls live here.

Pull, push, commit, stash, diff, the whole gang.
Also handles .DS_Store (fuck you macos) and conflict detection.
"""

import os
import glob
import random
import subprocess


def generate_commit_message() -> str:
    """
    Random commit message generator. For when AI fails you.
    Yeah this is cursed but sometimes you just need SOMETHING.
    """
    prefixes = [
        "Update", "Enhance", "Fix", "Refactor", "Improve",
        "Optimize", "Add", "Remove", "Modify", "Restructure", "Clean up",
    ]
    areas = [
        "codebase", "functionality", "structure", "design",
        "performance", "documentation", "configuration",
        "dependencies", "features", "UI",
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


def handle_gitignore(entry_path: str) -> bool:
    """Add .DS_Store to .gitignore if missing. Returns True if modified."""
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


def remove_ds_store_files() -> int:
    """Nuke all .DS_Store files. Returns count removed."""
    ds_store_files = glob.glob("**/.DS_Store", recursive=True)

    if ds_store_files:
        for file in ds_store_files:
            subprocess.run(["git", "rm", "--cached", file], check=False)
            subprocess.run(["rm", file], check=False)

    return len(ds_store_files)


def get_current_branch() -> str:
    """What branch we on?"""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def git_pull() -> subprocess.CompletedProcess:
    """git pull. That's it."""
    return subprocess.run(
        ["git", "pull"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )


def git_add_all() -> None:
    """Stage everything. git add ."""
    subprocess.run(["git", "add", "."], check=True)


def git_status_porcelain() -> str:
    """Get status in machine-readable format. Empty = clean repo."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def git_commit(message: str) -> None:
    """Commit with message. Uses -a so stages tracked files too."""
    subprocess.run(["git", "commit", "-a", "-m", message], check=True)


def git_push() -> subprocess.CompletedProcess:
    """Push it real good."""
    return subprocess.run(
        ["git", "push"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def git_show_last_commit() -> subprocess.CompletedProcess:
    """Show the last commit. One liner + stats."""
    return subprocess.run(
        ["git", "show", "--stat", "--oneline", "-1"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def git_diff(staged: bool = False) -> str:
    """Get diff stats. Pass staged=True for cached."""
    cmd = ["git", "diff", "--stat"]
    if staged:
        cmd.append("--cached")
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def git_diff_full(staged: bool = False) -> str:
    """Full diff with actual changes. Can be huge."""
    cmd = ["git", "diff"]
    if staged:
        cmd.append("--cached")
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def git_stash() -> bool:
    """Stash changes. Returns True if actually stashed something."""
    result = subprocess.run(
        ["git", "stash", "push", "-m", "iskra-auto-stash"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return "No local changes" not in result.stdout


def git_stash_pop() -> bool:
    """Pop the stash. Returns True if it worked."""
    result = subprocess.run(
        ["git", "stash", "pop"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.returncode == 0


def check_for_conflicts() -> list[str]:
    """Check for merge conflicts. Returns list of conflicted files."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=U"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    files = result.stdout.strip()
    if files:
        return files.split("\n")
    return []


def check_would_conflict_on_pull() -> bool:
    """
    Dry-run to see if pull would cause conflicts. Cleans up after itself.
    This is some galaxy brain shit right here - fake merge then abort.
    """
    subprocess.run(
        ["git", "fetch"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    result = subprocess.run(
        ["git", "merge", "--no-commit", "--no-ff", "FETCH_HEAD"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    subprocess.run(
        ["git", "merge", "--abort"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    return "CONFLICT" in result.stdout or "CONFLICT" in result.stderr


def get_remote_url() -> str:
    """Get the remote origin URL."""
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def is_ssh_remote() -> bool:
    """Is the remote using SSH? (git@ or ssh://)"""
    url = get_remote_url()
    return url.startswith("git@") or url.startswith("ssh://")


def check_ssh_agent_has_keys() -> bool:
    """Check if ssh-agent has keys loaded."""
    result = subprocess.run(
        ["ssh-add", "-l"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.returncode == 0


def is_protected_branch(branch: str, protected_branches: list[str]) -> bool:
    """Is this branch protected? Simple list check."""
    return branch in protected_branches


def run_hook_command(command: str, cwd: str = None) -> tuple[int, str, str]:
    """Run a hook command. Returns (returncode, stdout, stderr)."""
    result = subprocess.run(
        command,
        shell=True,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def generate_smart_commit_message(status_output: str) -> str:
    """
    Generate commit message based on what changed.
    Detects tests, docs, config, deps, etc.
    Fallback when AI is unavailable.

    Look at all these if statements. This is what happens when you
    don't want to pay for API calls.
    """
    if not status_output:
        return "chore: update files"

    changes = [c for c in status_output.split("\n") if c.strip()]
    files = [c[3:].strip() for c in changes]

    # what kind of files?
    has_tests = any("test" in f.lower() for f in files)
    has_docs = any(
        f.endswith((".md", ".rst", ".txt")) or "doc" in f.lower() for f in files
    )
    has_config = any(
        f.endswith((".json", ".yaml", ".yml", ".toml", ".ini", ".cfg")) for f in files
    )
    has_deps = any(
        f in ("package.json", "requirements.txt", "go.mod", "Cargo.toml", "pom.xml")
        for f in files
    )

    # count ops
    added = sum(1 for c in changes if c.startswith("A") or c.startswith("??"))
    modified = sum(1 for c in changes if c.startswith("M"))
    deleted = sum(1 for c in changes if c.startswith("D"))

    # figure out what to say
    if has_deps:
        return "chore: update dependencies"
    elif has_tests:
        if added > modified:
            return "test: add tests"
        return "test: update tests"
    elif has_docs:
        return "docs: update documentation"
    elif has_config:
        return "chore: update configuration"
    elif deleted > added and deleted > modified:
        return f"chore: remove {deleted} file{'s' if deleted > 1 else ''}"
    elif added > modified:
        if len(files) == 1:
            return f"feat: add {os.path.basename(files[0])}"
        return f"feat: add {added} new file{'s' if added > 1 else ''}"
    else:
        if len(files) == 1:
            return f"chore: update {os.path.basename(files[0])}"
        return f"chore: update {len(files)} file{'s' if len(files) > 1 else ''}"
