import shutil
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.align import Align

from ..core.constants import ICONS, FILE_ICONS


console = Console()


def get_icon(name):
    return ICONS.get(name, "📄")


def get_file_icon(filename):
    if "." not in filename:
        return get_icon("file")

    extension = filename.split(".")[-1].lower()
    icon_type = FILE_ICONS.get(extension, "file")

    return get_icon(icon_type)


def print_header(text, title="Git Project Manager"):
    """Modern minimal header without heavy boxes."""
    console.print()

    # Minimal centered header
    console.print(f"[bold white]{text}[/]", justify="center")
    console.print(
        f"[dim]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/]", justify="center"
    )

    console.print()
