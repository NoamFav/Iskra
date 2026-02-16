"""
Config management. Because hardcoding paths is for peasants.

Lives in ~/.config/iskra/ like a civilized tool. Stores your preferences,
tracks your repos, and remembers what you like. Unlike your ex.
"""

import yaml
import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime


@dataclass
class RepoInfo:
    """Info about a tracked repo. Path, name, the usual suspects."""

    path: str
    name: str
    remote_url: Optional[str] = None
    default_branch: Optional[str] = None
    last_commit: Optional[str] = None
    last_updated: Optional[str] = None
    active: bool = True

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "RepoInfo":
        return cls(**data)


@dataclass
class Theme:
    """Theme of the ui, pretty stars and fancy doo da"""

    theme: str = "default"
    icons_enabled: bool = True

    # Optional override in case themes are not enough,
    # or too much if you hate sparkles
    colors: Optional[dict[str, str]] = None

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "Theme":
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)


@dataclass
class GlobalConfig:
    """
    All the settings. There's a lot. Like way too many.

    Directory stuff, git operations, AI provider config, safety nets,
    display options, macos garbage handling... it's all here.
    I don't even remember adding half of these wtf.
    """

    # where stuff lives
    base_dir: str = "~/Neoware"
    config_dir: str = "~/.config/iskra"
    max_depth: int = 3
    follow_symlinks: bool = True
    exclude_patterns: List[str] = field(default_factory=lambda: [])
    only_patterns: List[str] = field(default_factory=lambda: [])

    # git stuff
    default_branch: str = "main"
    protected_branches: List[str] = field(
        default_factory=lambda: ["main", "master", "production"]
    )
    auto_pull: bool = True
    auto_push: bool = True
    auto_stash: bool = False

    # AI settings - the fun part
    use_ai_commit: bool = True
    commit_message_style: str = "conventional"
    ai_provider: str = "ollama"  # ollama, openai, claude
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    claude_api_key: Optional[str] = None
    claude_model: str = "claude-sonnet-4-20250514"

    # safety stuff for the paranoid
    require_confirmation: bool = True
    require_confirmation_for_protected: bool = True
    dry_run: bool = False
    check_ssh_keys: bool = True
    warn_conflicts: bool = True

    # pretty output
    show_diff: bool = False
    verbose: bool = False
    use_rich_ui: bool = True

    # filtering
    skip_repos_without_changes: bool = False
    skip_repos_ahead_of_remote: bool = False

    # macos is special (not in a good way)
    handle_gitignore: bool = False
    remove_ds_store: bool = False

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "GlobalConfig":
        """Load from dict. Fixes people who put strings instead of lists."""
        if isinstance(data.get("exclude_patterns"), str):
            data["exclude_patterns"] = [data["exclude_patterns"]]
        if isinstance(data.get("only_patterns"), str):
            data["only_patterns"] = [data["only_patterns"]]
        if isinstance(data.get("protected_branches"), str):
            data["protected_branches"] = [data["protected_branches"]]

        # don't blow up on unknown keys
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}

        return cls(**filtered_data)


@dataclass
class RepoConfig:
    """
    Per-repo overrides. Put a .iskra.yaml in your repo root.
    Whatever you set here beats the global config.
    """

    protected_branches: Optional[List[str]] = None
    use_ai_commit: Optional[bool] = None
    commit_message_style: Optional[str] = None
    require_confirmation: Optional[bool] = None
    auto_pull: Optional[bool] = None
    auto_push: Optional[bool] = None
    exclude_files: Optional[List[str]] = None

    # hooks - run commands before/after commit
    custom_commit_template: Optional[str] = None
    pre_commit_command: Optional[str] = None
    post_commit_command: Optional[str] = None

    def to_dict(self) -> Dict:
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict) -> "RepoConfig":
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)


