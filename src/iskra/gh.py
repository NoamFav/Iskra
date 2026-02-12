# src/iskra/gh.py
import sys
import subprocess
import argparse
import json
import webbrowser

from rich.console import Console
from rich.table import Table

from rich.panel import Panel
from .github import get_prs

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


def cmd_prs(
    repo_path: str,
    limit: int,
    state: str,
    draft: str,
    need_review: bool,
    require_changes: bool,
    open_number: int | None,
) -> int:
    remote = get_remote_url(repo_path)
    if not remote:
        console.print("[red]No 'origin' remote found[/]")
        return 1

    slug = parse_github_slug(remote)
    if not slug:
        console.print("[red]Remote is not a GitHub URL[/]")
        return 1

    try:
        console.print(
            f"[bold blue]{
                get_icon('github')
            } Fetching PRs for {slug}...[/]"
        )
        prs = get_prs(
            slug=slug,
            limit=limit,
            state=state,
            draft=draft,
            need_review=need_review,
            require_changes=require_changes,
        )
    except subprocess.CalledProcessError as e:
        console.print(
            f"[bold red]{get_icon('error')} Error fetching PRs from GitHub:[/]"
        )
        console.print(
            Panel(
                e.stderr or str(e),
                title="Error Details",
                border_style="red",
            )
        )
        return 1
    except json.JSONDecodeError as e:
        console.print(
            f"[bold red]{get_icon('error')} Error parsing GitHub response:[/]"
        )
        console.print(Panel(str(e), title="JSON Error", border_style="red"))
        return 1

    if open_number is not None:
        match = next(
            (
                pr
                for pr in prs
                if pr.get(
                    "number",
                )
                == open_number
            ),
            None,
        )
        if not match:
            console.print(
                f"[red]PR #{
                    open_number
                } not found in listed results[/]"
            )
            return 1
        url = match.get("url")
        if not url:
            console.print("[red]PR has no URL[/]")
            return 1
        console.print(f"{get_icon('link')} Opening [bold]{url}[/]...")
        webbrowser.open(url)
        return 0

    table = Table(
        title=f"{get_icon('project')} Pull Requests ({slug})",
        show_header=True,
        box=None,
        padding=(0, 1),
    )
    table.add_column("#", style="cyan", justify="right")
    table.add_column("Title", style="white")
    table.add_column("State", style="magenta")
    table.add_column("Draft", style="dim")
    table.add_column("Review", style="yellow")

    for pr in prs:
        table.add_row(
            str(pr.get("number", "")),
            pr.get("title", "") or "",
            pr.get("state", "") or "",
            "yes" if pr.get("isDraft", False) else "",
            pr.get("reviewDecision") or "",
        )

    console.print(table)
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

    prs_parser = subparsers.add_parser(
        "prs", help="List pull requests for current repo"
    )
    prs_parser.add_argument("--limit", type=int, default=50)
    prs_parser.add_argument(
        "--state",
        type=str,
        default="open",
        choices=[
            "open",
            "closed",
            "merged",
            "all",
        ],
    )
    prs_parser.add_argument(
        "--draft", type=str, default="all", choices=["all", "only", "exclude"]
    )
    prs_parser.add_argument("--need-review", action="store_true")
    prs_parser.add_argument("--require-changes", action="store_true")
    prs_parser.add_argument(
        "--open", type=int, default=None, help="Open PR number in browser"
    )
    args = parser.parse_args(argv)

    repo_root = get_git_root(".")
    if not repo_root:
        console.print("[red]iskra gh: not inside a git repository[/]")
        return 1

    if args.command == "info":
        return cmd_info(repo_root)
    if args.command == "open":
        return cmd_open(repo_root)
    if args.command == "prs":
        return cmd_prs(
            repo_root,
            limit=args.limit,
            state=args.state,
            draft=args.draft,
            need_review=args.need_review,
            require_changes=args.require_changes,
            open_number=args.open,
        )

    console.print("[red]Unknown gh command[/]")
    return 1
