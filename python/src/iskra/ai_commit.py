import os
import sys
from importlib.resources import files


def _binary_path():

    name = "ai_commit.exe" if os.name == "nt" else "ai_commit"

    return str(files("iskra").joinpath("bin", name))


def main():

    binpath = _binary_path()

    if not os.path.exists(binpath):
        print(
            f"FATAL: bundled ai_commit binary not found: {binpath}",
            file=sys.stderr,
        )
        sys.exit(1)

    os.execv(binpath, [binpath, *sys.argv[1:]])
