"""
GitHub repository cloning utilities.

Provides functions for cloning repositories from GitHub using the GitHub CLI,
with rich visual feedback, progress tracking, and repository statistics.
Handles duplicate detection, error cases, and displays detailed information
about cloned repositories.

Key Features:
    - Visual progress indicators during cloning
    - Duplicate repository detection
    - Repository statistics (size, file count, directory count)
    - Detailed error reporting
    - Rich UI with panels and tables

Dependencies:
    - GitHub CLI (gh): For cloning repositories
    - Rich: For visual output
"""

import os
import time
import subprocess
import shutil
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..ui.formatting import get_icon
from ..core.repo_scanner import find_repo_in_subdirs

# Global console instance for consistent output
console = Console()


def get_repo_size_str(repo_dir):
    """
        Get the size of a repository in human-readable format.

        Recursively walks the repository directory tree, calculating
        total size of all files. Formats the result with appropriate
        units (B, KB, MB, GB, TB) for readability.

        Args:
            repo_dir: Absolute path to repository directory

        Returns:
            Human-readable size string (e.g., "15.43 MB", "2.31 GB")

        Size Calculation:
            - Walks entire directory tree recursively
            - Sums size of all regular files
            - Skips symbolic links (doesn't follow, doesn't count)
            - Includes .git directory in calculation

        Units:
            - B (Bytes): 0-1023 bytes
            - KB (Kilobytes): 1024 bytes - 1023 KB
            - MB (Megabytes): 1024 KB - 1023 MB
            - GB (Gigabytes): 1024 MB - 1023 GB
            - TB (Terabytes): 1024 GB and above

        Example Usage:
    ```python
            size = get_repo_size_str("/path/to/repo")
            print(f"Repository size: {size}")
            # Output: "Repository size: 42.15 MB"
    ```

        Performance:
            - O(n) where n = total number of files
            - I/O bound operation (reads file metadata)
            - Can be slow for large repositories (10,000+ files)
            - Typical repo: <1 second
            - Large monorepo: 5-10 seconds

        Accuracy:
            - Reports actual disk usage (sum of file sizes)
            - Does NOT account for:
              * Filesystem block size (can be larger)
              * Sparse files (reports logical size)
              * Compressed filesystems
              * Hard links (counts each link separately)

        Edge Cases:
            - Empty directory: Returns "0 B"
            - Symbolic links: Ignored (not followed or counted)
            - Permission errors: May raise OSError
            - Non-existent directory: Raises OSError

        Note:
            For very large repositories, consider caching this value
            or computing it asynchronously to avoid blocking the UI.
    """
    total_size = 0

    # Walk entire directory tree
    # os.walk yields (dirpath, dirnames, filenames) tuples
    for dirpath, _, filenames in os.walk(repo_dir):
        for f in filenames:
            # Construct full path to file
            fp = os.path.join(dirpath, f)

            # Skip symbolic links
            # Following symlinks could:
            # - Cause infinite loops (circular links)
            # - Count same files multiple times
            # - Escape repository directory
            if not os.path.islink(fp):
                # Add file size to total
                # os.path.getsize() returns bytes
                total_size += os.path.getsize(fp)

    # Convert bytes to appropriate unit for readability
    units = ["B", "KB", "MB", "GB", "TB"]
    size = total_size
    unit_index = 0

    # Divide by 1024 until we reach appropriate unit
    # Stops at TB even if larger
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    # Format with 2 decimal places and unit
    return f"{size:.2f} {units[unit_index]}"


