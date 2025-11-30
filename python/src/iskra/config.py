#!/usr/bin/env python3
"""
Configuration management for Iskra.

Handles global configuration, per-repository overrides, and repository tracking.
Provides a centralized system for managing settings across all Iskra operations
with support for YAML configuration files, JSON repository databases, and
hierarchical configuration merging.

Architecture:
    - GlobalConfig: System-wide default settings
    - RepoConfig: Per-repository overrides
    - RepoInfo: Tracked repository metadata
    - ConfigManager: Orchestrates loading, saving, and merging

Configuration Hierarchy (highest to lowest priority):
    1. Per-repository .iskra.yaml file
    2. Global configuration (~/.config/iskra/config.yaml)
    3. Built-in defaults
"""

import os
import yaml
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime


@dataclass
class RepoInfo:
    """
    Information about a tracked repository.

    Stores metadata about repositories being managed by Iskra,
    including git information and tracking status. This allows
    Iskra to work with a known set of repositories rather than
    scanning the filesystem on every run.

    Attributes:
        path: Absolute path to the repository
        name: Display name (typically directory name)
        remote_url: Git remote origin URL (if available)
        default_branch: Main branch name (main, master, etc.)
        last_commit: SHA-1 hash of last known commit
        last_updated: ISO timestamp of last Iskra operation
        active: Whether this repo should be processed (soft delete)

    Note:
        Paths are always stored as absolute paths after resolution
        to avoid ambiguity with relative paths and symlinks.
    """

    path: str
    name: str
    remote_url: Optional[str] = None
    default_branch: Optional[str] = None
    last_commit: Optional[str] = None
    last_updated: Optional[str] = None
    active: bool = True

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "RepoInfo":
        """Create RepoInfo from dictionary (JSON deserialization)."""
        return cls(**data)


