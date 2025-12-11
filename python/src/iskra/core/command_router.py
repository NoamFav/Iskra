import sys


class CommandRouter:
    """Route and transform command-line arguments."""

    COMMAND_MAPPINGS = {
        "scan": ["--scan", "--status-only"],
        "pulse": ["--pulse"],
        "status": ["--status-only"],
        "sync": ["--pull", "--pull-only", "--pulse", "-y"],
        "sync-all": ["--pull", "--pull-only", "-y"],
    }

    @classmethod
    def route(cls, argv: list[str]) -> list[str]:
        """Transform command shortcuts into full argument lists."""
        if not argv:
            return argv

        cmd = argv[0]

        # Handle init subcommands separately
        if cmd == "init":
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

        return argv
