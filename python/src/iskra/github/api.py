""""""

import json
import subprocess
import fnmatch
from rich.console import Console
from rich.panel import Panel

from ..ui.formatting import get_icon

# Global console instance for consistent output
console = Console()


def _match_any(repo_name: str, patterns) -> bool:
    """"""
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
    """"""
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
