"""GitHub API interaction utilities."""

import json
import subprocess
import fnmatch
from rich.console import Console
from rich.panel import Panel

from ..ui.formatting import get_icon

console = Console()


def _match_any(repo_name: str, patterns) -> bool:
    """Match repository name against glob patterns."""
    if not patterns:
        return False
    for pat in patterns:
        if fnmatch.fnmatch(repo_name, pat):
            return True
    return False


def get_github_repos(limit=1000, filter_forks=False, only_stars=0, exclude=None):
    """Get list of repositories from GitHub CLI with detailed information"""
    try:
        # Define fields to extract
        fields = [
            "nameWithOwner",
            "name",
            "description",
            "isPrivate",
            "isFork",
            "stargazerCount",
            "url",
        ]
        fields_arg = ",".join(fields)

        console.print(
            f"[bold blue]{get_icon('github')} Fetching repositories from GitHub...[/]"
        )

        # Run the `gh repo list` command with JSON output
        command = ["gh", "repo", "list", "--limit", str(limit), "--json", fields_arg]

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )

        # Parse JSON output
        repos = json.loads(result.stdout.strip())

        # Apply filters
        if filter_forks:
            repos = [repo for repo in repos if not repo.get("isFork", False)]

        if only_stars > 0:
            repos = [
                repo for repo in repos if repo.get("stargazerCount", 0) >= only_stars
            ]

        if exclude:
            repos = [
                repo for repo in repos if not _match_any(repo["nameWithOwner"], exclude)
            ]

        console.print(
            f"[bold green]{get_icon('success')} Found {len(repos)} repositories."
        )
        return repos
    except subprocess.CalledProcessError as e:
        console.print(
            f"[bold red]{get_icon('error')} Error fetching repositories from GitHub:"
        )
        console.print(Panel(str(e), title="Error Details", border_style="red"))
        return []
    except json.JSONDecodeError as e:
        console.print(f"[bold red]{get_icon('error')} Error parsing GitHub response:")
        console.print(Panel(str(e), title="JSON Error", border_style="red"))
        return []
