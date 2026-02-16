"""
Formatting utilities. Icons, file icons, headers, colors.
The cosmetic surgery department.
"""

from datetime import datetime
from functools import lru_cache
from rich.console import Console

from ..core.constants import ICONS, FILE_ICONS, MINIMAL_ICONS


console = Console()

# Default color palette - used when no ui.yaml or theme override
DEFAULT_COLORS = {
    "primary": "cyan",
    "secondary": "yellow",
    "success": "green",
    "error": "red",
    "warning": "yellow",
    "info": "blue",
    "dim": "dim",
    "header": "bold cyan",
    "subheader": "bold white",
    "command": "green",
    "option": "yellow",
    "muted": "dim white",
    "highlight": "bold white",
    "link": "blue underline",
}

# Minimal palette - no colors, just text
MINIMAL_COLORS = {
    "primary": "",
    "secondary": "",
    "success": "",
    "error": "",
    "warning": "",
    "info": "",
    "dim": "",
    "header": "",
    "subheader": "",
    "command": "",
    "option": "",
    "muted": "",
    "highlight": "",
    "link": "",
}


# Module-level override for minimal mode (set via CLI flag)
_minimal_mode_override: bool = False


@lru_cache(maxsize=1)
def _get_ui_config():
    """Lazy load UI config. Cached so we don't hit disk every icon."""
    from ..config import get_config
    return get_config().ui_config


def set_minimal_mode(enabled: bool = True) -> None:
    """Enable/disable minimal mode via CLI flag."""
    global _minimal_mode_override
    _minimal_mode_override = enabled


def _is_minimal() -> bool:
    """Check if minimal mode is active (via CLI or config)."""
    if _minimal_mode_override:
        return True
    return _get_ui_config().theme == "minimal"


def _icons_enabled() -> bool:
    """Check if icons are enabled (respects CLI override)."""
    if _minimal_mode_override:
        return False
    return _get_ui_config().icons_enabled


def get_color(name: str) -> str:
    """Get a color by semantic name. Returns empty string in minimal mode."""
    # Minimal mode = no colors
    if _is_minimal():
        return MINIMAL_COLORS.get(name, "")

    ui_config = _get_ui_config()

    # Check for user overrides first
    if ui_config.colors and name in ui_config.colors:
        return ui_config.colors[name]

    # Fall back to defaults
    return DEFAULT_COLORS.get(name, "")


def style(text: str, color_key: str) -> str:
    """Wrap text in Rich markup using semantic color. No-op in minimal mode."""
    color = get_color(color_key)
    if not color:
        return text
    return f"[{color}]{text}[/]"


def get_icon(name: str) -> str:
    """Get an emoji icon by name. Falls back to minimal if icons disabled."""
    if not _icons_enabled():
        return MINIMAL_ICONS.get(name, "")
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
