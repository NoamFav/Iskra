## Python Library API

Iskra can be used as a Python library for programmatic repository management:

```python
from iskra import IskraManager

# Initialize
manager = IskraManager()

# Query operations
repos = manager.get_all_repos(active_only=True)
status = manager.get_repo_status("/path/to/repo")
dirty_repos = manager.filter_repos(has_changes=True)

# Action operations
result = manager.process_repo(
    "/path/to/repo",
    pull=True,
    commit=True,
    push=True
)

# Batch operations
result = manager.process_all(
    pull=True,
    filters={"has_changes": True}
)
```

See `examples/usage_examples.py` for more examples.

### API Reference

#### IskraManager

**Query Methods:**

- `get_all_repos(active_only=True)` - Get all tracked repositories
- `get_repo_status(repo_path)` - Get detailed repository status
- `filter_repos(**filters)` - Filter repositories by criteria

**Action Methods:**

- `process_repo(repo_path, **options)` - Process a single repository
- `process_all(**options)` - Process multiple repositories
- `pull_repo(repo_path)` - Pull latest changes
- `commit_repo(repo_path, message)` - Commit changes
- `push_repo(repo_path)` - Push to remote

**Config Methods:**

- `add_repo(repo_path)` - Add repository to tracking
- `remove_repo(repo_path)` - Remove repository from tracking
- `update_repo_config(repo_path, **config)` - Update repository config

**Validation Methods:**

- `validate_repo(repo_path)` - Validate repository
- `check_large_files(repo_path, threshold_mb)` - Check for large files
