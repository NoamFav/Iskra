"""
Binary wrapper for ai_commit executable.

This module provides a Python entry point that locates and executes the
bundled ai_commit binary. The actual AI commit message generation logic
is implemented in a compiled binary (Rust/Go) for performance and to
encapsulate complex AI integration logic.

Architecture:
    - Python wrapper (this file): Entry point, path resolution, error handling
    - Compiled binary (ai_commit/ai_commit.exe): Core AI logic, API calls

The binary is bundled in the package under iskra/bin/ and executed via
os.execv() to replace the Python process entirely, maintaining full
compatibility with shell pipelines and signal handling.

Platform Support:
    - Unix/Linux/macOS: ai_commit (ELF/Mach-O binary)
    - Windows: ai_commit.exe (PE executable)
"""

import os
import sys
from importlib.resources import files


def _binary_path():
    """
    Locate the platform-specific ai_commit binary within the package.

    Uses importlib.resources to find the binary in the installed package,
    which works correctly whether the package is installed normally,
    in development mode (pip install -e), or as a wheel.

    Returns:
        Absolute path to the ai_commit binary for the current platform

    Platform Detection:
        Uses os.name to determine platform:
        - 'nt' (Windows) → ai_commit.exe
        - 'posix' (Unix-like) → ai_commit

    Note:
        The binary must be included in MANIFEST.in and package_data
        for it to be bundled with the package distribution.

    Example Path:
        /usr/local/lib/python3.11/site-packages/iskra/bin/ai_commit
    """
    # Select binary name based on platform
    # Windows requires .exe extension, Unix systems don't
    name = "ai_commit.exe" if os.name == "nt" else "ai_commit"

    # Use importlib.resources to locate file in installed package
    # This is the modern, recommended way to access package data files
    # Works with zip imports, namespace packages, and all installation methods
    return str(files("iskra").joinpath("bin", name))


def main():
    """
        Main entry point for the ai_commit wrapper.

        Locates the bundled binary and executes it using os.execv(),
        which replaces the current Python process with the binary.
        This approach:

        Advantages:
            - No subprocess overhead or complexity
            - Binary becomes PID 1, receives signals directly
            - Proper exit code propagation
            - stdin/stdout/stderr inherited without piping
            - Works seamlessly in shell pipelines

        Error Handling:
            Checks for binary existence before execution to provide
            helpful error message if package is corrupted or incomplete.

        Exit Codes:
            1: Binary not found (packaging error)
            Other: Passed through from binary execution

        Example Usage:
    ```bash
            # As a command (via entry_points in setup.py)
            $ ai-commit --provider ollama --model llama3

            # As a module
            $ python -m iskra.ai_commit --help

            # In a git hook
            $ ai-commit > .git/COMMIT_EDITMSG
    ```

        Note:
            After os.execv(), this Python process no longer exists.
            The binary replaces it entirely in the process table.
    """
    # Locate the binary in the installed package
    binpath = _binary_path()

    # Verify binary exists before attempting execution
    # Provides clear error message if package installation is incomplete
    if not os.path.exists(binpath):
        print(f"FATAL: bundled ai_commit binary not found: {binpath}", file=sys.stderr)
        sys.exit(1)

    # Execute the binary, replacing this Python process
    # os.execv() never returns on success - the binary becomes this process
    #
    # Arguments:
    #   binpath: Path to executable
    #   [binpath, *sys.argv[1:]]: argv array for the new process
    #     - argv[0] is conventionally the program name
    #     - sys.argv[1:] contains all CLI arguments passed to this wrapper
    #
    # Example:
    #   If called as: python -m iskra.ai_commit --model gpt4
    #   Executes as:  /path/to/ai_commit --model gpt4
    os.execv(binpath, [binpath, *sys.argv[1:]])

    # Code after execv() is never reached (unless execv fails)
    # If we reach here, exec failed - Python will raise OSError
