""""""

from rich.table import Table
from rich.box import ROUNDED


def create_config_table(args, for_pull_repos=False):
    """"""
    # Create table with consistent styling
    config_table = Table(
        title="Configuration",  # Header text
        title_style="bold cyan",  # Emphasized title
        box=ROUNDED,  # Modern rounded corners
        border_style="cyan",  # Consistent color scheme
        show_header=True,  # Display column headers
        header_style="bold cyan",  # Emphasized column names
    )

    # Define two-column layout: Setting name | Value
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="green")

    # Branch based on command type
    if for_pull_repos:
        # GitHub repository cloning configuration
        # Settings specific to the pull_repos command

        # Base directory where repos will be cloned
        config_table.add_row("Base Directory", args.base_dir)

        # Maximum number of repos to fetch from GitHub API
        # Prevents excessive API calls and disk usage
        config_table.add_row("Repo Limit", str(args.limit))

        # Whether to exclude forked repositories
        # Useful for focusing on original work only
        config_table.add_row("Filter Forks", "Yes" if args.filter_forks else "No")

        # Minimum star count threshold for cloning
        # Quality/popularity filter
        config_table.add_row("Minimum Stars", str(args.only_stars))

        # Show exclusion patterns if any are configured
        # Only add row if exclusions exist to avoid clutter
        if args.exclude:
            config_table.add_row("Excluded Patterns", ", ".join(args.exclude))

    else:
        # Auto-commit configuration
        # Settings specific to git automation workflow

        # Whether to pull from remote before committing
        # Ensures working directory is up-to-date
        config_table.add_row("Pull Changes", "Yes" if args.pull else "No")

        # Automatic .gitignore file management
        # Adds common patterns to .gitignore automatically
        config_table.add_row(
            "Handle .gitignore", "Yes" if args.handle_gitignore else "No"
        )

        # Automatic cleanup of macOS .DS_Store files
        # Prevents committing OS-specific metadata
        config_table.add_row(
            "Remove .DS_Store", "Yes" if args.remove_ds_store else "No"
        )

        # AI-powered commit message generation
        # Uses bundled ai_commit binary for intelligent messages
        config_table.add_row("Using ai_commit", "Yes" if args.use_ai_commit else "No")

        # Commit message configuration
        # Shows either "AI Generated" or custom message text
        config_table.add_row(
            "Commit Message",
            (
                "AI Generated"
                if args.commit_message == "auto-commit"  # Default triggers AI
                else args.commit_message  # Custom message
            ),
        )

        # Repository filtering patterns
        # Only show if filters are configured

        # Exclusion patterns (blacklist)
        if args.exclude:
            config_table.add_row("Excluded", ", ".join(args.exclude))

        # Inclusion patterns (whitelist)
        if args.only:
            config_table.add_row("Only", ", ".join(args.only))

    return config_table
