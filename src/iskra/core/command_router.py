"""
Command router. Turns 'iskra sync' into actual flags.
Also handles help and dispatches to subcommands.
"""

import sys


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
        # Handle commit command (default behavior)
        if cmd == "commit":
            return argv[1:]

        # Map other commands
        if cmd in cls.COMMAND_MAPPINGS:
            return argv[1:] + cls.COMMAND_MAPPINGS[cmd]

        return argv
