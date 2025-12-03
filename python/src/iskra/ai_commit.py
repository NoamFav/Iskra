""""""

import os
import sys
from importlib.resources import files


def _binary_path():
    """"""
    # Select binary name based on platform
    # Windows requires .exe extension, Unix systems don't
    name = "ai_commit.exe" if os.name == "nt" else "ai_commit"

    # Use importlib.resources to locate file in installed package
    # This is the modern, recommended way to access package data files
    # Works with zip imports, namespace packages, and all installation methods
    return str(files("iskra").joinpath("bin", name))


def main():
    """"""
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
