"""
Command router. Routes commands to either Go CLI or Python handlers.

Most commands now delegate to the Go CLI for processing.
Python still handles some commands that need Python-specific features.
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
    "diff",
    "branches",
    "br",
    "stash",
]

# Commands that should be handled by Go CLI directly
GO_PASSTHROUGH_COMMANDS = {
    "log",
    "info",
    "diff",
    "branches",
    "br",
    "stash",
    "scan",
    "exec",
}


def show_unknown_command_error(cmd: str) -> None:
    """Show a styled error for unknown commands. Matches iskra -h aesthetic."""
    from rich.console import Console
    from iskra.ui.formatting import style

    console = Console()

    # Find similar commands
    suggestions = get_close_matches(cmd, KNOWN_COMMANDS, n=3, cutoff=0.4)

    console.print()
    console.print(f"{style('Error:', 'error')} Unknown command '{style(cmd, 'warning')}'")
    console.print()

    if suggestions:
        console.print(style("Did you mean:", "dim"))
        for s in suggestions:
            console.print(f"  {style(f'iskra {s}', 'command')}")
        console.print()

    console.print(f"{style('Run', 'dim')} {style('iskra -h', 'highlight')} {style('for available commands', 'dim')}")
    console.print()


def run_go_cli(argv: list[str]) -> int:
    """Run the Go CLI directly with given arguments."""
    from iskra.core.go_bridge import GO_BINARY, is_go_available
    import subprocess

    if not is_go_available():
        from rich.console import Console
        from iskra.ui.formatting import style

        console = Console()
        console.print(f"\n{style('Error:', 'error')} Go CLI not found")
        console.print(style("Build it with:", "dim"))
        console.print(style("  cd go-core && go build -o ../bin/iskra ./cmd/iskra", "command"))
        console.print()
        return 1

    return subprocess.run([GO_BINARY] + argv).returncode


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
        # No args = run default commit workflow
        if not argv:
            return []

        if argv[0] in ("-h", "--help", "help"):
            from iskra.help import show_help
            show_help()
            sys.exit(0)

        # Compact help
        if argv[0] in ("-hc", "--help-compact"):
            from iskra.help import show_help_compact
            show_help_compact()
            sys.exit(0)

        cmd = argv[0]

        # =====================================================================
        # Commands that passthrough directly to Go CLI
        # These are faster and have no Python dependencies
        # =====================================================================
        if cmd in GO_PASSTHROUGH_COMMANDS:
            sys.exit(run_go_cli(argv))

        # =====================================================================
        # Commands that still use Python handlers
        # These need Python-specific features or haven't been migrated yet
        # =====================================================================

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
