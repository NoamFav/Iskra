""""""

import shutil
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from rich.box import DOUBLE

from ..core.constants import ICONS, FILE_ICONS

# Global console instance for consistent output handling
console = Console()


def get_icon(name):
    """"""
    return ICONS.get(name, "📄")


def get_file_icon(filename):
    """"""
    # Handle files without extensions (e.g., LICENSE, Makefile, .gitignore)
    if "." not in filename:
        return get_icon("file")

    # Extract extension and normalize to lowercase for case-insensitive lookup
    # "script.PY" → "py", "archive.tar.gz" → "gz"
    extension = filename.split(".")[-1].lower()

    # Look up semantic icon type for this extension
    # FILE_ICONS maps extensions to ICONS keys (e.g., "py" → "python")
    icon_type = FILE_ICONS.get(extension, "file")

    # Resolve semantic name to actual emoji character
    return get_icon(icon_type)


def print_header(text, title="Git Project Manager"):
    """"""
    # Add visual separation before header
    console.print()

    # Create centered, padded panel with double-line border
    panel = Panel(
        # Center text both horizontally and vertically within panel
        Align.center(f"[bold white]{text}[/]", vertical="middle"),
        # Visual styling
        border_style="cyan",  # Professional, high-contrast color
        box=DOUBLE,  # Emphasized double-line border
        # Title (appears above panel)
        title=f"[bold blue]{title}[/]",  # Application/command name
        title_align="center",  # Centered title
        # Subtitle (appears below panel)
        subtitle=f"[bold cyan]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/]",
        subtitle_align="center",  # Centered timestamp
        # Spacing and dimensions
        padding=(1, 4),  # (vertical, horizontal) padding
        width=shutil.get_terminal_size().columns - 2,  # Fit terminal width
    )

    # Display the panel
    console.print(panel)

    # Add visual separation after header
    console.print()
