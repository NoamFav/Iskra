import os, subprocess, pathlib
from setuptools import setup, find_packages
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


setup(
    name="Iskra",
    version="1.7.3",
    description="Intelligent multi-repository Git automation tool with AI-powered commit messages",
    long_description=open("README.md").read() if os.path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    author="NoamFav",
    author_email="noamfav@nf-software.com",
    url="https://github.com/NoamFav/Iskra",
    license="Private-token",
    # Package discovery
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    # Include the compiled binary
    package_data={
        "auto_commit": ["bin/*"],
    },
    # Python version requirement
    python_requires=">=3.8",
    # Dependencies
    install_requires=[
        "rich>=13.0.0",
        "pyyaml>=6.0",
        "argcomplete>=2.0.0",
    ],
    # Optional dependencies
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.950",
        ],
    },
    # Entry points for command-line scripts
    entry_points={
        "console_scripts": [
            "iskra=auto_commit.auto_commit:main",
            "pull-repos=auto_commit.pull_repos:main",
            "ai_commit=auto_commit.ai_commit:main",
            "iskra-init=auto_commit.init:main",
        ],
    },
    # Build command customization
    cmdclass={"build_py": build_py},
    # Classifiers for PyPI
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Go",
        "Topic :: Software Development :: Version Control :: Git",
        "Topic :: Software Development :: Build Tools",
    ],
    # Keywords for discoverability
    keywords="git automation commit ai ollama multi-repository devtools iskra",
    # Project URLs
    project_urls={
        "Bug Reports": "https://github.com/NoamFav/Iskra/issues",
        "Source": "https://github.com/NoamFav/Iskra",
        "Documentation": "https://github.com/NoamFav/Iskra#readme",
    },
)
