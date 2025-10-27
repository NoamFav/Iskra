# python/src/autocommit/ai_commit.py
import os, sys
from importlib.resources import files


def _binary_path():
    # The build step will drop the binary here as "ai_commit" (or ai_commit.exe on Windows)
    name = "ai_commit.exe" if os.name == "nt" else "ai_commit"
    return str(files("autocommit").joinpath("bin", name))


def main():
    binpath = _binary_path()
    if not os.path.exists(binpath):
        print("FATAL: bundled ai_commit binary not found:", binpath, file=sys.stderr)
        sys.exit(1)
    # hand off to the binary
    os.execv(binpath, [binpath] + sys.argv[1:])
