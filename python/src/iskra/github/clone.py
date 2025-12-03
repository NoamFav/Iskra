import os
import time
import subprocess
import shutil
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..ui.formatting import get_icon
from ..core.repo_scanner import find_repo_in_subdirs


console = Console()


def get_repo_size_str(repo_dir):

    total_size = 0

    for dirpath, _, filenames in os.walk(repo_dir):
        for f in filenames:

            fp = os.path.join(dirpath, f)

            if not os.path.islink(fp):

                total_size += os.path.getsize(fp)

    units = ["B", "KB", "MB", "GB", "TB"]
    size = total_size
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    return f"{size:.2f} {units[unit_index]}"


def process_repository(repo_info, base_dir, total, current):

    repo_name = repo_info["nameWithOwner"]

    repo_short_name = repo_name.split("/")[-1]

    is_private = repo_info.get("isPrivate", False)
    is_fork = repo_info.get("isFork", False)
    stars = repo_info.get("stargazerCount", 0)
    description = repo_info.get("description", "No description available")
    url = repo_info.get("url", "")

    repo_icon = get_icon("lock") if is_private else get_icon("unlock")

    fork_text = f" ({get_icon('fork')} Fork)" if is_fork else ""

    star_text = f" {get_icon('star')} {stars}" if stars > 0 else ""

    repo_panel = Panel(
        f"[dim cyan]{description}[/]\n[blue]{url}[/]",
        title=f"[bold]{repo_icon} {repo_name}{fork_text}{star_text}[/]",
        title_align="left",
        border_style="blue" if not is_private else "magenta",
        subtitle=f"[dim]Repository {current} of {total}[/]",
        subtitle_align="right",
        padding=(1, 2),
    )
    console.print(repo_panel)

    start_time = time.time()
    ok = True

    existing_repo_path = find_repo_in_subdirs(base_dir, repo_short_name)

    if existing_repo_path:

        rel_path = os.path.relpath(existing_repo_path, base_dir)
        console.print(
            f"[yellow]{get_icon('warning')} Repository already exists at: "
            f"[bold]{rel_path}[/], skipping..."
        )
    else:

        try:

            with console.status(
                f"[bold blue]Cloning {repo_name}...[/]", spinner="dots"
            ):
                subprocess.run(
                    ["gh", "repo", "clone", repo_name],
                    cwd=base_dir,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

            end_time = time.time()
            elapsed = end_time - start_time

            console.print(
                f"[bold green]{get_icon('success')} Successfully cloned in "
                f"{elapsed:.2f} seconds."
            )

            repo_dir = os.path.join(base_dir, repo_short_name)
            if os.path.isdir(repo_dir):

                file_count = sum(len(files) for _, _, files in os.walk(repo_dir))
                dir_count = sum(len(dirs) for _, dirs, _ in os.walk(repo_dir))

                stats_table = Table(show_header=False, box=None, pad_edge=False)
                stats_table.add_column("", style="cyan")
                stats_table.add_column("", style="white")

                stats_table.add_row(
                    f"{get_icon('folder')} Directories:", f"{dir_count}"
                )
                stats_table.add_row(f"{get_icon('file')} Files:", f"{file_count}")
                stats_table.add_row(
                    f"{get_icon('code')} Repository size:",
                    f"{get_repo_size_str(repo_dir)}",
                )

                console.print(stats_table)

        except subprocess.CalledProcessError as e:

            ok = False
            console.print(f"[bold red]{get_icon('error')} Error cloning repository:")

            console.print(Panel(e.stderr, title="Error Details", border_style="red"))

    separator_count = shutil.get_terminal_size().columns // 2
    console.print(f"[dim cyan]{get_icon('separator') * separator_count}[/]")
    console.print()

    return ok
