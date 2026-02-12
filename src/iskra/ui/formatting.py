"""
Formatting utilities. Icons, file icons, headers.
The cosmetic surgery department.
"""

from datetime import datetime
from rich.console import Console

from ..core.constants import ICONS, FILE_ICONS


console = Console()


def get_icon(name):
    """Get an emoji icon by name. Falls back to a file icon."""
    return ICONS.get(name, "📄")


def get_file_icon(filename):
    """Pick an icon based on file extension. .py gets python, etc."""
    if "." not in filename:
        return get_icon("file")

    extension = filename.split(".")[-1].lower()
    icon_type = FILE_ICONS.get(extension, "file")

    return get_icon(icon_type)


def print_header(text, title="Git Project Manager"):
    """Print a centered header with timestamp. Fancy."""
    console.print()

    # Minimal centered header
    console.print(f"[bold white]{text}[/]", justify="center")
    console.print(
        f"[dim]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/]",
        justify="center",
    )

    console.print()
