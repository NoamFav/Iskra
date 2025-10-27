import os, subprocess, pathlib
from setuptools import setup
from setuptools.command.build_py import build_py as _build_py

ROOT = pathlib.Path(__file__).resolve().parent  # python/
GO_CLI_DIR = ROOT / "gocli"
PKG_BIN_DIR = ROOT / "src" / "auto_commit" / "bin"


class build_py(_build_py):
    def run(self):
        self._build_go_binary()
        super().run()

    def _build_go_binary(self):
        PKG_BIN_DIR.mkdir(parents=True, exist_ok=True)
        exe = "ai_commit.exe" if os.name == "nt" else "ai_commit"
        out = PKG_BIN_DIR / exe
        # ensure Go modules on
        env = os.environ.copy()
        env.setdefault("GO111MODULE", "on")
        subprocess.run(
            ["go", "build", "-o", str(out), "./cmd/auto_commit"],
            cwd=str(GO_CLI_DIR),
            check=True,
            env=env,
        )
        if os.name != "nt":
            os.chmod(out, 0o755)


setup(cmdclass={"build_py": build_py})
