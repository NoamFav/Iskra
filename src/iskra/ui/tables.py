"""
Table builders. Config tables, status tables, whatever needs columns.
"""

from rich.table import Table
from rich.box import ROUNDED


def create_config_table(args, for_pull_repos=False):
    """Build a config summary table. Shows what settings are active."""

    config_table = Table(
        title="Configuration",
        title_style="bold cyan",
        box=ROUNDED,
        border_style="cyan",
        show_header=True,
        header_style="bold cyan",
    )

    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="green")

    if for_pull_repos:

        config_table.add_row(
            "Base Directory",
            args.base_dir,
        )

        config_table.add_row(
            "Repo Limit",
            str(args.limit),
        )

        config_table.add_row(
            "Filter Forks",
            "Yes" if args.filter_forks else "No",
        )

        config_table.add_row(
            "Minimum Stars",
            str(args.only_stars),
        )

        if args.exclude:
            config_table.add_row(
                "Excluded Patterns",
                ", ".join(args.exclude),
            )

    else:

        config_table.add_row(
            "Pull Changes",
            "Yes" if args.pull else "No",
        )

        config_table.add_row(
            "Handle .gitignore",
            "Yes" if args.handle_gitignore else "No",
        )

        config_table.add_row(
            "Remove .DS_Store",
            "Yes" if args.remove_ds_store else "No",
        )

        config_table.add_row(
            "Using ai_commit",
            "Yes" if args.use_ai_commit else "No",
        )

        config_table.add_row(
            "Commit Message",
            (
                "AI Generated"
                if args.commit_message == "auto-commit"
                else args.commit_message
            ),
        )

        if args.exclude:
            config_table.add_row(
                "Excluded",
                ", ".join(args.exclude),
            )

        if args.only:
            config_table.add_row(
                "Only",
                ", ".join(args.only),
            )

    return config_table
