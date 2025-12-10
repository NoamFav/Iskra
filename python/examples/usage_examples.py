"""
Iskra Python API - Usage Examples
Demonstrates how to use Iskra as a library in Zvezda and other tools.
"""

from iskra.api.manager import IskraManager


# ============================================================================
# Example 1: Basic Usage - Query Repository Status
# ============================================================================


def example_basic_query():
    """Query repository information"""

    # Initialize manager
    manager = IskraManager()

    # Get all tracked repositories
    repos = manager.get_all_repos(active_only=True)
    print(f"Found {len(repos)} repositories")

    for repo in repos:
        print(f"  - {repo.name}: {repo.path}")

    # Get detailed status of a specific repo
    if repos:
        status = manager.get_repo_status(repos[0].path)
        print(f"\nStatus of {status.name}:")
        print(f"  Branch: {status.branch}")
        print(f"  Changes: {status.changes.has_changes}")
        print(f"  Behind remote: {status.remote.behind} commits")


# ============================================================================
# Example 2: Filtering Repositories
# ============================================================================


def example_filtering():
    """Find repositories matching specific criteria"""

    manager = IskraManager()

    # Find repos with uncommitted changes
    dirty_repos = manager.filter_repos(has_changes=True)
    print(f"Repositories with changes: {len(dirty_repos)}")

    # Find repos behind remote
    behind_repos = manager.filter_repos(behind_remote=True)
    print(f"Repositories behind remote: {len(behind_repos)}")

    # Find repos by pattern
    python_repos = manager.filter_repos(pattern="*python*")
    print(f"Python repositories: {len(python_repos)}")

    # Combine filters
    main_branch_dirty = manager.filter_repos(has_changes=True, branch="main")
    print(f"Dirty repos on main: {len(main_branch_dirty)}")


# ============================================================================
# Example 3: Single Repository Operations
# ============================================================================


def example_single_repo_ops():
    """Process a single repository"""

    manager = IskraManager()
    repo_path = "/path/to/repo"

    # Just pull
    result = manager.pull_repo(repo_path)
    if result.success:
        print("Pull successful")

    # Just commit
    result = manager.commit_repo(repo_path, "feat: add new feature")
    if result.success:
        print("Commit successful")

    # Just push
    result = manager.push_repo(repo_path)
    if result.success:
        print("Push successful")

    # All-in-one: pull + commit + push
    result = manager.process_repo(
        repo_path,
        pull=True,
        commit=True,
        push=True,
        commit_message="fix: bug fix",
    )

    print(f"Operations: {len(result.operations)}")
    for op in result.operations:
        print(f"  {op.type}: {'✓' if op.success else '✗'} - {op.message}")


# ============================================================================
# Example 4: Batch Operations
# ============================================================================


def example_batch_operations():
    """Process multiple repositories at once"""

    manager = IskraManager()

    # Process all repos with changes
    result = manager.process_all(
        pull=True,
        commit=True,
        push=True,
        filters={"has_changes": True},
    )

    print(f"Processed: {result.total} repos")
    print(f"Successful: {result.successful}")
    print(f"Failed: {result.failed}")

    # Show details
    for repo_result in result.results:
        if not repo_result.success:
            print(f"\nFailed: {repo_result.repo_path}")
            for error in repo_result.errors:
                print(f"  Error: {error}")


# ============================================================================
# Example 5: Dry Run Mode
# ============================================================================


def example_dry_run():
    """Preview what would happen without making changes"""

    manager = IskraManager()

    # See what would be committed
    result = manager.process_repo(
        "/path/to/repo",
        commit=True,
        push=True,
        dry_run=True,  # No actual changes
    )

    print("Dry run results:")
    for op in result.operations:
        print(f"  {op.message}")


# ============================================================================
# Example 6: Repository Management
# ============================================================================


def example_repo_management():
    """Add, remove, and configure repositories"""

    manager = IskraManager()

    # Add a new repository
    added = manager.add_repo("/path/to/new/repo")
    if added:
        print("Repository added")

    # Update repository config
    manager.update_repo_config(
        "/path/to/repo",
        active=True,
        default_branch="main",
    )

    # Remove repository
    removed = manager.remove_repo("/path/to/old/repo")
    if removed:
        print("Repository removed")


# ============================================================================
# Example 7: Validation and Safety Checks
# ============================================================================


