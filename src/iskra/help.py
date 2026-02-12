"""
The help screen. Pretty tables and ASCII art because we're fancy like that.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box


console = Console()


LOGO = """
[bold cyan]
  ██╗███████╗██╗  ██╗██████╗  █████╗
  ██║██╔════╝██║ ██╔╝██╔══██╗██╔══██╗
  ██║███████╗█████╔╝ ██████╔╝███████║
  ██║╚════██║██╔═██╗ ██╔══██╗██╔══██║
  ██║███████║██║  ██╗██║  ██║██║  ██║
  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝
[/]
"""

TAGLINE = "[dim]Intelligent Git automation with AI-powered commits[/]"


def show_help():
    """The full help. Commands, options, examples, the whole enchilada."""
    console.print(LOGO)
    console.print(f"  {TAGLINE}\n")

    # Commands table
    commands_table = Table(
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
        title="[bold white]Commands[/]",
        title_justify="left",
        padding=(0, 1),
    )
    commands_table.add_column("Command", style="green", min_width=20)
    commands_table.add_column("Description", style="white")

    commands = [
        ("iskra", "Commit & push all tracked repos (default)"),
        ("iskra exec <cmd>", "Run any command across all repos"),
        ("iskra init", "Initialize config and scan for repos"),
        ("iskra status", "Show status of all repos"),
        ("iskra scan", "Scan directory and show status"),
        ("iskra pulse", "Process current repo only"),
        ("iskra sync", "Pull current repo"),
        ("iskra sync-all", "Pull all tracked repos"),
        ("iskra clone", "Clone GitHub repos"),
    ]

    for cmd, desc in commands:
        commands_table.add_row(cmd, desc)

    console.print(commands_table)
    console.print()

    # Init subcommands
    init_table = Table(
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
        title="[bold white]Init Subcommands[/]",
        title_justify="left",
        padding=(0, 1),
    )
    init_table.add_column("Command", style="green", min_width=20)
    init_table.add_column("Description", style="white")

    init_commands = [
        ("iskra init init", "Scan and track repos"),
        ("iskra init list", "List tracked repos"),
        ("iskra init add [path]", "Add repo to tracking"),
        ("iskra init remove [path]", "Remove repo from tracking"),
    ]

    for cmd, desc in init_commands:
        init_table.add_row(cmd, desc)

    console.print(init_table)
    console.print()

    # Options - split into groups
    print_option_group(
        "Operation Modes",
        [
            ("--scan", "Scan directory instead of using tracked repos"),
            ("--pulse", "Process current repo only"),
            ("--status-only", "Show status without committing"),
            ("--pull-only", "Only pull, don't commit"),
        ],
    )

    print_option_group(
        "Git Operations",
        [
            ("--pull", "Pull before commit"),
            ("--no-push", "Don't push after commit"),
            ("--no-ai-commit", "Use manual commit message"),
            ("--commit-message MSG", "Set commit message"),
        ],
    )

    print_option_group(
        "Filtering",
        [
            ("--only PATTERN...", "Only include matching repos"),
            ("--exclude PATTERN...", "Exclude matching repos"),
            ("--dirty, -c", "Only repos with changes"),
            ("--clean", "Only clean repos"),
            ("--on-branch BRANCH...", "Only repos on branch"),
            ("--behind-remote", "Only repos behind remote"),
            ("--ahead-remote", "Only repos ahead of remote"),
            ("--conflicts", "Only repos with conflicts"),
        ],
    )

    print_option_group(
        "Safety & Preview",
        [
            ("--dry-run", "Preview without making changes"),
            ("--show-diff", "Show diff before committing"),
            ("-y, --yes", "Skip all confirmations"),
        ],
    )

    print_option_group(
        "Output",
        [
            ("--json", "Output JSON instead of Rich UI"),
            ("-q, --quiet", "Minimal output"),
            ("--compact", "Compact display for clean repos"),
        ],
    )

    print_option_group(
        "Configuration",
        [
            ("--config PATH", "Use custom config file"),
            ("--dir PATH", "Override base directory"),
        ],
    )

    print_option_group(
        "Exec Options",
        [
            ("-p N, --parallel N", "Run N commands in parallel"),
            ("--fail-fast", "Stop on first error"),
        ],
    )

    # Examples
    examples_panel = Panel(
        Text.from_markup(
            "[green]# Commit all repos with AI messages[/]\n"
            "iskra\n\n"
            "[green]# Preview what would happen[/]\n"
            "iskra --dry-run\n\n"
            "[green]# Pull all repos[/]\n"
            "iskra sync-all\n\n"
            "[green]# Run command across repos[/]\n"
            'iskra exec "git fetch --all"\n\n'
            "[green]# Filter by pattern[/]\n"
            'iskra --only "frontend-*" --show-diff\n\n'
            "[green]# Parallel execution[/]\n"
            'iskra exec -p 5 "npm install"'
        ),
        title="[bold white]Examples[/]",
        border_style="dim",
        padding=(1, 2),
    )
    console.print(examples_panel)

    # Footer
    console.print()
    console.print(
        "[dim]Config:[/] ~/.config/iskra/config.yaml"
    )
    console.print(
        "[dim]Docs:[/]   https://github.com/NoamFav/Iskra"
    )
    console.print()


def print_option_group(title: str, options: list):
    """Make a nice little table for a group of options."""
    table = Table(
        box=box.SIMPLE,
        show_header=False,
        padding=(0, 1),
        expand=False,
    )
    table.add_column("Option", style="yellow", min_width=24)
    table.add_column("Description", style="dim")

    for opt, desc in options:
        table.add_row(opt, desc)

    panel = Panel(
        table,
        title=f"[bold white]{title}[/]",
        title_align="left",
        border_style="dim",
        padding=(0, 0),
    )
    console.print(panel)


def show_exec_help():
    """Help specifically for exec. Because it's special."""
    console.print("\n[bold cyan]iskra exec[/] - Run commands across repos\n")

    console.print("[bold]Usage:[/]")
    console.print('  iskra exec [OPTIONS] "COMMAND"\n')

    print_option_group(
        "Options",
        [
            ("--only PATTERN...", "Only include matching repos"),
            ("--exclude PATTERN...", "Exclude matching repos"),
            ("--scan", "Scan directory instead of tracked"),
            ("--dir PATH", "Override base directory"),
            ("-y, --yes", "Skip confirmation"),
            ("-q, --quiet", "Only show output, no headers"),
            ("--fail-fast", "Stop on first error"),
            ("-p N, --parallel N", "Run N in parallel (default: 1)"),
        ],
    )

    examples = Panel(
        Text.from_markup(
            "[green]# Git commands[/]\n"
            'iskra exec "git log --oneline -5"\n'
            'iskra exec "git fetch --all"\n'
            'iskra exec "git stash list"\n\n'
            "[green]# Shell commands[/]\n"
            'iskra exec "npm install"\n'
            'iskra exec "make test"\n\n'
            "[green]# With filters[/]\n"
            'iskra exec --only "api-*" "npm test"\n\n'
            "[green]# Parallel[/]\n"
            'iskra exec -p 5 -y "git fetch"'
        ),
        title="[bold white]Examples[/]",
        border_style="dim",
        padding=(1, 2),
    )
    console.print(examples)


