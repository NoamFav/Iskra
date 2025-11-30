"""
GitHub API interaction utilities.

Provides functions for fetching repository information from GitHub using
the GitHub CLI (gh). Supports filtering, pagination, and rich error handling
for robust integration with GitHub's API.

Dependencies:
    - GitHub CLI (gh): Must be installed and authenticated
    - Rich: For console output and error display

Authentication:
    Relies on GitHub CLI authentication (gh auth login).
    User must have valid GitHub credentials configured.
"""

import json
import subprocess
import fnmatch
from rich.console import Console
from rich.panel import Panel

from ..ui.formatting import get_icon

# Global console instance for consistent output
console = Console()


def _match_any(repo_name: str, patterns) -> bool:
    """
        Match repository name against glob patterns.

        Tests if a repository name matches any pattern in a list,
        using shell-style glob syntax (* and ? wildcards). Used
        for filtering repositories by name patterns.

        Args:
            repo_name: Repository name to test (e.g., "user/repo-name")
            patterns: List of glob patterns to match against
                     Can be empty list or None

        Returns:
            True if repo_name matches any pattern
            False if no patterns provided or no match

        Pattern Syntax:
            - * : Matches any sequence of characters
            - ? : Matches any single character
            - [abc] : Matches any character in brackets
            - [!abc] : Matches any character not in brackets

        Example Usage:
    ```python
            # Match all repos starting with "test-"
            _match_any("test-app", ["test-*"])  # True
            _match_any("prod-app", ["test-*"])  # False

            # Match multiple patterns
            patterns = ["test-*", "demo-*", "tmp-*"]
            _match_any("demo-project", patterns)  # True

            # Match specific repos
            _match_any("old-repo", ["old-*", "legacy-*"])  # True

            # Empty patterns
            _match_any("any-repo", [])  # False
            _match_any("any-repo", None)  # False
    ```

        Case Sensitivity:
            Matching is case-sensitive on Unix-like systems,
            case-insensitive on Windows (fnmatch behavior).

        Performance:
            O(n*m) where n=len(patterns), m=len(repo_name)
            Acceptable for typical use (10-100 patterns, short names)

        Note:
            Short-circuits on first match for efficiency.
            Empty pattern list is explicitly handled to avoid
            iteration and returns False immediately.
    """
    # Fast path: no patterns means no match
    if not patterns:
        return False

    # Test each pattern until we find a match
    for pat in patterns:
        if fnmatch.fnmatch(repo_name, pat):
            return True

    # No pattern matched
    return False


