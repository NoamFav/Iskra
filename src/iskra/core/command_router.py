"""
Command router. Turns 'iskra sync' into actual flags.
Also handles help and dispatches to subcommands.
"""

import sys
from difflib import get_close_matches


# All known commands/subcommands for suggestions
KNOWN_COMMANDS = [
    "exec",
    "init",
    "clone",
    "gh",
    "log",
    "info",
    "commit",
    "scan",
    "pulse",
    "status",
    "sync",
    "sync-all",
    "help",
]


def show_unknown_command_error(cmd: str) -> None:
    """Show a styled error for unknown commands. Matches iskra -h aesthetic."""
    from rich.console import Console
    from rich.panel import Panel

    console = Console()

    # Find similar commands
    suggestions = get_close_matches(cmd, KNOWN_COMMANDS, n=3, cutoff=0.4)

    console.print()
    console.print(f"[bold red]Error:[/] Unknown command '[yellow]{cmd}[/]'")
    console.print()

    if suggestions:
        console.print("[dim]Did you mean:[/]")
        for s in suggestions:
            console.print(f"  [green]iskra {s}[/]")
        console.print()

    console.print("[dim]Run [white]iskra -h[/] for available commands[/]")
    console.print()


class CommandRouter:
    """Turn command shortcuts into full arg lists. Also intercepts help."""

    COMMAND_MAPPINGS = {
        "scan": ["--scan", "--status-only"],
        "pulse": ["--pulse"],
        "status": ["--status-only"],
        "sync": ["--pull", "--pull-only", "--pulse", "-y"],
        "sync-all": ["--pull", "--pull-only", "-y"],
    }

    @classmethod
    def route(cls, argv: list[str]) -> list[str]:
        """Route commands. Map shortcuts, handle help, dispatch subcommands."""
        if not argv or argv[0] in ("-h", "--help", "help"):
            from iskra.help import show_help
            show_help()
            sys.exit(0)

        # Compact help
        if argv[0] in ("-hc", "--help-compact"):
            from iskra.help import show_help_compact
            show_help_compact()
            sys.exit(0)

        cmd = argv[0]

        # Handle init subcommands separately
        if cmd == "init":
            # Handle init help
            if len(argv) > 1 and argv[1] in ("-h", "--help"):
                from iskra.help import show_init_help
                show_init_help()
                sys.exit(0)
            from iskra import init as init_cli

            subcmd = ["init"] if len(argv) == 1 else argv[1:]
            sys.exit(init_cli.main(subcmd))
        if cmd == "clone":
            from iskra import clone_repos as clone_cli

            sys.exit(clone_cli.main(argv[1:]))
        if cmd == "gh":
            from iskra import gh as gh_cli

            sys.exit(gh_cli.main(argv[1:]))
        if cmd == "exec":
            # Handle exec help
            if len(argv) > 1 and argv[1] in ("-h", "--help"):
                from iskra.help import show_exec_help
                show_exec_help()
                sys.exit(0)
            from iskra import exec as exec_cli

            sys.exit(exec_cli.main(argv[1:]))
        if cmd == "log":
            from iskra import log as log_cli

            sys.exit(log_cli.main(argv[1:]))
        if cmd == "info":
            from iskra import info as info_cli

            sys.exit(info_cli.main(argv[1:]))
        # Handle commit command (default behavior)
        if cmd == "commit":
            return argv[1:]

        # Map other commands
        if cmd in cls.COMMAND_MAPPINGS:
            return argv[1:] + cls.COMMAND_MAPPINGS[cmd]

        # Check if it looks like an unknown subcommand (no dashes)
        if not cmd.startswith("-") and cmd not in KNOWN_COMMANDS:
            show_unknown_command_error(cmd)
            sys.exit(1)

        return argv