@dataclass
class GlobalConfig:
    """
    Global configuration settings for Iskra.

    Defines system-wide defaults that apply to all repositories
    unless overridden by per-repository configuration. Settings
    are organized into logical groups for clarity.

    Path Settings:
        base_dir: Root directory for repository scanning
        config_dir: Location of Iskra configuration files

    Scanning Settings:
        max_depth: How deep to recurse when scanning for repos
        follow_symlinks: Whether to follow symbolic links during scan
        exclude_patterns: Glob patterns for repos to skip
        only_patterns: Glob patterns for repos to include (whitelist)

    Git Settings:
        default_branch: Assumed main branch for new repos
        protected_branches: Branches requiring extra confirmation
        auto_pull: Pull before committing
        auto_push: Push after committing

    Commit Settings:
        use_ai_commit: Generate commit messages with AI
        commit_message_style: Format style (conventional, simple, descriptive)
        ai_provider: AI service to use (ollama, claude, openai)

    Safety Settings:
        require_confirmation: Prompt before operations
        require_confirmation_for_protected: Extra confirmation for protected branches
        dry_run: Show what would happen without making changes

    UI Settings:
        show_diff: Display git diff before committing
        verbose: Enable detailed output
        use_rich_ui: Enable Rich terminal formatting

    Filter Settings:
        skip_repos_without_changes: Skip repos with clean working directory
        skip_repos_ahead_of_remote: Skip repos with unpushed commits

    Special Handling:
        handle_gitignore: Automatically manage .gitignore files
        remove_ds_store: Remove .DS_Store files before committing
    """

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
        """Convert to dictionary for YAML serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "GlobalConfig":
        """
        Create GlobalConfig from dictionary (YAML deserialization).

        Handles type coercion for backwards compatibility - converts
        single string values to lists where lists are expected.

        Args:
            data: Dictionary from YAML file

        Returns:
            Populated GlobalConfig instance
        """
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
    """
        Per-repository configuration overrides.

        Allows individual repositories to override global settings by
        placing a .iskra.yaml file in the repository root. All fields
        are optional - only specified values override global config.

        Override Fields:
            Protected branch lists, AI settings, confirmation requirements,
            auto-pull/push behavior, file exclusions

        Repo-Specific Fields:
            custom_commit_template: Custom template for this repo
            pre_commit_command: Shell command to run before committing
            post_commit_command: Shell command to run after committing

        Example .iskra.yaml:
    ```yaml
            use_ai_commit: false
            require_confirmation: false
            pre_commit_command: "npm test"
            exclude_files:
              - "dist/"
              - "*.log"
    ```

        Note:
            Only non-None values are serialized to avoid clutter in
            per-repository config files.
    """

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
        """
        Convert to dictionary, excluding None values.

        Returns only populated fields to keep per-repo config files
        minimal and readable. Empty fields inherit from global config.
        """
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict) -> "RepoConfig":
        """Create RepoConfig from dictionary (YAML deserialization)."""
        return cls(**data)


class ConfigManager:
    """
        Manages all configuration for Iskra.

        Central orchestrator for configuration management, handling:
        - Loading and saving global configuration (YAML)
        - Tracking repository metadata (JSON)
        - Merging global and per-repo configurations
        - Managing configuration directory structure
        - Providing logging infrastructure

        Directory Structure:
            ~/.config/iskra/
            ├── config.yaml          # Global configuration
            ├── repos.json           # Tracked repository database
            └── logs/                # Operation logs
                ├── iskra-20240101.log
                └── auto-commit-20240101.log

        Usage:
    ```python
            config_manager = ConfigManager()
            config = config_manager.global_config
            repos = config_manager.get_all_repos()
            merged_config = config_manager.merge_config("/path/to/repo")
    ```

        Thread Safety:
            This class is not thread-safe. File operations are not locked.
            Concurrent access may result in data loss or corruption.
    """

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize configuration manager.

        Args:
            config_dir: Override default config directory (~/.config/iskra)
                       Useful for testing or custom installations

        Side Effects:
            - Creates config directory structure if missing
            - Creates default config.yaml if missing
            - Creates empty repos.json if missing
            - Loads all configuration into memory
        """
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
        """
        Create configuration directory structure if it doesn't exist.

        Initializes the Iskra configuration environment with default
        files and directory structure. Safe to call multiple times -
        existing files are not overwritten.

        Side Effects:
            - Creates ~/.config/iskra/ directory
            - Creates logs/ subdirectory
            - Creates default config.yaml if missing
            - Creates empty repos.json if missing
        """
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
        """
        Create a default configuration file with sensible defaults.

        Uses GlobalConfig dataclass defaults to generate initial
        config.yaml. This provides a template users can customize.
        """
        default_config = GlobalConfig()
        self.save_global_config(default_config)

    def _load_global_config(self) -> GlobalConfig:
        """
        Load global configuration from YAML file.

        Returns:
            GlobalConfig instance populated from config.yaml
            On error, returns default GlobalConfig with warning

        Error Handling:
            Fails gracefully with defaults if file is missing or corrupt.
            Warns user but doesn't crash - allows Iskra to continue.
        """
        try:
            with open(self.config_file, "r") as f:
                data = yaml.safe_load(f) or {}
            return GlobalConfig.from_dict(data)
        except Exception as e:
            print(f"Warning: Could not load config, using defaults: {e}")
            return GlobalConfig()

    def save_global_config(self, config: GlobalConfig):
        """
        Save global configuration to YAML file.

        Args:
            config: GlobalConfig instance to persist

        Side Effects:
            Overwrites config.yaml with new settings

        Note:
            Uses safe_dump for security (prevents code execution)
            Disables flow style for readability (uses block style)
            Preserves key order for predictable diffs
        """
        with open(self.config_file, "w") as f:
            yaml.safe_dump(
                config.to_dict(), f, default_flow_style=False, sort_keys=False
            )

    def _load_tracked_repos(self) -> Dict[str, RepoInfo]:
        """
        Load tracked repositories from JSON file.

        Returns:
            Dictionary mapping absolute paths to RepoInfo objects
            On error, returns empty dict with warning

        Error Handling:
            Fails gracefully if file is missing or corrupt.
            Returns empty dict to allow Iskra to continue.
        """
        try:
            with open(self.repos_file, "r") as f:
                data = json.load(f)
            return {path: RepoInfo.from_dict(info) for path, info in data.items()}
        except Exception as e:
            print(f"Warning: Could not load tracked repos: {e}")
            return {}

    def _save_tracked_repos(self, repos: Dict[str, RepoInfo]):
        """
        Save tracked repositories to JSON file.

        Args:
            repos: Dictionary mapping paths to RepoInfo objects

        Side Effects:
            Overwrites repos.json with current tracking database

        Note:
            Uses indent=2 for human-readable JSON formatting
        """
        data = {path: info.to_dict() for path, info in repos.items()}
        with open(self.repos_file, "w") as f:
            json.dump(data, f, indent=2)

    def add_repo(self, repo_info: RepoInfo) -> bool:
        """
        Add a repository to tracking database.

        Args:
            repo_info: Repository information to track

        Returns:
            True if repository was added
            False if repository was already tracked

        Side Effects:
            - Resolves and normalizes repository path
            - Sets last_updated timestamp
            - Persists to repos.json

        Note:
            Path is always resolved to absolute canonical path
            to prevent duplicate entries from different path formats.
        """
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
        """
        Remove a repository from tracking.

        Args:
            path: Path to repository to untrack

        Returns:
            True if repository was removed
            False if repository was not tracked

        Side Effects:
            Persists change to repos.json

        Note:
            This only removes from tracking - does not delete
            the actual repository from disk.
        """
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
        """
        Get information about a tracked repository.

        Args:
            path: Path to repository

        Returns:
            RepoInfo if repository is tracked, None otherwise
        """
        path = str(Path(path).expanduser().resolve())
        return self.tracked_repos.get(path)

    def get_all_repos(self, active_only: bool = True) -> List[RepoInfo]:
        """
        Get all tracked repositories.

        Args:
            active_only: If True, only return active repositories
                        If False, include deactivated repositories

        Returns:
            List of RepoInfo objects

        Note:
            Deactivated repositories are soft-deleted (active=False)
            and can be reactivated without re-adding metadata.
        """
        repos = list(self.tracked_repos.values())
        if active_only:
            repos = [r for r in repos if r.active]
        return repos

    def update_repo(self, path: str, **kwargs):
        """
                Update repository metadata.

                Args:
                    path: Path to repository
                    **kwargs: Fields to update (must be valid RepoInfo attributes)

                Returns:
                    True if updated successfully
                    False if repository not tracked

                Side Effects:
                    - Updates last_updated timestamp
                    - Persists changes to repos.json

                Example:
        ```python
                    config_manager.update_repo(
                        "/path/to/repo",
                        last_commit="abc123",
                        default_branch="main"
                    )
        ```
        """
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
        """
        Mark a repository as inactive (soft delete).

        Inactive repositories are kept in the database but skipped
        during processing. Useful for temporarily disabling repos
        without losing their metadata.

        Args:
            path: Path to repository

        Returns:
            True if deactivated, False if not tracked
        """
        return self.update_repo(path, active=False)

    def activate_repo(self, path: str):
        """
        Mark a repository as active.

        Re-enables a previously deactivated repository.

        Args:
            path: Path to repository

        Returns:
            True if activated, False if not tracked
        """
        return self.update_repo(path, active=True)

    def load_repo_config(self, repo_path: str) -> Optional[RepoConfig]:
        """
        Load per-repository configuration if it exists.

        Looks for .iskra.yaml in the repository root and loads
        it as a RepoConfig object for merging with global config.

        Args:
            repo_path: Path to repository

        Returns:
            RepoConfig if .iskra.yaml exists and is valid
            None if no config file or parsing failed

        Error Handling:
            Logs warning but returns None on parse errors.
            Allows operation to continue with global config.
        """
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
        """
        Merge global config with repository-specific overrides.

        Creates a new GlobalConfig with values from the global config,
        then applies any overrides from the repository's .iskra.yaml.

        Args:
            repo_path: Path to repository

        Returns:
            Merged GlobalConfig with repo-specific overrides applied

        Merge Strategy:
            1. Start with copy of global config
            2. Load .iskra.yaml if it exists
            3. Override global values with non-None repo values

        Example:
            If global has use_ai_commit=True and repo has use_ai_commit=False,
            the merged config will have use_ai_commit=False for that repo.

        Note:
            Returns a new object - does not modify global_config.
        """
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
        """
        Get path to a log file with date-based naming.

        Args:
            name: Base name for log file (e.g., "auto-commit", "iskra")

        Returns:
            Path to log file: logs/{name}-{YYYYMMDD}.log

        Note:
            Creates one log file per day for each operation type.
            Allows easy log rotation and historical analysis.

        Example:
            >>> config.get_log_file("iskra")
            Path("/home/user/.config/iskra/logs/iskra-20240101.log")
        """
        timestamp = datetime.now().strftime("%Y%m%d")
        return self.logs_dir / f"{name}-{timestamp}.log"

    def export_config(self, output_path: str):
        """
                Export current configuration to a file.

                Creates a complete backup of both global config and
                tracked repository database. Useful for:
                - Backing up configuration
                - Sharing setup across machines
                - Version controlling settings

                Args:
                    output_path: Destination file path (.json or .yaml)

                Format Detection:
                    - .json extension → JSON format
                    - Anything else → YAML format

                Example:
        ```python
                    config.export_config("backup.yaml")
                    config.export_config("iskra-config-2024.json")
        ```
        """
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
        """
        Import configuration from a file.

        Restores configuration from an export file, replacing
        current global config and tracked repositories.

        Args:
            input_path: Source file path (.json or .yaml)

        Side Effects:
            - Overwrites global config
            - Replaces entire tracked repository database
            - Persists changes to disk

        Warning:
            This is a destructive operation - existing configuration
            and tracked repos are replaced, not merged.

        Format Detection:
            - .json extension → Parse as JSON
            - Anything else → Parse as YAML
        """
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
    """
        Get the global config manager instance.

        Convenience function for CLI scripts that need quick access
        to configuration without manual initialization.

        Returns:
            ConfigManager instance using default paths

        Example:
    ```python
            from iskra.config import get_config

            config = get_config()
            print(config.global_config.base_dir)
    ```
    """
    return ConfigManager()


def init_config(base_dir: Optional[str] = None) -> ConfigManager:
    """
        Initialize configuration with optional base directory override.

        Creates or loads configuration, optionally setting a custom
        base directory. Useful for first-time setup or migrations.

        Args:
            base_dir: Optional base directory to set in global config

        Returns:
            ConfigManager instance with updated configuration

        Side Effects:
            If base_dir is provided, saves updated global config to disk

        Example:
    ```python
            from iskra.config import init_config

            config = init_config(base_dir="~/projects")
    ```
    """
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