def show_init_help():
    """Help for init. Scan, track, manage repos."""
    console.print("\n[bold cyan]iskra init[/] - Initialize and manage repos\n")

    console.print("[bold]Usage:[/]")
    console.print("  iskra init <subcommand> [OPTIONS]\n")

    print_option_group(
        "Subcommands",
        [
            ("init", "Scan directory and track repos"),
            ("list, ls", "List all tracked repos"),
            ("add [PATH]", "Add repo to tracking"),
            ("remove, rm [PATH]", "Remove repo from tracking"),
        ],
    )

    print_option_group(
        "Init Options",
        [
            ("--base-dir PATH", "Directory to scan"),
            ("-y, --yes", "Accept all defaults"),
            ("--show-repos", "Show repos after init"),
        ],
    )

    print_option_group(
        "List Options",
        [
            ("--all", "Include inactive repos"),
        ],
    )


def show_help_compact():
    """The TL;DR version. Quick reference for people in a hurry."""
    console.print("[bold cyan]iskra[/] - Git automation with AI commits\n")

    console.print("[bold]Commands:[/]")
    console.print("  [green]iskra[/]              Commit & push all repos")
    console.print("  [green]iskra exec[/] <cmd>   Run command across repos")
    console.print("  [green]iskra init[/]         Initialize & scan repos")
    console.print("  [green]iskra status[/]       Show status only")
    console.print("  [green]iskra sync-all[/]     Pull all repos")
    console.print()

    console.print("[bold]Common Options:[/]")
    console.print("  [yellow]--dry-run[/]          Preview without changes")
    console.print("  [yellow]--pull[/]             Pull before commit")
    console.print("  [yellow]--no-push[/]          Don't push after commit")
    console.print("  [yellow]--only[/] PATTERN     Filter repos by pattern")
    console.print("  [yellow]--exclude[/] PATTERN  Exclude repos by pattern")
    console.print("  [yellow]-y, --yes[/]          Skip confirmations")
    console.print("  [yellow]--show-diff[/]        Show diff before commit")
    console.print("  [yellow]-q, --quiet[/]        Minimal output")
    console.print()

    console.print("[bold]Exec Options:[/]")
    console.print("  [yellow]-p N[/]               Parallel execution")
    console.print("  [yellow]--fail-fast[/]        Stop on first error")
    console.print()

    console.print("[bold]Examples:[/]")
    console.print("  [dim]$[/] iskra --dry-run")
    console.print("  [dim]$[/] iskra --only \"api-*\" --show-diff")
    console.print("  [dim]$[/] iskra exec -p 5 \"git fetch --all\"")
    console.print()

    console.print("[dim]Full help: iskra -h | Config: ~/.config/iskra/[/]")


if __name__ == "__main__":
    show_help()
