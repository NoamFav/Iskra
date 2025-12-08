# src/iskra/gh.py
import os
import sys
import subprocess
import argparse
import webbrowser

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from iskra.ui.formatting import get_icon

console = Console()


def get_git_root(path: str = ".") -> str | None:
    result = subprocess.run(
        ["git", "-C", path, "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def get_remote_url(repo_path: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", repo_path, "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def parse_github_slug(remote_url: str) -> str | None:
    # supports:
    #   git@github.com:user/repo.git
    #   https://github.com/user/repo.git
    #   https://github.com/user/repo
    if "github.com" not in remote_url:
        return None

    url = remote_url.rstrip("/")
    url = url.removesuffix(".git")

    if url.startswith("git@github.com:"):
        return url.split("git@github.com:")[1]
    if "github.com/" in url:
        return url.split("github.com/")[1]

    return None


def cmd_info(repo_path: str) -> int:
    remote = get_remote_url(repo_path)
    if not remote:
        console.print("[red]No 'origin' remote found[/]")
        return 1

    slug = parse_github_slug(remote)

    table = Table(
        title=f"{get_icon('project')} GitHub Info",
        show_header=False,
        box=None,
        padding=(0, 2),
    )
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Repo path", repo_path)
    table.add_row("Remote", remote)
    table.add_row("GitHub slug", slug or "[dim]not a GitHub repo[/]")

    console.print(table)
    return 0


def cmd_open(repo_path: str) -> int:
    remote = get_remote_url(repo_path)
    if not remote:
        console.print("[red]No 'origin' remote found[/]")
        return 1

    slug = parse_github_slug(remote)
    if not slug:
        console.print("[red]Remote is not a GitHub URL[/]")
        return 1

    url = f"https://github.com/{slug}"
    console.print(f"{get_icon('link')} Opening [bold]{url}[/]...")
    webbrowser.open(url)
    return 0


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="Iskra GitHub integration",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("info", help="Show GitHub info for current repo")
    subparsers.add_parser("open", help="Open GitHub repo page in browser")
    # later: issues, prs, status, etc.

    args = parser.parse_args(argv)

    repo_root = get_git_root(".")
    if not repo_root:
        console.print("[red]iskra gh: not inside a git repository[/]")
        return 1

    if args.command == "info":
        return cmd_info(repo_root)
    if args.command == "open":
        return cmd_open(repo_root)

    console.print("[red]Unknown gh command[/]")
    return 1
