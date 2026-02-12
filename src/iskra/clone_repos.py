"""
Clone repos from GitHub. Bulk clone all your repos.
Supports filters for forks, stars, exclude patterns.
"""

import os
import argparse
import argcomplete
from rich.console import Console
from rich.panel import Panel
from rich.traceback import install as install_traceback
from typing import Optional

from .ui.formatting import print_header, get_icon
from .ui.tables import create_config_table
from .github.api import get_github_repos
from .github.clone import process_repository
from .output.formatter import (
    get_formatter,
    OutputPayload,
    RepoResult,
    RepoStatusType,
    RepoRemote,
)


install_traceback(show_locals=True)


console = Console()


def main(argv: Optional[list[str]] = None):

    parser = argparse.ArgumentParser(
        description="Clone GitHub repositories with rich visual interface.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--base-dir",
        type=str,
        default=os.path.expanduser("~/Neoware"),
        help="Base directory where repositories will be cloned.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Maximum number of repositories to fetch.",
    )

    parser.add_argument(
        "--filter-forks",
        action="store_true",
        help="Filter out forked repositories.",
    )

    parser.add_argument(
        "--only-stars",
        type=int,
        default=0,
        help="Only clone repositories with at least this many stars.",
    )

    parser.add_argument(
        "--exclude",
        type=str,
        nargs="+",
        default=[],
        help="List of repository name patterns to exclude"
        + "(supports glob patterns).",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON instead of Rich UI.",
    )

    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress Rich UI and output only JSON.",
    )

    args = parser.parse_args(argv)
    argcomplete.autocomplete(parser)

    base_dir = args.base_dir

    formatter = get_formatter(
        json_mode=args.json,
        quiet=args.quiet,
        console=console,
    )

    print_header(
        "GitHub Repository Clone Manager",
        title="GitHub Clone Manager",
    )

    config_table = create_config_table(args, for_pull_repos=True)
    console.print(config_table)

    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
        console.print(
            f"[cyan]{get_icon('folder')} Created base directory at {base_dir}"
        )

    repositories = get_github_repos(
        limit=args.limit,
        filter_forks=args.filter_forks,
        only_stars=args.only_stars,
        exclude=args.exclude,
    )

    repo_results: list[RepoResult] = []
    errors: list[str] = []
    success_count = 0
    total = len(repositories)

    if not (args.json or args.quiet):
        summary_panel = Panel(
            f"{
                get_icon('github')
            } Found [bold green]{total}[/] repositories to process\n"
            + f"{
                get_icon('folder')
            } Target directory: [bold blue]{base_dir}[/]",
            title="Repository Summary",
            border_style="blue",
        )
        console.print(summary_panel)

    if repositories:
        if not (args.json or args.quiet):
            console.print(f"[bold blue]Processing {total} repositories...[/]")

        for idx, repo in enumerate(repositories, 1):

            ok = process_repository(repo, base_dir, total, idx)

            if ok:
                success_count += 1

            status: RepoStatusType = "success" if ok else "failed"

            repo_name = repo.get("name", "")
            repo_short_name = (
                repo_name
                or repo.get(
                    "nameWithOwner",
                    "",
                ).split(
                    "/"
                )[-1]
            )

            repo_path = os.path.join(base_dir, repo_short_name)

            repo_results.append(
                RepoResult(
                    path=repo_path,
                    name=repo_name or repo_short_name,
                    status=status,
                    remote=RepoRemote(
                        url=repo.get("url", ""),
                        ahead=0,
                        behind=0,
                    ),
                    error=None if ok else "clone_failed",
                )
            )

        if not (args.json or args.quiet):
            console.print()
            final_panel = Panel(
                f"{
                    get_icon('sparkles')
                } [bold]{success_count}/{total}[/] repositories "
                f"processed successfully {get_icon('sparkles')}",
                border_style="green" if success_count == total else "yellow",
                title="Processing Complete",
                title_align="center",
            )
            console.print(final_panel)
    else:

        if not (args.json or args.quiet):
            console.print(
                f"[bold yellow]{
                    get_icon('warning')
                } No repositories found to process[/]"
            )

    payload = OutputPayload(
        success=(success_count == total and total > 0),
        operation="pull",
        repos_total=total,
        repos_success=success_count,
        repos_failed=total - success_count,
        results=repo_results,
        errors=errors,
    )

    formatter.emit(payload)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:

        console.print("\n[bold red]Operation canceled by user[/]")
    except Exception:

        console.print_exception()
