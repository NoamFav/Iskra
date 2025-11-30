"""
UI formatting and display utilities.

Provides reusable components for creating consistent, visually appealing
terminal output using the Rich library. Includes icon mapping, file type
detection, and header generation for a polished user experience.

Components:
    - Icon system: Emoji-based visual indicators
    - File type icons: Extension-based file identification
    - Header panels: Branded application headers with timestamps
"""

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
    """
        Get an emoji icon based on semantic name.

        Provides a centralized icon lookup system that maps semantic
        names to emoji characters. This abstraction allows changing
        icons globally without updating call sites.

        Args:
            name: Semantic icon name (e.g., 'success', 'error', 'folder')

        Returns:
            Unicode emoji character or default file icon if name not found

        Icon Categories (from ICONS constant):
            - Status: success, error, warning, info
            - Git: commit, branch, merge, pull, push
            - Files: folder, file, code, config
            - Operations: sparkles, rocket, lightning

        Fallback Behavior:
            Returns generic file icon (📄) for unknown names rather than
            crashing. This makes the system resilient to typos and allows
            gradual expansion of the icon set.

        Example Usage:
    ```python
            print(f"{get_icon('success')} Operation completed")
            print(f"{get_icon('error')} Failed to connect")
            print(f"{get_icon('folder')} Scanning directory")
    ```

        Note:
            Icons are purely cosmetic and should never be used for logic.
            They enhance readability but must not affect functionality.
            Always include descriptive text alongside icons.
    """
    return ICONS.get(name, "📄")


def get_file_icon(filename):
    """
        Get an appropriate icon based on file extension.

        Maps file extensions to semantic icon names, then resolves to
        actual emoji. Provides visual file type identification in listings
        and status displays.

        Args:
            filename: File name or path (extension is extracted)

        Returns:
            Unicode emoji character representing the file type

        File Type Detection:
            - Extracts extension from filename (last dot segment)
            - Looks up extension in FILE_ICONS mapping
            - Falls back to generic file icon for unknown types
            - Handles extensionless files gracefully

        Supported File Types (examples from FILE_ICONS):
            - Code: .py → Python icon, .js → JavaScript icon
            - Markup: .md → Markdown icon, .html → HTML icon
            - Config: .yaml → Config icon, .json → Config icon
            - Media: .png → Image icon, .mp4 → Video icon

        Edge Cases:
            - No extension: Returns generic file icon
            - Hidden files (.gitignore): Treated as extensionless
            - Multiple dots (archive.tar.gz): Uses rightmost extension (gz)
            - Case insensitive: .PY and .py both match python

        Example Usage:
    ```python
            icon = get_file_icon("script.py")      # → 🐍
            icon = get_file_icon("README.md")      # → 📝
            icon = get_file_icon("config.yaml")    # → ⚙️
            icon = get_file_icon(".gitignore")     # → 📄
            icon = get_file_icon("binary")         # → 📄
    ```

        Performance:
            O(1) lookup after extension extraction. Suitable for large
            file listings without noticeable performance impact.

        Note:
            This is a heuristic based on file extension only. It does not
            inspect file contents or MIME types. Misnamed files will show
            incorrect icons (e.g., .txt file containing Python code).
    """
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
    """
        Print a fancy branded header panel with Rich.

        Creates a visually prominent header that appears at the start of
        operations. Includes the application name, current timestamp, and
        custom text describing the operation being performed.

        Args:
            text: Main header text to display (operation description)
            title: Application title shown above the panel (default: "Git Project Manager")

        Side Effects:
            Prints directly to console via Rich.
            Adds blank lines before and after for visual separation.

        Panel Structure:
            ╔════════════════════════════════════════════╗
            ║          Git Project Manager               ║
            ║                                            ║
            ║         Repository Scan Complete           ║  ← text parameter
            ║                                            ║
            ║            2024-01-15 14:30:45             ║  ← timestamp
            ╚════════════════════════════════════════════╝

        Styling:
            - Border: DOUBLE box for emphasis (╔═══╗ style)
            - Border color: Cyan - professional, high-contrast
            - Title: Bold blue - matches border, stands out
            - Main text: Bold white - high visibility
            - Subtitle: Bold cyan - matches border, less prominent than main text
            - Padding: (1, 4) - vertical and horizontal spacing
            - Width: Terminal width - 2 (fits cleanly with minimal margins)
    - Alignment: Centered both horizontally and vertically

        Terminal Width Adaptation:
            Automatically adapts to terminal width using shutil.get_terminal_size().
            Subtracts 2 columns to prevent line wrapping on most terminals.
            Works seamlessly across different terminal sizes and SSH sessions.

        Example Usage:
    ```python
            from iskra.ui.formatting import print_header

            print_header("Processing 42 repositories")
            print_header("GitHub Clone Manager", title="Pull Repos")
            print_header("Configuration Initialized", title="Iskra Setup")
    ```

        Timestamp Format:
            Uses ISO-like format: YYYY-MM-DD HH:MM:SS
            - Unambiguous date format (year-month-day)
            - 24-hour time notation
            - Second precision for operation tracking
            - Suitable for log correlation

        Design Rationale:
            - Visual hierarchy: Title > Main text > Timestamp
            - Professional appearance for CLI tools
            - Consistent branding across all Iskra commands
            - Timestamp aids in debugging and log analysis
            - Centering creates balanced, polished look

        Performance:
            Minimal overhead - one-time display at operation start.
            Terminal size query is fast and cached by most terminals.

        Note:
            This header is cosmetic and should not be relied upon for
            functionality. It's suppressed in JSON/quiet modes to avoid
            polluting machine-readable output.
    """
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
