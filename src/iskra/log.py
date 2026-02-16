"""
iskra log - git history for the current repo.

Like lazygit's log view but in your terminal without all the TUI nonsense.
Shows commits with hashes, messages, authors, dates. Pretty and fast.
"""

import os
import subprocess
import argparse
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.panel import Panel

from iskra.ui.formatting import style, get_color


console = Console()


def create_argument_parser() -> argparse.ArgumentParser:
    """Flags for log command."""
    parser = argparse.ArgumentParser(
        description="Show git history for current repository",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  iskra log
  iskra log -n 50
  iskra log --oneline
  iskra log --author "noam"
  iskra log --since "2 weeks ago"
        """,
    )

    parser.add_argument(
        "-n", "--count", type=int, default=20,
        help="Number of commits to show (default: 20)",
    )
    parser.add_argument(
        "--oneline", action="store_true",
        help="Compact one-line format",
    )
    parser.add_argument(
        "--author", type=str,
        help="Filter by author name/email",
    )
    parser.add_argument(
        "--since", type=str,
        help="Show commits after date (e.g. '2 weeks ago', '2024-01-01')",
    )
    parser.add_argument(
        "--until", type=str,
        help="Show commits before date",
    )
    parser.add_argument(
        "--grep", type=str,
        help="Filter commits by message pattern",
    )
    parser.add_argument(
        "--branch", type=str,
        help="Show commits from specific branch (default: current)",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Show commits from all branches",
    )
    parser.add_argument(
        "--graph", action="store_true",
        help="Show ASCII branch graph",
    )

    return parser


def get_current_branch() -> str:
    """Get current branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "HEAD"


def is_git_repo() -> bool:
    """Check if we're in a git repo."""
    result = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        capture_output=True, text=True
    )
    return result.returncode == 0