class ConfigManager:
    """
    The config boss. Loads, saves, merges configs.

    ~/.config/iskra/
    ├── config.yaml    <- your settings
    ├── repos.json     <- tracked repos
    └── logs/          <- what happened when
    """

    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir or "~/.config/iskra").expanduser()
        self.config_file = self.config_dir / "config.yaml"
        self.repos_file = self.config_dir / "repos.json"
        self.logs_dir = self.config_dir / "logs"
        self.ui_file = self.config_dir / "ui.yaml"

        self._ensure_structure()

        self.global_config = self._load_global_config()
        self.tracked_repos = self._load_tracked_repos()
        self.ui_config = self.load_ui_config()

    def _ensure_structure(self) -> None:
        """Create the dirs if they don't exist. Not rocket science."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        if not self.config_file.exists():
            self._create_default_config()

        if not self.repos_file.exists():
            self._save_tracked_repos({})

    def _create_default_config(self) -> None:
        default_config = GlobalConfig()
        self.save_global_config(default_config)

    def _load_global_config(self) -> GlobalConfig:
        """Load config from yaml. Falls back to defaults if it's fucked."""
        try:
            with open(self.config_file, "r") as f:
                data = yaml.safe_load(f) or {}
            return GlobalConfig.from_dict(data)
        except Exception as e:
            print(f"Warning: Could not load config, using defaults: {e}")
            return GlobalConfig()

    def save_global_config(self, config: GlobalConfig) -> None:
        with open(self.config_file, "w") as f:
            yaml.safe_dump(
                config.to_dict(), f, default_flow_style=False, sort_keys=False
            )

    def _load_tracked_repos(self) -> Dict[str, RepoInfo]:
        try:
            with open(self.repos_file, "r") as f:
                data = json.load(f)
            return {path: RepoInfo.from_dict(info) for path, info in data.items()}
        except Exception as e:
            print(f"Warning: Could not load tracked repos: {e}")
            return {}

    def load_ui_config(self) -> Theme:
        """Load ui.yaml if it exists. Silent fallback to defaults."""
        if not self.ui_file.exists():
            return Theme()
        try:
            with open(self.ui_file, "r") as f:
                data = yaml.safe_load(f) or {}
            return Theme.from_dict(data)
        except Exception as e:
            print(f"Warning: Could not load ui config: {e}")
            return Theme()

    def _save_tracked_repos(self, repos: Dict[str, RepoInfo]) -> None:
        data = {path: info.to_dict() for path, info in repos.items()}
        with open(self.repos_file, "w") as f:
            json.dump(data, f, indent=2)

    def add_repo(self, repo_info: RepoInfo) -> bool:
        """Track a repo. Returns False if already tracked (duh)."""
        path = str(Path(repo_info.path).expanduser().resolve())

        if path in self.tracked_repos:
            print(f"Repository already tracked: {path}")
            return False

        repo_info.path = path
        repo_info.last_updated = datetime.now().isoformat()

        self.tracked_repos[path] = repo_info
        self._save_tracked_repos(self.tracked_repos)
        return True

    def remove_repo(self, path: str) -> bool:
        """Untrack a repo. Returns False if wasn't tracked anyway."""
        path = str(Path(path).expanduser().resolve())

        if path not in self.tracked_repos:
            print(f"Repository not tracked: {path}")
            return False

        del self.tracked_repos[path]
        self._save_tracked_repos(self.tracked_repos)
        return True

    def get_repo(self, path: str) -> Optional[RepoInfo]:
        path = str(Path(path).expanduser().resolve())
        return self.tracked_repos.get(path)

    def get_all_repos(self, active_only: bool = True) -> List[RepoInfo]:
        repos = list(self.tracked_repos.values())
        if active_only:
            repos = [r for r in repos if r.active]
        return repos

    def update_repo(self, path: str, **kwargs) -> bool:
        """Update repo info. Pass whatever fields you want to change."""
        path = str(Path(path).expanduser().resolve())

        if path not in self.tracked_repos:
            print(f"Repository not tracked: {path}")
            return False

        repo = self.tracked_repos[path]
        for key, value in kwargs.items():
            if hasattr(repo, key):
                setattr(repo, key, value)

        repo.last_updated = datetime.now().isoformat()
        self._save_tracked_repos(self.tracked_repos)
        return True

    def deactivate_repo(self, path: str) -> bool:
        """Turn off a repo without removing it."""
        return self.update_repo(path, active=False)

    def activate_repo(self, path: str) -> bool:
        """Turn a repo back on."""
        return self.update_repo(path, active=True)

    def load_repo_config(self, repo_path: str) -> Optional[RepoConfig]:
        """Load .iskra.yaml from repo root if it exists."""
        config_path = Path(repo_path) / ".iskra.yaml"

        if not config_path.exists():
            return None

        try:
            with open(config_path, "r") as f:
                data = yaml.safe_load(f) or {}
            return RepoConfig.from_dict(data)
        except Exception as e:
            print(f"Warning: Could not load repo config from {config_path}: {e}")
            return None

    def merge_config(self, repo_path: str) -> GlobalConfig:
        """
        Merge global config with per-repo overrides.
        Repo config wins where it's defined.
        Don't ask me the priority order I wrote this at 3am.
        """
        merged = GlobalConfig.from_dict(self.global_config.to_dict())

        repo_config = self.load_repo_config(repo_path)
        if repo_config:
            for key, value in repo_config.to_dict().items():
                if value is not None and hasattr(merged, key):
                    setattr(merged, key, value)

        return merged

    def get_log_file(self, name: str = "auto-commit") -> Path:
        """Get today's log file path."""
        timestamp = datetime.now().strftime("%Y%m%d")
        return self.logs_dir / f"{name}-{timestamp}.log"

    def export_config(self, output_path: str) -> None:
        """Dump everything to a file. JSON or YAML based on extension."""
        data = {
            "global_config": self.global_config.to_dict(),
            "tracked_repos": {
                path: info.to_dict() for path, info in self.tracked_repos.items()
            },
        }

        with open(output_path, "w") as f:
            if output_path.endswith(".json"):
                json.dump(data, f, indent=2)
            else:
                yaml.safe_dump(data, f, default_flow_style=False)

    def import_config(self, input_path: str) -> None:
        """Load config from a file. JSON or YAML."""
        with open(input_path, "r") as f:
            if input_path.endswith(".json"):
                data = json.load(f)
            else:
                data = yaml.safe_load(f)

        if "global_config" in data:
            self.global_config = GlobalConfig.from_dict(data["global_config"])
            self.save_global_config(self.global_config)

        if "tracked_repos" in data:
            self.tracked_repos = {
                path: RepoInfo.from_dict(info)
                for path, info in data["tracked_repos"].items()
            }
            self._save_tracked_repos(self.tracked_repos)


# shortcuts
def get_config() -> ConfigManager:
    """Just get a ConfigManager. Nothing fancy."""
    return ConfigManager()


def init_config(base_dir: Optional[str] = None) -> ConfigManager:
    """Init config, optionally set base dir."""
    config_manager = ConfigManager()
    if base_dir:
        config_manager.global_config.base_dir = base_dir
        config_manager.save_global_config(config_manager.global_config)
    return config_manager


if __name__ == "__main__":
    config = get_config()
    print(f"Config directory: {config.config_dir}")
    print(f"Base directory: {config.global_config.base_dir}")
    print(f"Tracked repos: {len(config.tracked_repos)}")
    print(f"AI provider: {config.global_config.ai_provider}")
