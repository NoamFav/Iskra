"""
Command router. Routes commands to either Go CLI or Python handlers.

Most commands now delegate to the Go CLI for processing.
Python still handles clone and gh which need GitHub API access.
"""

import sys
import subprocess
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

# Commands that passthrough to Go as-is (no flag translation needed)
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
    """Show a styled error for unknown commands."""
    from rich.console import Console
    from iskra.ui.formatting import style

    console = Console()
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


def get_go_binary():
    """Get Go binary path, or None if not available."""
    from iskra.core.go_bridge import GO_BINARY
    return GO_BINARY


def run_go_cli(argv: list[str]) -> int:
    """Run the Go CLI directly with given arguments, output to terminal."""
    binary = get_go_binary()

    if binary is None:
        from rich.console import Console
        from iskra.ui.formatting import style
        console = Console()
        console.print(f"\n{style('Error:', 'error')} Go CLI not found")
        console.print(style("Build it with:", "dim"))
        console.print(style("  cd go-core && go build -o ../bin/iskra ./cmd/iskra", "command"))
        console.print()
        return 1

    return subprocess.run([binary] + argv).returncode


def _translate_python_to_go(argv: list[str]) -> list[str] | None:
    """
    Translate Python-style iskra flags into a Go CLI invocation.

    Returns a list of args to pass to Go CLI (including the subcommand),
    or None if Go CLI is not available and Python should handle it.

    Python's flat flag style → Go's subcommand style:
      iskra --pulse              → iskra pulse
      iskra --status-only        → iskra status
      iskra --pull-only          → iskra commit --pull-only  (via sync-all internally)
      iskra commit               → iskra commit
      iskra status               → iskra status
      iskra pulse                → iskra pulse
      iskra sync                 → iskra sync
      iskra sync-all             → iskra sync-all
    """
    import argparse

    # Parse the Python-style flags minimally (just enough to route)
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--pulse", action="store_true")
    p.add_argument("--status-only", action="store_true")
    p.add_argument("--pull-only", action="store_true")
    p.add_argument("--pull", action="store_true")
    p.add_argument("--no-push", action="store_true")
    p.add_argument("--no-ai-commit", action="store_true")
    p.add_argument("--commit-message", type=str, default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--has-changes", "-c", action="store_true")
    p.add_argument("--only", nargs="+", default=[])
    p.add_argument("--exclude", nargs="+", default=[])
    p.add_argument("--json", action="store_true")
    p.add_argument("--quiet", "-q", action="store_true")
    p.add_argument("--minimal", action="store_true")
    p.add_argument("--scan", action="store_true")
    p.add_argument("--yes", "-y", action="store_true")
    p.add_argument("subcommand", nargs="?", default=None)
    # Ignore unknown flags gracefully
    args, _ = p.parse_known_args(argv)

    # Determine the Go subcommand
    subcommand = args.subcommand or ""

    # Map Python subcommands / flags → Go subcommands
    if subcommand == "pulse" or args.pulse:
        go_cmd = ["pulse"]
    elif subcommand in ("status", "s") or args.status_only:
        go_cmd = ["status"]
    elif subcommand in ("sync",):
        go_cmd = ["sync"]
    elif subcommand in ("sync-all",):
        go_cmd = ["sync-all"]
    elif subcommand in ("commit", "") or True:
        go_cmd = ["commit"]
    else:
        go_cmd = ["commit"]

    # Build global flags (must go before subcommand)
    global_flags = []
    if args.json:
        global_flags.append("--json")
    if args.quiet:
        global_flags.append("--quiet")
    if args.minimal:
        global_flags.append("--minimal")

    # Build subcommand flags
    sub_flags = []

    if go_cmd[0] not in ("sync", "sync-all"):
        # commit / status / pulse flags
        if args.status_only and go_cmd[0] == "commit":
            sub_flags.append("--status-only")
        if args.pull_only:
            sub_flags.append("--pull-only")
        if args.pull:
            sub_flags.append("--pull")
        if args.no_push:
            sub_flags.append("--no-push")
        if args.no_ai_commit:
            sub_flags.append("--no-ai-commit")
        if args.dry_run:
            sub_flags.append("--dry-run")
        if args.has_changes:
            sub_flags.append("--has-changes")
        if args.commit_message:
            sub_flags.extend(["--message", args.commit_message])
        if args.only:
            sub_flags.extend(["--only", ",".join(args.only)])
        if args.exclude:
            sub_flags.extend(["--exclude", ",".join(args.exclude)])

    return global_flags + go_cmd + sub_flags


class CommandRouter:
    """Route commands to Go CLI or Python handlers."""

    @classmethod
    def route(cls, argv: list[str]) -> list[str]:
        """Route commands. Dispatch to Go or Python as appropriate."""
        # No args = run default commit workflow via Go
        if not argv:
            binary = get_go_binary()
            if binary is not None:
                sys.exit(subprocess.run([binary]).returncode)
            return []  # Fall through to Python

        if argv[0] in ("-h", "--help", "help"):
            from iskra.help import show_help
            show_help()
            sys.exit(0)

        if argv[0] in ("-hc", "--help-compact"):
            from iskra.help import show_help_compact
            show_help_compact()
            sys.exit(0)

        cmd = argv[0]

        # =====================================================================
        # Direct Go passthrough: commands with no flag translation needed
        # =====================================================================
        if cmd in GO_PASSTHROUGH_COMMANDS:
            sys.exit(run_go_cli(argv))

        # =====================================================================
        # Main workflow commands: translate Python flags → Go and delegate
        # =====================================================================
        if cmd in ("commit", "status", "s", "pulse", "p", "sync", "sync-all") or (
            not cmd.startswith("-") and cmd not in KNOWN_COMMANDS and False
        ):
            binary = get_go_binary()
            if binary is not None:
                go_args = _translate_python_to_go(argv)
                sys.exit(subprocess.run([binary] + go_args).returncode)

        # Default bare call (no subcommand, just flags like --status-only)
        if cmd.startswith("-"):
            binary = get_go_binary()
            if binary is not None:
                go_args = _translate_python_to_go(argv)
                sys.exit(subprocess.run([binary] + go_args).returncode)

        # =====================================================================
        # Python-only commands
        # =====================================================================
        if cmd == "init":
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

        # Check if it looks like an unknown subcommand
        if not cmd.startswith("-") and cmd not in KNOWN_COMMANDS:
            show_unknown_command_error(cmd)
            sys.exit(1)

        return argv
