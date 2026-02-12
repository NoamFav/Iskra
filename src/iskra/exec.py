"""
iskra exec - run any command across all your repos.

Like gita's superman mode but prettier.
Git commands, shell commands, whatever. It'll run it everywhere.
"""

import os
import sys
import argparse
import subprocess
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn

from iskra.config import get_config
from iskra.core.repository_selector import RepositorySelector
from iskra.core.filters import RepoFilter


console = Console()


def create_argument_parser() -> argparse.ArgumentParser:
    """All the flags for exec."""
    parser = argparse.ArgumentParser(
        description="Execute commands across multiple repositories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  iskra exec "git log --oneline -5"
  iskra exec "git fetch --all"
  iskra exec "npm install"
  iskra exec --only "api-*" "make test"
        """,
    )

    parser.add_argument(
        "command", type=str,
        help="Command to execute (use quotes for multi-word commands)",
    )
    parser.add_argument(
        "--only", type=str, nargs="+", default=[],
        help="Only include repos matching patterns",
    )
    parser.add_argument(
        "--exclude", type=str, nargs="+", default=[],
        help="Exclude repos matching patterns",
    )
    parser.add_argument(
        "--scan", action="store_true",
        help="Scan for repos instead of using tracked repos",
    )
    parser.add_argument(
        "--dir", type=str,
        help="Base directory (overrides config)",
    )
    parser.add_argument(
        "-y", "--yes", action="store_true",
        help="Skip confirmation prompt",
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true",
        help="Only show output, no headers",
    )
    parser.add_argument(
        "--fail-fast", action="store_true",
        help="Stop on first error",
    )
    parser.add_argument(
        "--parallel", "-p", type=int, default=1,
        help="Number of parallel executions (default: 1)",
    )

    return parser


def execute_command(repo_path: str, command: str, quiet: bool = False) -> tuple:
    """Run command in a repo. Returns (success, stdout, stderr)."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=300,  # 5 min timeout
        )
        return (
            result.returncode == 0,
            result.stdout.strip(),
            result.stderr.strip(),
        )
    except subprocess.TimeoutExpired:
        return (False, "", "Command timed out after 5 minutes")
    except Exception as e:
        return (False, "", str(e))


def execute_parallel(
    git_repos: list,
    command: str,
    max_workers: int,
    quiet: bool,
    fail_fast: bool,
    console: Console,
) -> list:
    """
    Run command across repos in parallel. Fancy spinner included.
    ThreadPoolExecutor go brrrr.
    The output buffering is so things don't interleave. You're welcome.
    """
    results = []
    stop_flag = False

    def run_one(repo_tuple):
        repo_path, meta = repo_tuple
        repo_name = os.path.basename(repo_path)
        success, stdout, stderr = execute_command(repo_path, command, quiet)
        return {
            "repo": repo_name,
            "path": repo_path,
            "success": success,
            "stdout": stdout,
            "stderr": stderr,
        }

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task(
            f"Running across {len(git_repos)} repos...",
            total=len(git_repos),
        )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(run_one, repo): repo for repo in git_repos}

            for future in as_completed(futures):
                if stop_flag:
                    break
                result = future.result()
                results.append(result)
                progress.advance(task)

                if fail_fast and not result["success"]:
                    stop_flag = True
                    for f in futures:
                        f.cancel()

    # show results after all done (so output doesn't interleave)
    if not quiet:
        console.print()
        for result in results:
            header = Text()
            if result["success"]:
                header.append("✓ ", style="green bold")
                header.append(result["repo"], style="bold")
                if result["stdout"]:
                    console.print(Panel(
                        result["stdout"],
                        title=str(header),
                        title_align="left",
                        border_style="green",
                        padding=(0, 1),
                    ))
                else:
                    console.print(
                        f"[green]✓[/] [bold]{result['repo']}[/] [dim](no output)[/]"
                    )
            else:
                header.append("✗ ", style="red bold")
                header.append(result["repo"], style="bold")
                error_output = result["stderr"] or "(command failed)"
                console.print(Panel(
                    error_output,
                    title=str(header),
                    title_align="left",
                    border_style="red",
                    padding=(0, 1),
                ))

    return results