def process_repository(repo_info, base_dir, total, current):
    """
        Clone a repository with visual enhancements and progress tracking.

        Handles the complete repository cloning workflow including duplicate
        detection, visual feedback, error handling, and post-clone statistics.
        Provides rich UI elements for an excellent user experience.

        Args:
            repo_info: Dictionary containing repository metadata from GitHub API:
                - nameWithOwner: Full name (e.g., "owner/repo")
                - name: Short name (e.g., "repo")
                - isPrivate: Boolean privacy status
                - isFork: Boolean fork status
                - stargazerCount: Number of stars
                - description: Repository description text
                - url: Repository URL
            base_dir: Base directory where repository should be cloned
            total: Total number of repositories being processed
            current: Current repository number (for progress display)

        Returns:
            True if repository was cloned successfully or already exists
            False if cloning failed with an error

        Workflow:
            1. Extract and format repository metadata
            2. Display repository information panel
            3. Check for existing repository (duplicate detection)
            4. Clone repository if not exists
            5. Display cloning time and statistics
            6. Show visual separator

        Visual Output:
            - Repository panel with:
              * Name with privacy/fork indicators
              * Star count if any
              * Description
              * URL
              * Progress indicator (X of N)
            - Status messages during cloning
            - Success message with timing
            - Statistics table (directories, files, size)
            - Error panel if cloning fails
            - Visual separator between repositories

        Duplicate Detection:
            Uses find_repo_in_subdirs() to search for existing repo
            anywhere under base_dir. Prevents:
            - Duplicate clones in same directory
            - Clones in subdirectories
            - Wasted bandwidth and disk space

        Error Handling:
            - Catches subprocess.CalledProcessError from gh clone
            - Displays stderr in error panel
            - Returns False to indicate failure
            - Allows batch processing to continue

        Example Usage:
    ```python
            repo_info = {
                "nameWithOwner": "user/awesome-project",
                "name": "awesome-project",
                "isPrivate": False,
                "isFork": False,
                "stargazerCount": 142,
                "description": "An awesome project",
                "url": "https://github.com/user/awesome-project"
            }

            success = process_repository(
                repo_info=repo_info,
                base_dir="/home/user/repos",
                total=10,
                current=1
            )
    ```

        Performance:
            - Network bound (git clone speed)
            - Small repos: 5-30 seconds
            - Large repos: 1-10 minutes
            - Depends on network speed and repository size

        Side Effects:
            - Clones repository to base_dir/{repo_name}
            - Prints Rich UI elements to console
            - Temporarily changes working directory (via subprocess cwd)

        Note:
            This function is designed for sequential processing.
            For parallel cloning, additional coordination would be needed
            to avoid console output conflicts and directory collisions.
    """
    # === EXTRACT REPOSITORY METADATA ===

    # Full name includes owner: "owner/repo"
    repo_name = repo_info["nameWithOwner"]
    # Short name is just the repo part: "repo"
    repo_short_name = repo_name.split("/")[-1]

    # Extract repository metadata with safe defaults
    is_private = repo_info.get("isPrivate", False)
    is_fork = repo_info.get("isFork", False)
    stars = repo_info.get("stargazerCount", 0)
    description = repo_info.get("description", "No description available")
    url = repo_info.get("url", "")

    # === FORMAT VISUAL ELEMENTS ===

    # Choose icon based on repository privacy
    # Private repos get lock icon, public get unlock icon
    repo_icon = get_icon("lock") if is_private else get_icon("unlock")

    # Add fork indicator if repository is forked
    fork_text = f" ({get_icon('fork')} Fork)" if is_fork else ""

    # Add star count if repository has stars (popularity indicator)
    star_text = f" {get_icon('star')} {stars}" if stars > 0 else ""

    # === DISPLAY REPOSITORY INFORMATION PANEL ===

    # Create rich panel with repository details
    # Different border colors for private (magenta) vs public (blue)
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

    # Start timing for performance measurement
    start_time = time.time()
    ok = True  # Success flag

    # === DUPLICATE DETECTION ===

    # Check if repository already exists anywhere under base_dir
    # Searches recursively through all subdirectories
    existing_repo_path = find_repo_in_subdirs(base_dir, repo_short_name)

    if existing_repo_path:
        # Repository already exists - skip cloning
        # Display relative path for readability
        rel_path = os.path.relpath(existing_repo_path, base_dir)
        console.print(
            f"[yellow]{get_icon('warning')} Repository already exists at: "
            f"[bold]{rel_path}[/], skipping..."
        )
    else:
        # === CLONE REPOSITORY ===

        try:
            # Clone using GitHub CLI with visual spinner
            # gh repo clone is preferred over git clone because:
            # - Uses authenticated session (for private repos)
            # - Handles GitHub-specific features
            # - Respects gh configuration
            with console.status(
                f"[bold blue]Cloning {repo_name}...[/]", spinner="dots"
            ):
                subprocess.run(
                    ["gh", "repo", "clone", repo_name],
                    cwd=base_dir,  # Clone into base_dir
                    check=True,  # Raise exception on failure
                    stdout=subprocess.PIPE,  # Capture output
                    stderr=subprocess.PIPE,  # Capture errors
                    text=True,  # Decode as text
                )

            # === DISPLAY SUCCESS AND STATISTICS ===

            # Calculate cloning time
            end_time = time.time()
            elapsed = end_time - start_time

            console.print(
                f"[bold green]{get_icon('success')} Successfully cloned in "
                f"{elapsed:.2f} seconds."
            )

            # Calculate and display repository statistics
            repo_dir = os.path.join(base_dir, repo_short_name)
            if os.path.isdir(repo_dir):
                # Count files and directories recursively
                # Walks entire tree to get accurate counts
                file_count = sum(len(files) for _, _, files in os.walk(repo_dir))
                dir_count = sum(len(dirs) for _, dirs, _ in os.walk(repo_dir))

                # Create statistics table
                # Compact layout without borders for clean display
                stats_table = Table(show_header=False, box=None, pad_edge=False)
                stats_table.add_column("", style="cyan")  # Labels
                stats_table.add_column("", style="white")  # Values

                # Add statistics rows
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
            # === ERROR HANDLING ===

            # Cloning failed - display error details
            ok = False
            console.print(f"[bold red]{get_icon('error')} Error cloning repository:")

            # Display stderr from gh command in error panel
            # Shows git errors, authentication issues, etc.
            console.print(Panel(e.stderr, title="Error Details", border_style="red"))

    # === VISUAL SEPARATOR ===

    # Print separator line between repositories for visual clarity
    # Uses terminal width to create full-width separator
    separator_count = shutil.get_terminal_size().columns // 2
    console.print(f"[dim cyan]{get_icon('separator') * separator_count}[/]")
    console.print()  # Blank line for spacing

    return ok
