#!/usr/bin/env python3
""""""

import os
import yaml
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime


@dataclass
class RepoInfo:
    """"""

    path: str
    name: str
    remote_url: Optional[str] = None
    default_branch: Optional[str] = None
    last_commit: Optional[str] = None
    last_updated: Optional[str] = None
    active: bool = True

    def to_dict(self) -> Dict:
        """"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "RepoInfo":
        """"""
        return cls(**data)


@dataclass
class GlobalConfig:
    """"""

    # Paths - expanduser() is applied when loading
    base_dir: str = "~/Neoware"
    config_dir: str = "~/.config/iskra"

    # Repository scanning configuration
    max_depth: int = 3  # Prevent infinite recursion
    follow_symlinks: bool = True  # Allow symlinked repos
    exclude_patterns: List[str] = field(default_factory=lambda: [])
    only_patterns: List[str] = field(default_factory=lambda: [])

    # Git operation defaults
    default_branch: str = "main"
    protected_branches: List[str] = field(
        default_factory=lambda: ["main", "master", "production"]
    )
    auto_pull: bool = True  # Sync before committing
    auto_push: bool = True  # Sync after committing

    # Commit message generation
    use_ai_commit: bool = True
    commit_message_style: str = "conventional"  # conventional, simple, descriptive
    ai_provider: str = "ollama"  # ollama, claude, openai

    # Safety mechanisms to prevent accidents
    require_confirmation: bool = True
    require_confirmation_for_protected: bool = True
    dry_run: bool = False  # Preview mode

    # User interface preferences
    show_diff: bool = False  # Show changes before commit
    verbose: bool = False  # Detailed logging
    use_rich_ui: bool = True  # Fancy terminal output

    # Repository filtering for selective processing
    skip_repos_without_changes: bool = False  # Optimization for clean repos
    skip_repos_ahead_of_remote: bool = False  # Skip repos with local-only commits

    # Special file handling options
    handle_gitignore: bool = False  # Auto-update .gitignore
    remove_ds_store: bool = False  # macOS cleanup

    def to_dict(self) -> Dict:
        """"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "GlobalConfig":
        """"""
        # Convert single strings to lists for pattern fields
        # Allows users to write "exclude: '*.tmp'" instead of "exclude: ['*.tmp']"
        if isinstance(data.get("exclude_patterns"), str):
            data["exclude_patterns"] = [data["exclude_patterns"]]
        if isinstance(data.get("only_patterns"), str):
            data["only_patterns"] = [data["only_patterns"]]
        if isinstance(data.get("protected_branches"), str):
            data["protected_branches"] = [data["protected_branches"]]
        return cls(**data)


@dataclass
class RepoConfig:
    """"""

    # Overridable global settings
    # None means "use global config value"
    protected_branches: Optional[List[str]] = None
    use_ai_commit: Optional[bool] = None
    commit_message_style: Optional[str] = None
    require_confirmation: Optional[bool] = None
    auto_pull: Optional[bool] = None
    auto_push: Optional[bool] = None
    exclude_files: Optional[List[str]] = None

    # Repository-specific settings
    # These have no global equivalent
    custom_commit_template: Optional[str] = None
    pre_commit_command: Optional[str] = None  # Run before commit
    post_commit_command: Optional[str] = None  # Run after commit

    def to_dict(self) -> Dict:
        """"""
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict) -> "RepoConfig":
        """"""
        return cls(**data)