def get_repo_name() -> str:
    """Get the repo name from the current directory."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True
        )
        return os.path.basename(result.stdout.strip())
    except subprocess.CalledProcessError:
        return os.path.basename(os.getcwd())


def get_commits(
    count: int = 20,
    author: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    grep: Optional[str] = None,
    branch: Optional[str] = None,
    all_branches: bool = False,
    graph: bool = False,
) -> list[dict]:
    """Fetch commits from git log."""
    # Format: hash|author|date|subject|refs
    fmt = "%H|%an|%ai|%s|%D"

    cmd = ["git", "log", f"--format={fmt}", f"-n{count}"]

    if author:
        cmd.append(f"--author={author}")
    if since:
        cmd.append(f"--since={since}")
    if until:
        cmd.append(f"--until={until}")
    if grep:
        cmd.append(f"--grep={grep}")
    if all_branches:
        cmd.append("--all")
    elif branch:
        cmd.append(branch)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError:
        return []

    commits = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("|", 4)
        if len(parts) >= 4:
            commits.append({
                "hash": parts[0][:8],
                "full_hash": parts[0],
                "author": parts[1],
                "date": parts[2],
                "subject": parts[3],
                "refs": parts[4] if len(parts) > 4 else "",
            })

    return commits


def get_graph_commits(
    count: int = 20,
    author: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    grep: Optional[str] = None,
    branch: Optional[str] = None,
    all_branches: bool = False,
) -> str:
    """Get git log with ASCII graph."""
    cmd = [
        "git", "log",
        "--graph",
        "--oneline",
        "--decorate",
        f"-n{count}",
    ]

    if author:
        cmd.append(f"--author={author}")
    if since:
        cmd.append(f"--since={since}")
    if until:
        cmd.append(f"--until={until}")
    if grep:
        cmd.append(f"--grep={grep}")
    if all_branches:
        cmd.append("--all")
    elif branch:
        cmd.append(branch)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError:
        return ""


def format_date(date_str: str) -> str:
    """Format git date to something readable."""
    try:
        # Git date format: 2024-01-15 14:30:00 +0100
        dt = datetime.strptime(date_str[:19], "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        diff = now - dt

        if diff.days == 0:
            hours = diff.seconds // 3600
            if hours == 0:
                mins = diff.seconds // 60
                return f"{mins}m ago" if mins > 0 else "just now"
            return f"{hours}h ago"
        elif diff.days == 1:
            return "yesterday"
        elif diff.days < 7:
            return f"{diff.days}d ago"
        elif diff.days < 30:
            weeks = diff.days // 7
            return f"{weeks}w ago"
        elif diff.days < 365:
            months = diff.days // 30
            return f"{months}mo ago"
        else:
            return dt.strftime("%Y-%m-%d")
    except ValueError:
        return date_str[:10]


def display_oneline(commits: list[dict]) -> None:
    """Display commits in compact one-line format."""
    for commit in commits:
        hash_text = Text(commit["hash"], style="yellow")
        subject = commit["subject"]

        # Add refs if present
        if commit["refs"]:
            refs = commit["refs"]
            # Color different ref types
            if "HEAD" in refs:
                refs_text = Text(f" ({refs})", style="cyan bold")
            elif "tag:" in refs:
                refs_text = Text(f" ({refs})", style="magenta")
            else:
                refs_text = Text(f" ({refs})", style="green")
            console.print(hash_text, subject, refs_text, sep=" ")
        else:
            console.print(hash_text, subject, sep=" ")


def display_table(commits: list[dict]) -> None:
    """Display commits in a nice table."""
    table = Table(
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
        expand=True,
    )

    table.add_column("Hash", style="yellow", width=8)
    table.add_column("Message", style="white", ratio=3)
    table.add_column("Author", style="green", width=15)
    table.add_column("Date", style="dim", width=10)

    for commit in commits:
        subject = commit["subject"]

        # Add branch/tag decoration
        if commit["refs"]:
            refs = commit["refs"]
            if "HEAD" in refs:
                subject = f"[cyan bold]({refs})[/] {subject}"
            elif "tag:" in refs:
                subject = f"[magenta]({refs})[/] {subject}"
            else:
                subject = f"[green]({refs})[/] {subject}"

        # Truncate long messages
        if len(subject) > 60:
            subject = subject[:57] + "..."

        # Truncate author name
        author = commit["author"]
        if len(author) > 15:
            author = author[:12] + "..."

        table.add_row(
            commit["hash"],
            subject,
            author,
            format_date(commit["date"]),
        )

    console.print(table)


def display_graph(graph_output: str) -> None:
    """Display the git graph output with colors."""
    for line in graph_output.split("\n"):
        if not line:
            continue

        # Color the graph characters
        text = Text()
        i = 0
        while i < len(line):
            char = line[i]
            if char in "*/|\\":
                text.append(char, style="cyan")
            elif char == "-":
                text.append(char, style="cyan")
            else:
                # Rest of the line (hash + message)
                rest = line[i:]
                # Try to color the hash (first 7-8 chars after graph)
                parts = rest.split(" ", 1)
                if parts:
                    text.append(parts[0], style="yellow")
                    if len(parts) > 1:
                        text.append(" " + parts[1])
                break
            i += 1

        console.print(text)


def main(argv: list[str] = None) -> int:
    """Main entry point for iskra log."""
    parser = create_argument_parser()
    args = parser.parse_args(argv)

    # Check if we're in a git repo
    if not is_git_repo():
        console.print(f"{style('Error:', 'error')} Not in a git repository")
        return 1

    repo_name = get_repo_name()
    branch = args.branch or get_current_branch()

    # Header
    console.print()
    console.print(
        Panel(
            f"{style(repo_name, 'highlight')} {style('on', 'dim')} {style(branch, 'primary')}",
            border_style=get_color("dim") or "dim",
            padding=(0, 1),
        )
    )
    console.print()

    if args.graph:
        # Graph mode
        graph_output = get_graph_commits(
            count=args.count,
            author=args.author,
            since=args.since,
            until=args.until,
            grep=args.grep,
            branch=args.branch,
            all_branches=args.all,
        )
        if graph_output:
            display_graph(graph_output)
        else:
            console.print(style("No commits found", "dim"))
    else:
        # Regular log
        commits = get_commits(
            count=args.count,
            author=args.author,
            since=args.since,
            until=args.until,
            grep=args.grep,
            branch=args.branch,
            all_branches=args.all,
        )

        if not commits:
            console.print(style("No commits found", "dim"))
            return 0

        if args.oneline:
            display_oneline(commits)
        else:
            display_table(commits)

    console.print()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
