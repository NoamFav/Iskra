"""
Iskra Python Library - Main API Interface
Provides a clean programmatic interface for Zvezda and other tools.
"""

from __future__ import annotations
import os
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from iskra.config import ConfigManager, RepoInfo
from iskra.core.git_operations import (
    get_current_branch,
    git_pull,
    git_add_all,
    git_status_porcelain,
    git_commit,
    git_push,
    generate_commit_message,
)


# ============================================================================
# Data Classes for API
# ============================================================================


@dataclass
class ChangesSummary:
    """Summary of repository changes"""

    uncommitted: int = 0
    staged: int = 0
    untracked: int = 0
    modified_files: List[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return (self.uncommitted + self.staged + self.untracked) > 0


@dataclass
class RemoteStatus:
    """Remote repository status"""

    url: str = ""
    ahead: int = 0
    behind: int = 0

    @property
    def in_sync(self) -> bool:
        return self.ahead == 0 and self.behind == 0


@dataclass
class CommitInfo:
    """Last commit information"""

    hash: str = ""
    message: str = ""
    author: str = ""
    timestamp: str = ""


@dataclass
class RepoStatus:
    """Complete repository status"""

    path: str
    name: str
    branch: str
    changes: ChangesSummary
    remote: RemoteStatus
    last_commit: CommitInfo
    is_valid_repo: bool = True
    errors: List[str] = field(default_factory=list)


@dataclass
class Operation:
    """Single git operation result"""

    type: str  # pull, commit, push
    success: bool
    message: str = ""
    duration: float = 0.0


@dataclass
class ProcessResult:
    """Result of processing a repository"""

    success: bool
    repo_path: str
    operations: List[Operation] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    duration: float = 0.0


@dataclass
class BatchResult:
    """Result of batch repository processing"""

    total: int
    successful: int
    failed: int
    results: List[ProcessResult] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Repository validation result"""

    is_valid: bool
    is_git_repo: bool
    has_remote: bool
    issues: List[str] = field(default_factory=list)


# ============================================================================
# Main API Class
# ============================================================================


class IskraManager:
    """
    Main API interface for Iskra - Git repository automation

    Usage:
        manager = IskraManager()
        repos = manager.get_all_repos()
        status = manager.get_repo_status("/path/to/repo")
        result = manager.process_repo("/path/to/repo", pull=True, commit=True)
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize IskraManager

        Args:
            config_path: Optional path to config directory.
                        Defaults to ~/.config/iskra
        """
        self.config_manager = ConfigManager(config_path)
        self.global_config = self.config_manager.global_config

    # ========================================================================
    # Query Methods
    # ========================================================================

    def get_all_repos(self, active_only: bool = True) -> List[RepoInfo]:
        """
        Get all tracked repositories

        Args:
            active_only: Only return active repositories

        Returns:
            List of RepoInfo objects
        """
        return self.config_manager.get_all_repos(active_only=active_only)

    def get_repo_status(self, repo_path: str) -> RepoStatus:
        """
        Get detailed status of a repository

        Args:
            repo_path: Path to repository

        Returns:
            RepoStatus object with complete repository state
        """
        repo_path = str(Path(repo_path).expanduser().resolve())
        orig_cwd = os.getcwd()

        try:
            os.chdir(repo_path)

            # Get branch
            branch = get_current_branch()

            # Get changes
            status_output = git_status_porcelain()
            changes = self._parse_status(status_output)

            # Get remote info
            remote = self._get_remote_status(repo_path)

            # Get last commit
            commit = self._get_commit_info()

            return RepoStatus(
                path=repo_path,
                name=os.path.basename(repo_path),
                branch=branch,
                changes=changes,
                remote=remote,
                last_commit=commit,
                is_valid_repo=True,
            )

        except Exception as e:
            return RepoStatus(
                path=repo_path,
                name=os.path.basename(repo_path),
                branch="",
                changes=ChangesSummary(),
                remote=RemoteStatus(),
                last_commit=CommitInfo(),
                is_valid_repo=False,
                errors=[str(e)],
            )
        finally:
            os.chdir(orig_cwd)

    def filter_repos(
        self,
        has_changes: Optional[bool] = None,
        behind_remote: Optional[bool] = None,
        branch: Optional[str] = None,
        pattern: Optional[str] = None,
    ) -> List[RepoInfo]:
        """
        Filter repositories by criteria

        Args:
            has_changes: Filter repos with uncommitted changes
            behind_remote: Filter repos behind remote
            branch: Filter by branch name
            pattern: Filter by name pattern (glob)

        Returns:
            Filtered list of RepoInfo objects
        """
        repos = self.get_all_repos(active_only=True)
        filtered = []

        for repo in repos:
            # Apply filters
            if pattern:
                import fnmatch

                if not fnmatch.fnmatch(repo.name, pattern):
                    continue

            if has_changes is not None or behind_remote is not None:
                status = self.get_repo_status(repo.path)

                if has_changes is not None:
                    if status.changes.has_changes != has_changes:
                        continue

                if behind_remote is not None:
                    if (status.remote.behind > 0) != behind_remote:
                        continue

            if branch is not None:
                status = self.get_repo_status(repo.path)
                if status.branch != branch:
                    continue

            filtered.append(repo)

        return filtered

    # ========================================================================
    # Action Methods
    # ========================================================================

    def process_repo(
        self,
        repo_path: str,
        pull: bool = False,
        commit: bool = False,
        push: bool = False,
        commit_message: Optional[str] = None,
        dry_run: bool = False,
    ) -> ProcessResult:
        """
        Process a single repository

        Args:
            repo_path: Path to repository
            pull: Pull latest changes
            commit: Commit changes
            push: Push to remote
            commit_message: Custom commit message (or auto-generate)
            dry_run: Show what would be done without doing it

        Returns:
            ProcessResult with operation details
        """
        import time

        repo_path = str(Path(repo_path).expanduser().resolve())
        start_time = time.time()
        orig_cwd = os.getcwd()

        operations = []
        errors = []

        try:
            os.chdir(repo_path)

            # Pull
            if pull:
                try:
                    if not dry_run:
                        result = git_pull()
                        operations.append(
                            Operation(
                                type="pull",
                                success=True,
                                message=result.stdout.strip(),
                            )
                        )
                    else:
                        operations.append(
                            Operation(
                                type="pull",
                                success=True,
                                message="[DRY RUN] Would pull changes",
                            )
                        )
                except Exception as e:
                    errors.append(f"Pull failed: {e}")
                    operations.append(
                        Operation(
                            type="pull",
                            success=False,
                            message=str(e),
                        )
                    )

            # Commit
            if commit:
                try:
                    status = git_status_porcelain()
                    if status.strip():
                        if not dry_run:
                            git_add_all()
                            msg = commit_message or generate_commit_message()
                            git_commit(msg)
                            operations.append(
                                Operation(
                                    type="commit",
                                    success=True,
                                    message=f"Committed: {msg}",
                                )
                            )
                        else:
                            operations.append(
                                Operation(
                                    type="commit",
                                    success=True,
                                    message="[DRY RUN] Would commit changes",
                                )
                            )
                    else:
                        operations.append(
                            Operation(
                                type="commit",
                                success=True,
                                message="No changes to commit",
                            )
                        )
                except Exception as e:
                    errors.append(f"Commit failed: {e}")
                    operations.append(
                        Operation(
                            type="commit",
                            success=False,
                            message=str(e),
                        )
                    )

            # Push
            if push:
                try:
                    if not dry_run:
                        result = git_push()
                        operations.append(
                            Operation(
                                type="push",
                                success=True,
                                message="Pushed to remote",
                            )
                        )
                    else:
                        operations.append(
                            Operation(
                                type="push",
                                success=True,
                                message="[DRY RUN] Would push to remote",
                            )
                        )
                except Exception as e:
                    errors.append(f"Push failed: {e}")
                    operations.append(
                        Operation(
                            type="push",
                            success=False,
                            message=str(e),
                        )
                    )

            duration = time.time() - start_time

            return ProcessResult(
                success=len(errors) == 0,
                repo_path=repo_path,
                operations=operations,
                errors=errors,
                duration=duration,
            )

        except Exception as e:
            errors.append(str(e))
            return ProcessResult(
                success=False,
                repo_path=repo_path,
                operations=operations,
                errors=errors,
                duration=time.time() - start_time,
            )
        finally:
            os.chdir(orig_cwd)

    def process_all(
        self,
        pull: bool = False,
        commit: bool = False,
        push: bool = False,
        filters: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
    ) -> BatchResult:
        """
        Process multiple repositories

        Args:
            pull: Pull latest changes
            commit: Commit changes
            push: Push to remote
            filters: Filter criteria (see filter_repos)
            dry_run: Show what would be done without doing it

        Returns:
            BatchResult with all operation results
        """
        # Get repos to process
        if filters:
            repos = self.filter_repos(**filters)
        else:
            repos = self.get_all_repos(active_only=True)

        results = []
        successful = 0
        failed = 0

        for repo in repos:
            result = self.process_repo(
                repo.path,
                pull=pull,
                commit=commit,
                push=push,
                dry_run=dry_run,
            )
            results.append(result)

            if result.success:
                successful += 1
            else:
                failed += 1

        return BatchResult(
            total=len(repos),
            successful=successful,
            failed=failed,
            results=results,
        )

    def pull_repo(self, repo_path: str) -> ProcessResult:
        """Pull latest changes from remote"""
        return self.process_repo(repo_path, pull=True)

    def commit_repo(self, repo_path: str, message: str) -> ProcessResult:
        """Commit changes with message"""
        return self.process_repo(repo_path, commit=True, commit_message=message)

    def push_repo(self, repo_path: str) -> ProcessResult:
        """Push changes to remote"""
        return self.process_repo(repo_path, push=True)

    # ========================================================================
    # Config Methods
    # ========================================================================

    def add_repo(self, repo_path: str, **kwargs) -> bool:
        """
        Add repository to tracking

        Args:
            repo_path: Path to repository
            **kwargs: Additional RepoInfo fields

        Returns:
            True if added, False if already tracked
        """
        repo_path = str(Path(repo_path).expanduser().resolve())

        # Get git info
        git_info = self._get_git_info(repo_path)

        repo_info = RepoInfo(
            path=repo_path,
            name=os.path.basename(repo_path),
            remote_url=git_info.get("remote_url"),
            default_branch=git_info.get("default_branch"),
            last_commit=git_info.get("last_commit"),
            **kwargs,
        )

        return self.config_manager.add_repo(repo_info)

    def remove_repo(self, repo_path: str) -> bool:
        """Remove repository from tracking"""
        return self.config_manager.remove_repo(repo_path)

    def update_repo_config(self, repo_path: str, **kwargs) -> bool:
        """Update repository configuration"""
        return self.config_manager.update_repo(repo_path, **kwargs)

    # ========================================================================
    # Validation Methods
    # ========================================================================

    def validate_repo(self, repo_path: str) -> ValidationResult:
        """
        Validate repository

        Args:
            repo_path: Path to repository

        Returns:
            ValidationResult with validation details
        """
        repo_path = str(Path(repo_path).expanduser().resolve())
        issues = []

        # Check if directory exists
        if not os.path.isdir(repo_path):
            return ValidationResult(
                is_valid=False,
                is_git_repo=False,
                has_remote=False,
                issues=["Directory does not exist"],
            )

        # Check if git repo
        git_dir = os.path.join(repo_path, ".git")
        is_git = os.path.isdir(git_dir) or os.path.isfile(git_dir)

        if not is_git:
            issues.append("Not a git repository")

        # Check remote
        has_remote = False
        if is_git:
            try:
                result = subprocess.run(
                    ["git", "remote", "get-url", "origin"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                )
                has_remote = result.returncode == 0
                if not has_remote:
                    issues.append("No remote origin configured")
            except Exception as e:
                issues.append(f"Cannot check remote: {e}")

        return ValidationResult(
            is_valid=(is_git and has_remote),
            is_git_repo=is_git,
            has_remote=has_remote,
            issues=issues,
        )

    def check_large_files(
        self, repo_path: str, threshold_mb: float = 10.0
    ) -> List[str]:
        """
        Check for large files in repository

        Args:
            repo_path: Path to repository
            threshold_mb: Size threshold in MB

        Returns:
            List of large file paths
        """
        repo_path = str(Path(repo_path).expanduser().resolve())
        large_files = []
        threshold_bytes = threshold_mb * 1024 * 1024

        for root, _, files in os.walk(repo_path):
            # Skip .git directory
            if ".git" in root:
                continue

            for file in files:
                filepath = os.path.join(root, file)
                try:
                    size = os.path.getsize(filepath)
                    if size > threshold_bytes:
                        rel_path = os.path.relpath(filepath, repo_path)
                        large_files.append(f"{rel_path} ({size / 1024 / 1024:.2f} MB)")
                except OSError:
                    pass

        return large_files

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _parse_status(self, status_output: str) -> ChangesSummary:
        """Parse git status output"""
        if not status_output:
            return ChangesSummary()

        lines = status_output.strip().split("\n")
        uncommitted = 0
        staged = 0
        untracked = 0
        modified_files = []

        for line in lines:
            if not line.strip():
                continue

            status_code = line[:2]
            filepath = line[3:].strip()
            modified_files.append(filepath)

            if status_code == "??":
                untracked += 1
            elif status_code[0] != " ":
                staged += 1
            else:
                uncommitted += 1

        return ChangesSummary(
            uncommitted=uncommitted,
            staged=staged,
            untracked=untracked,
            modified_files=modified_files,
        )

    def _get_remote_status(self, repo_path: str) -> RemoteStatus:
        """Get remote repository status"""
        try:
            # Get remote URL
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )
            url = result.stdout.strip() if result.returncode == 0 else ""

            # Get ahead/behind counts
            result = subprocess.run(
                ["git", "rev-list", "--left-right", "--count", "HEAD...@{upstream}"],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split()
                ahead = int(parts[0]) if len(parts) > 0 else 0
                behind = int(parts[1]) if len(parts) > 1 else 0
            else:
                ahead = 0
                behind = 0

            return RemoteStatus(url=url, ahead=ahead, behind=behind)

        except Exception:
            return RemoteStatus()

    def _get_commit_info(self) -> CommitInfo:
        """Get last commit information"""
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%H|%s|%an|%ai"],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split("|")
                return CommitInfo(
                    hash=parts[0] if len(parts) > 0 else "",
                    message=parts[1] if len(parts) > 1 else "",
                    author=parts[2] if len(parts) > 2 else "",
                    timestamp=parts[3] if len(parts) > 3 else "",
                )
        except Exception:
            pass

        return CommitInfo()

    def _get_git_info(self, repo_path: str) -> Dict[str, Optional[str]]:
        """Get git repository information"""
        orig_cwd = os.getcwd()
        os.chdir(repo_path)

        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"], capture_output=True, text=True
            )
            remote_url = result.stdout.strip() if result.returncode == 0 else None

            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
            )
            default_branch = result.stdout.strip() if result.returncode == 0 else None

            result = subprocess.run(
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True
            )
            last_commit = result.stdout.strip() if result.returncode == 0 else None

            return {
                "remote_url": remote_url,
                "default_branch": default_branch,
                "last_commit": last_commit,
            }
        finally:
            os.chdir(orig_cwd)