class ConfigManager:
    """"""

    def __init__(self, config_dir: Optional[str] = None):
        """"""
        self.config_dir = Path(config_dir or "~/.config/iskra").expanduser()
        self.config_file = self.config_dir / "config.yaml"
        self.repos_file = self.config_dir / "repos.json"
        self.logs_dir = self.config_dir / "logs"

        # Ensure directory structure exists
        # Must happen before loading configs
        self._ensure_structure()

        # Load configurations into memory
        # These are cached for the lifetime of the ConfigManager instance
        self.global_config = self._load_global_config()
        self.tracked_repos = self._load_tracked_repos()

    def _ensure_structure(self):
        """"""
        # Create main config directory and logs subdirectory
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Create default config file if it doesn't exist
        # Uses built-in GlobalConfig defaults
        if not self.config_file.exists():
            self._create_default_config()

        # Create empty repository tracking database
        # Empty dict means no repositories tracked yet
        if not self.repos_file.exists():
            self._save_tracked_repos({})

    def _create_default_config(self):
        """"""
        default_config = GlobalConfig()
        self.save_global_config(default_config)

    def _load_global_config(self) -> GlobalConfig:
        """"""
        try:
            with open(self.config_file, "r") as f:
                data = yaml.safe_load(f) or {}
            return GlobalConfig.from_dict(data)
        except Exception as e:
            print(f"Warning: Could not load config, using defaults: {e}")
            return GlobalConfig()

    def save_global_config(self, config: GlobalConfig):
        """"""
        with open(self.config_file, "w") as f:
            yaml.safe_dump(
                config.to_dict(), f, default_flow_style=False, sort_keys=False
            )

    def _load_tracked_repos(self) -> Dict[str, RepoInfo]:
        """"""
        try:
            with open(self.repos_file, "r") as f:
                data = json.load(f)
            return {path: RepoInfo.from_dict(info) for path, info in data.items()}
        except Exception as e:
            print(f"Warning: Could not load tracked repos: {e}")
            return {}

    def _save_tracked_repos(self, repos: Dict[str, RepoInfo]):
        """"""
        data = {path: info.to_dict() for path, info in repos.items()}
        with open(self.repos_file, "w") as f:
            json.dump(data, f, indent=2)

    def add_repo(self, repo_info: RepoInfo) -> bool:
        """"""
        # Normalize path to absolute canonical form
        # Handles ~, relative paths, and symlinks
        path = str(Path(repo_info.path).expanduser().resolve())

        # Check for duplicate entry
        if path in self.tracked_repos:
            print(f"Repository already tracked: {path}")
            return False

        # Update path in repo_info and set timestamp
        repo_info.path = path
        repo_info.last_updated = datetime.now().isoformat()

        # Add to in-memory cache and persist
        self.tracked_repos[path] = repo_info
        self._save_tracked_repos(self.tracked_repos)
        return True

    def remove_repo(self, path: str) -> bool:
        """"""
        # Normalize path for consistent lookup
        path = str(Path(path).expanduser().resolve())

        # Check if repository is tracked
        if path not in self.tracked_repos:
            print(f"Repository not tracked: {path}")
            return False

        # Remove from in-memory cache and persist
        del self.tracked_repos[path]
        self._save_tracked_repos(self.tracked_repos)
        return True

    def get_repo(self, path: str) -> Optional[RepoInfo]:
        """"""
        path = str(Path(path).expanduser().resolve())
        return self.tracked_repos.get(path)

    def get_all_repos(self, active_only: bool = True) -> List[RepoInfo]:
        """"""
        repos = list(self.tracked_repos.values())
        if active_only:
            repos = [r for r in repos if r.active]
        return repos

    def update_repo(self, path: str, **kwargs):
        """"""
        path = str(Path(path).expanduser().resolve())

        # Verify repository is tracked
        if path not in self.tracked_repos:
            print(f"Repository not tracked: {path}")
            return False

        # Update specified fields
        repo = self.tracked_repos[path]
        for key, value in kwargs.items():
            if hasattr(repo, key):
                setattr(repo, key, value)

        # Update timestamp and persist
        repo.last_updated = datetime.now().isoformat()
        self._save_tracked_repos(self.tracked_repos)
        return True

    def deactivate_repo(self, path: str):
        """"""
        return self.update_repo(path, active=False)

    def activate_repo(self, path: str):
        """"""
        return self.update_repo(path, active=True)

    def load_repo_config(self, repo_path: str) -> Optional[RepoConfig]:
        """"""
        config_path = Path(repo_path) / ".iskra.yaml"

        # Check if per-repo config exists
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
        """"""
        # Create copy of global config to avoid mutations
        merged = GlobalConfig.from_dict(self.global_config.to_dict())

        # Load repository-specific overrides
        repo_config = self.load_repo_config(repo_path)

        # Apply overrides if repo config exists
        if repo_config:
            for key, value in repo_config.to_dict().items():
                # Only override if value is specified (not None)
                # and the field exists in GlobalConfig
                if value is not None and hasattr(merged, key):
                    setattr(merged, key, value)

        return merged

    def get_log_file(self, name: str = "auto-commit") -> Path:
        """"""
        timestamp = datetime.now().strftime("%Y%m%d")
        return self.logs_dir / f"{name}-{timestamp}.log"

    def export_config(self, output_path: str):
        """"""
        # Build complete configuration snapshot
        data = {
            "global_config": self.global_config.to_dict(),
            "tracked_repos": {
                path: info.to_dict() for path, info in self.tracked_repos.items()
            },
        }

        # Write in requested format based on extension
        with open(output_path, "w") as f:
            if output_path.endswith(".json"):
                json.dump(data, f, indent=2)
            else:
                yaml.safe_dump(data, f, default_flow_style=False)

    def import_config(self, input_path: str):
        """"""
        # Load configuration data based on format
        with open(input_path, "r") as f:
            if input_path.endswith(".json"):
                data = json.load(f)
            else:
                data = yaml.safe_load(f)

        # Restore global configuration if present
        if "global_config" in data:
            self.global_config = GlobalConfig.from_dict(data["global_config"])
            self.save_global_config(self.global_config)

        # Restore tracked repositories if present
        if "tracked_repos" in data:
            self.tracked_repos = {
                path: RepoInfo.from_dict(info)
                for path, info in data["tracked_repos"].items()
            }
            self._save_tracked_repos(self.tracked_repos)


# Convenience functions for CLI usage


def get_config() -> ConfigManager:
    """"""
    return ConfigManager()


def init_config(base_dir: Optional[str] = None) -> ConfigManager:
    """"""
    config_manager = ConfigManager()

    if base_dir:
        config_manager.global_config.base_dir = base_dir
        config_manager.save_global_config(config_manager.global_config)

    return config_manager


# Demonstration and testing entry point
if __name__ == "__main__":
    # Example usage for testing and demonstration
    config = get_config()
    print(f"Config directory: {config.config_dir}")
    print(f"Base directory: {config.global_config.base_dir}")
    print(f"Tracked repos: {len(config.tracked_repos)}")