def get_github_repos(limit=1000, filter_forks=False, only_stars=0, exclude=None):
    """
        Get list of repositories from GitHub CLI with detailed information.

        Fetches repository metadata from GitHub using the GitHub CLI (gh),
        applies filters, and returns a list of repository dictionaries.
        Designed for bulk repository operations like cloning or analysis.

        Args:
            limit: Maximum number of repositories to fetch (default: 1000)
                  GitHub CLI pagination limit
            filter_forks: If True, exclude forked repositories (default: False)
                         Useful for focusing on original work
            only_stars: Minimum star count threshold (default: 0)
                       If >0, only return repos with at least this many stars
            exclude: List of glob patterns for repos to exclude (default: None)
                    Example: ["test-*", "tmp-*", "archive-*"]

        Returns:
            List of repository dictionaries, each containing:
                - nameWithOwner: Full name (e.g., "user/repo")
                - name: Repository name only (e.g., "repo")
                - description: Repository description text
                - isPrivate: Boolean indicating private status
                - isFork: Boolean indicating if forked
                - stargazerCount: Number of stars
                - url: Repository URL
            Empty list if error occurs or no repos match filters

        Filtering Pipeline:
            1. Fetch repos from GitHub (up to limit)
            2. Filter out forks (if filter_forks=True)
            3. Filter by star count (if only_stars>0)
            4. Filter by exclusion patterns (if exclude provided)
            5. Return remaining repositories

        Example Usage:
    ```python
            # Get all repositories
            repos = get_github_repos()

            # Get non-fork repos with 10+ stars
            popular = get_github_repos(
                filter_forks=True,
                only_stars=10
            )

            # Exclude test and demo repos
            production = get_github_repos(
                exclude=["test-*", "demo-*", "*-sandbox"]
            )

            # Limited fetch for quick tests
            sample = get_github_repos(limit=10)
    ```

        GitHub CLI Requirements:
            - `gh` command must be in PATH
            - User must be authenticated (gh auth login)
            - User must have repo access permissions

        Error Handling:
            - subprocess.CalledProcessError: gh command failed
              (not installed, not authenticated, network error)
            - json.JSONDecodeError: Invalid JSON from GitHub
              (rare, indicates API or CLI bug)
            - Returns empty list on any error after logging

        Performance:
            - API call latency: 1-5 seconds typical
            - Pagination: Fetches in batches internally
            - Network-bound operation
            - Caching: None (always fetches fresh data)

        Rate Limiting:
            GitHub API has rate limits (5000/hour authenticated).
            GitHub CLI handles rate limit errors automatically.
            May receive HTTP 403 if limit exceeded.

        Output:
            Displays progress and results via Rich console:
            - "Fetching repositories..." during API call
            - "Found N repositories" on success
            - Error panels on failure

        Note:
            This function uses the GitHub CLI rather than direct API
            calls to leverage gh's authentication, pagination, and
            error handling. Requires gh to be installed separately.
    """
    try:
        # Define fields to extract from GitHub API
        # These are GraphQL field names from GitHub's schema
        fields = [
            "nameWithOwner",  # Full name: "owner/repo"
            "name",  # Short name: "repo"
            "description",  # Repository description
            "isPrivate",  # Privacy status
            "isFork",  # Whether forked from another repo
            "stargazerCount",  # Number of stars (popularity metric)
            "url",  # HTTPS clone URL
        ]

        # Convert field list to comma-separated string for CLI
        fields_arg = ",".join(fields)

        # Display progress message to user
        console.print(
            f"[bold blue]{get_icon('github')} Fetching repositories from GitHub...[/]"
        )

        # Build GitHub CLI command
        # gh repo list: Lists repositories for authenticated user
        # --limit: Maximum repos to fetch (pagination handled by gh)
        # --json: Output format (structured data)
        command = ["gh", "repo", "list", "--limit", str(limit), "--json", fields_arg]

        # Execute GitHub CLI command
        # check=True: Raise exception on non-zero exit code
        # text=True: Decode stdout/stderr as text (not bytes)
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,  # Raise CalledProcessError on failure
        )

        # Parse JSON response from GitHub CLI
        # GitHub CLI outputs valid JSON array of repository objects
        repos = json.loads(result.stdout.strip())

        # === FILTERING PIPELINE ===

        # Filter 1: Remove forked repositories if requested
        # Forks are copies of other repos, often for contributions
        if filter_forks:
            repos = [repo for repo in repos if not repo.get("isFork", False)]

        # Filter 2: Apply star count threshold
        # Stars indicate popularity/quality
        if only_stars > 0:
            repos = [
                repo for repo in repos if repo.get("stargazerCount", 0) >= only_stars
            ]

        # Filter 3: Apply exclusion patterns
        # Remove repos matching any exclude pattern
        if exclude:
            repos = [
                repo for repo in repos if not _match_any(repo["nameWithOwner"], exclude)
            ]

        # Display success message with final count
        console.print(
            f"[bold green]{get_icon('success')} Found {len(repos)} repositories."
        )

        return repos

    except subprocess.CalledProcessError as e:
        # GitHub CLI command failed
        # Possible causes:
        # - gh not installed or not in PATH
        # - User not authenticated (need: gh auth login)
        # - Network connectivity issues
        # - GitHub API errors (rate limit, service disruption)
        # - Invalid command arguments

        console.print(
            f"[bold red]{get_icon('error')} Error fetching repositories from GitHub:"
        )
        console.print(Panel(str(e), title="Error Details", border_style="red"))
        return []

    except json.JSONDecodeError as e:
        # GitHub CLI returned invalid JSON
        # Rare error - usually indicates:
        # - Corrupted response
        # - GitHub CLI bug
        # - Network truncation
        # - Non-JSON stderr mixed with stdout

        console.print(f"[bold red]{get_icon('error')} Error parsing GitHub response:")
        console.print(Panel(str(e), title="JSON Error", border_style="red"))
        return []