def example_validation():
    """Validate repositories before operations"""

    manager = IskraManager()
    repo_path = "/path/to/repo"

    # Validate repository
    validation = manager.validate_repo(repo_path)

    if not validation.is_valid:
        print("Validation failed:")
        for issue in validation.issues:
            print(f"  - {issue}")
        return

    # Check for large files
    large_files = manager.check_large_files(repo_path, threshold_mb=5.0)
    if large_files:
        print("Warning: Large files detected:")
        for file in large_files:
            print(f"  - {file}")

    # Safe to proceed with operations
    manager.process_repo(repo_path, commit=True, push=True)


# ============================================================================
# Example 8: Zvezda Integration - Intelligent Workflow
# ============================================================================


def zvezda_intelligent_workflow():
    """
    Example of how Zvezda would use Iskra for smart repository management
    """

    manager = IskraManager()

    # 1. Find repos that need attention
    repos_to_sync = manager.filter_repos(has_changes=True)
    repos_behind = manager.filter_repos(behind_remote=True)

    print(f"Found {len(repos_to_sync)} repos with changes")
    print(f"Found {len(repos_behind)} repos behind remote")

    # 2. Pull repos that are behind
    if repos_behind:
        print("\nPulling repos behind remote...")
        for repo in repos_behind:
            result = manager.pull_repo(repo.path)
            if result.success:
                print(f"  ✓ {repo.name}")
            else:
                print(f"  ✗ {repo.name}: {result.errors}")

    # 3. Commit and push repos with changes
    if repos_to_sync:
        print("\nCommitting and pushing changes...")
        for repo in repos_to_sync:
            # Validate first
            validation = manager.validate_repo(repo.path)
            if not validation.is_valid:
                print(f"  ⚠ {repo.name}: Skipping (validation failed)")
                continue

            # Check for large files
            large_files = manager.check_large_files(repo.path)
            if large_files:
                print(f"  ⚠ {repo.name}: Has large files, skipping")
                continue

            # Process repo
            result = manager.process_repo(
                repo.path,
                commit=True,
                push=True,
                commit_message=None,  # Auto-generate
            )

            if result.success:
                print(f"  ✓ {repo.name}")
            else:
                print(f"  ✗ {repo.name}: {result.errors}")

    # 4. Generate report
    all_repos = manager.get_all_repos()
    total = len(all_repos)
    synced = len(repos_to_sync)
    behind = len(repos_behind)

    print("\n=== Summary ===")
    print(f"Total repos: {total}")
    print(f"Synced: {synced}")
    print(f"Behind: {behind}")
    print(f"Clean: {total - synced - behind}")


# ============================================================================
# Example 9: Custom Commit Messages
# ============================================================================


def example_custom_commits():
    """Generate smart commit messages based on changes"""

    manager = IskraManager()
    repo_path = "/path/to/repo"

    # Get status to see what changed
    status = manager.get_repo_status(repo_path)

    if not status.changes.has_changes:
        print("No changes to commit")
        return

    # Generate message based on files
    modified_files = status.changes.modified_files

    if any(".py" in f for f in modified_files):
        message = "refactor: update Python code"
    elif any(".md" in f for f in modified_files):
        message = "docs: update documentation"
    elif any("test" in f for f in modified_files):
        message = "test: update tests"
    else:
        message = "chore: general updates"

    # Commit with custom message
    manager.commit_repo(repo_path, message)
    print(f"Committed: {message}")


# ============================================================================
# Example 10: Error Handling
# ============================================================================


def example_error_handling():
    """Robust error handling for production use"""

    manager = IskraManager()

    try:
        result = manager.process_repo(
            "/path/to/repo",
            pull=True,
            commit=True,
            push=True,
        )

        if not result.success:
            print("Operation failed:")
            for error in result.errors:
                print(f"  Error: {error}")

            # Check which operations succeeded
            for op in result.operations:
                if not op.success:
                    print(f"  Failed operation: {op.type}")
                    print(f"    Message: {op.message}")

    except Exception as e:
        print(f"Unexpected error: {e}")
        # Log to file, send alert, etc.


# ============================================================================
# Run Examples
# ============================================================================

if __name__ == "__main__":
    # Uncomment to run specific examples

    # example_basic_query()
    # example_filtering()
    # example_single_repo_ops()
    # example_batch_operations()
    # example_dry_run()
    # example_repo_management()
    # example_validation()
    # zvezda_intelligent_workflow()
    # example_custom_commits()
    # example_error_handling()

    print("Examples ready to run!")
    print("Uncomment the example you want to try in the __main__ block")
