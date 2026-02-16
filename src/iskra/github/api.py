"""
GitHub API wrappers. Uses gh CLI under the hood.
Now with caching so we don't hammer the API like barbarians.
"""

import json
import subprocess
import fnmatch
from rich.console import Console
from rich.panel import Panel

from ..ui.formatting import get_icon, style, get_color
from .cache import cached


console = Console()


def _match_any(repo_name: str, patterns) -> bool:

    if not patterns:
        return False

    for pat in patterns:
        if fnmatch.fnmatch(repo_name, pat):
            return True

    return False


@cached("github_repos")
def get_github_repos(
    limit=1000,
    filter_forks=False,
    only_stars=0,
    exclude=None,
):

    try:

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
            f"{style(get_icon('github') + ' Fetching repositories from GitHub...', 'info')}"
        )

        command = [
            "gh",
            "repo",
            "list",
            "--limit",
            str(limit),
            "--json",
            fields_arg,
        ]

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )

        repos = json.loads(result.stdout.strip())

        if filter_forks:
            repos = [repo for repo in repos if not repo.get("isFork", False)]

        if only_stars > 0:
            repos = [
                repo
                for repo in repos
                if repo.get(
                    "stargazerCount",
                    0,
                )
                >= only_stars
            ]

        if exclude:
            repos = [
                repo
                for repo in repos
                if not _match_any(
                    repo["nameWithOwner"],
                    exclude,
                )
            ]

        console.print(
            f"{style(get_icon('success') + f' Found {len(repos)} repositories.', 'success')}"
        )

        return repos

    except subprocess.CalledProcessError as e:
        console.print(
            f"{style(get_icon('error') + ' Error fetching repositories from GitHub:', 'error')}"
        )
        console.print(Panel(str(e), title="Error Details", border_style=get_color("error") or "red"))
        return []

    except json.JSONDecodeError as e:
        console.print(
            f"{style(get_icon('error') + ' Error parsing GitHub response:', 'error')}"
        )
        console.print(Panel(str(e), title="JSON Error", border_style=get_color("error") or "red"))
        return []


@cached("github_prs")
def get_pr(
    limit=1000,
    filter_closed=True,
    filter_open=False,
    filter_need_review=False,
    filter_require_changes=False,
    filter_draft=False,
    exclude=None,
    repo=None,
):
    try:
        fields = [
            "number",
            "title",
            "state",
            "isDraft",
            "url",
            "createdAt",
            "updatedAt",
            "author",
            "headRefName",
            "baseRefName",
            "reviewDecision",
        ]

        console.print(
            f"{style(get_icon('github') + ' Fetching pull requests from GitHub...', 'info')}"
        )

        # Decide state: default to closed unless open explicitly requested
        state = "all"
        if filter_open and not filter_closed:
            state = "open"
        elif filter_closed and not filter_open:
            state = "closed"

        cmd = [
            "gh",
            "pr",
            "list",
            "--limit",
            str(limit),
            "--state",
            state,
            "--json",
            ",".join(fields),
        ]

        if repo:
            cmd += ["--repo", repo]

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )

        prs = json.loads(result.stdout.strip() or "[]")

        # Draft filter
        if filter_draft:
            prs = [pr for pr in prs if pr.get("isDraft", False)]

        # Review-decision filters (depends on GitHub’s reviewDecision values)
        if filter_need_review:
            prs = [
                pr
                for pr in prs
                if pr.get("reviewDecision") in (None, "REVIEW_REQUIRED")
            ]

        if filter_require_changes:
            prs = [
                pr
                for pr in prs
                if pr.get(
                    "reviewDecision",
                )
                == "CHANGES_REQUESTED"
            ]

        if exclude and repo:
            if _match_any(repo, exclude):
                prs = []

        console.print(
            f"{style(get_icon('success') + f' Found {len(prs)} pull requests.', 'success')}"
        )
        return prs

    except subprocess.CalledProcessError as e:
        console.print(
            f"{style(get_icon('error') + ' Error fetching pull requests from GitHub:', 'error')}"
        )
        console.print(Panel(str(e), title="Error Details", border_style=get_color("error") or "red"))
        return []

    except json.JSONDecodeError as e:
        console.print(
            f"{style(get_icon('error') + ' Error parsing GitHub response:', 'error')}"
        )
        console.print(Panel(str(e), title="JSON Error", border_style=get_color("error") or "red"))
        return []


@cached("github_prs_slug")
def get_prs(
    slug: str,
    limit: int = 50,
    state: str = "open",  # open|closed|merged|all
    draft: str = "all",  # all|only|exclude
    need_review: bool = False,
    require_changes: bool = False,
) -> list[dict]:
    fields = [
        "number",
        "title",
        "state",
        "isDraft",
        "url",
        "author",
        "createdAt",
        "updatedAt",
        "reviewDecision",
        "baseRefName",
        "headRefName",
    ]

    cmd = [
        "gh",
        "pr",
        "list",
        "--repo",
        slug,
        "--limit",
        str(limit),
        "--state",
        state,
        "--json",
        ",".join(fields),
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )

    prs = json.loads(result.stdout.strip() or "[]")

    if draft == "only":
        prs = [pr for pr in prs if pr.get("isDraft", False)]
    elif draft == "exclude":
        prs = [pr for pr in prs if not pr.get("isDraft", False)]

    if need_review:
        prs = [
            pr
            for pr in prs
            if pr.get(
                "reviewDecision",
            )
            in (None, "REVIEW_REQUIRED")
        ]

    if require_changes:
        prs = [
            pr
            for pr in prs
            if pr.get(
                "reviewDecision",
            )
            == "CHANGES_REQUESTED"
        ]

    return prs
