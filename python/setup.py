# python/setup.py
import os, sys, subprocess, pathlib
from setuptools import setup
from setuptools.command.build_py import build_py as _build_py

ROOT = pathlib.Path(__file__).resolve().parent.parent  # repo root
GO_CMD_DIR = ROOT / "cmd" / "auto_commit"
PKG_BIN_DIR = pathlib.Path(__file__).resolve().parent / "src" / "autocommit" / "bin"


class build_py(_build_py):
    def run(self):
        self._build_go_binary()
        super().run()

    def _build_go_binary(self):
        # Ensure bin dir exists
        PKG_BIN_DIR.mkdir(parents=True, exist_ok=True)

        exe = "ai_commit.exe" if os.name == "nt" else "ai_commit"
        out = PKG_BIN_DIR / exe

        # Build Go binary
        env = os.environ.copy()
        # You can pin GOOS/GOARCH here if you want; otherwise build for host
        cmd = ["go", "build", "-o", str(out), "./cmd/auto_commit"]
        try:
            subprocess.run(cmd, cwd=ROOT, check=True, env=env)
        except FileNotFoundError:
            print("Go toolchain not found. Please install Go.", file=sys.stderr)
            sys.exit(1)
        except subprocess.CalledProcessError as e:
            print("Go build failed:", e, file=sys.stderr)
            sys.exit(e.returncode)

        # make executable on POSIX
        if os.name != "nt":
            out.chmod(0o755)


setup(cmdclass={"build_py": build_py})