def main(argv: Optional[list[str]] = None) -> int:
    """Main entry point. Returns 0 on success, 1 on failure. Shell convention."""
    if argv is None:
        argv = sys.argv[1:]

    parser = create_argument_parser()
    args = parser.parse_args(argv)

    config_manager = get_config()
    config = config_manager.global_config

    if args.dir:
        config.base_dir = args.dir

    base_dir = os.path.expanduser(config.base_dir)

    # get repos
    try:
        selector = RepositorySelector(config_manager, config, base_dir)
        git_repos, tracked_repos = selector.get_repositories(
            scan=args.scan, pulse=False
        )
    except RuntimeError as e:
        console.print(f"[red]Error: {e}[/]")
        return 1

    # filter
    if args.only or args.exclude:
        repo_paths = [path for path, _ in git_repos]
        if args.only:
            filtered = RepoFilter.filter_by_pattern(
                repo_paths, include_patterns=args.only
            )
            git_repos = [(p, m) for p, m in git_repos if p in filtered]
        if args.exclude:
            filtered = RepoFilter.filter_by_pattern(
                repo_paths, exclude_patterns=args.exclude
            )
            git_repos = [(p, m) for p, m in git_repos if p in filtered]

    if not git_repos:
        console.print("[yellow]No repositories found[/]")
        return 0

    # preview
    if not args.quiet:
        console.print(
            f"\n[bold]Running command across {len(git_repos)} repositories:[/]"
        )
        console.print(f"[cyan]$ {args.command}[/]\n")

    # confirm
    if not args.yes and not args.quiet:
        response = console.input("[dim]Continue? [Y/n]: [/]").lower()
        if response not in ("", "y", "yes"):
            console.print("[yellow]Cancelled[/]")
            return 0

    # do the thing
    success_count = 0
    fail_count = 0
    results = []

    if args.parallel > 1:
        results = execute_parallel(
            git_repos, args.command, args.parallel,
            args.quiet, args.fail_fast, console
        )
        for r in results:
            if r["success"]:
                success_count += 1
            else:
                fail_count += 1
    else:
        # sequential
        for repo_path, meta in git_repos:
            repo_name = os.path.basename(repo_path)
            success, stdout, stderr = execute_command(
                repo_path, args.command, args.quiet
            )

            if success:
                success_count += 1
                if not args.quiet:
                    header = Text()
                    header.append("✓ ", style="green bold")
                    header.append(repo_name, style="bold")
                    if stdout:
                        console.print(Panel(
                            stdout,
                            title=str(header),
                            title_align="left",
                            border_style="green",
                            padding=(0, 1),
                        ))
                    else:
                        console.print(
                            f"[green]✓[/] [bold]{repo_name}[/] [dim](no output)[/]"
                        )
            else:
                fail_count += 1
                if not args.quiet:
                    header = Text()
                    header.append("✗ ", style="red bold")
                    header.append(repo_name, style="bold")
                    error_output = stderr if stderr else "(command failed)"
                    console.print(Panel(
                        error_output,
                        title=str(header),
                        title_align="left",
                        border_style="red",
                        padding=(0, 1),
                    ))

                if args.fail_fast:
                    console.print("\n[red]Stopped: --fail-fast enabled[/]")
                    break

            results.append({
                "repo": repo_name,
                "path": repo_path,
                "success": success,
                "stdout": stdout,
                "stderr": stderr,
            })

    # summary
    if not args.quiet:
        console.print()
        if fail_count == 0:
            console.print(
                f"[green bold]✓ All {success_count} repositories completed successfully[/]"
            )
        else:
            console.print(
                f"[yellow]Completed: {success_count} succeeded, {fail_count} failed[/]"
            )

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
