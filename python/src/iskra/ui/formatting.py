"""UI formatting and display utilities."""

import shutil
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from rich.box import DOUBLE

from ..core.constants import ICONS, FILE_ICONS

console = Console()


def get_icon(name):
    """Get an icon based on name"""
    return ICONS.get(name, "📄")


def get_file_icon(filename):
    """Get an appropriate icon based on file extension"""
    if "." not in filename:
        return get_icon("file")

    extension = filename.split(".")[-1].lower()
    icon_type = FILE_ICONS.get(extension, "file")
    return get_icon(icon_type)


def print_header(text, title="Git Project Manager"):
    """Print a fancy header with Rich"""
    console.print()
    panel = Panel(
        Align.center(f"[bold white]{text}[/]", vertical="middle"),
        border_style="cyan",
        box=DOUBLE,
        title=f"[bold blue]{title}[/]",
        title_align="center",
        subtitle=f"[bold cyan]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/]",
        subtitle_align="center",
        padding=(1, 4),
        width=shutil.get_terminal_size().columns - 2,
    )
    console.print(panel)
    console.print()
