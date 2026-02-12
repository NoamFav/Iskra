"""
UI Manager. Handles all the user-facing output and prompts.
"""

from rich.console import Console
from iskra.ui.formatting import print_header
from rich.prompt import Confirm


class UIManager:
    """Print stuff, ask questions, show summaries. The people skills."""

    def __init__(self, rich_enabled: bool, console: Console):
        self.rich_enabled = rich_enabled
        self.console = console

    def show_header(self):
        """Show the fancy header. If we're in Rich mode."""
        if self.rich_enabled:
            print_header("Git Repository Manager")

    def show_mode_warnings(self, args):
        """Warn about dry-run, status-only, whatever mode we're in."""
        if not self.rich_enabled:
            return

        if args.dry_run:
            self.console.print(
                (
                    "[dim yellow]⚠[/]  "
                    "[yellow]dry run mode[/] "
                    "[dim]— no changes will be made[/]\n"
                )
            )

        if args.status_only:
            mode_text = "[dim cyan]ℹ[/]  [cyan]status only mode[/]"
            if args.compact:
                mode_text += " [dim]— compact display for clean repos[/]"
            self.console.print(f"{mode_text}\n")

    def show_repository_summary(self, repo_count: int, message: str = ""):
        """Tell em how many repos we found."""
        if not self.rich_enabled:
            return

        if message:
            self.console.print(
                f"[dim]{message}[/]\n",
            )

        self.console.print(
            f"[white]Found[/] [bold]{repo_count}[/] [white]repositories[/]\n",
        )

    def confirm_processing(self, repo_count: int) -> bool:
        """Are you sure you wanna do this? Y/n"""
        if not self.rich_enabled:
            return True

        if not Confirm.ask(
            f"Process {repo_count} repositories?",
            default=True,
        ):
            self.console.print("[dim yellow]cancelled[/]")
            return False

        return True

    def show_final_summary(self, args, stats, total: int):
        """The victory lap. How many did we process?"""
        if not self.rich_enabled:
            return

        self.console.print()

        if args.status_only and args.compact:
            self._show_compact_summary(stats, total)
        else:
            self._show_standard_summary(
                stats.success_count,
                total,
            )

    def _show_compact_summary(self, stats, total: int):
        """Quick summary. Clean vs dirty counts."""
        self.console.print("[dim]Summary:[/]")
        self.console.print(
            f"  [green]✓[/] [dim]clean:[/] [green]{
                stats.clean_count
            }[/]"
        )
        self.console.print(
            f"  [yellow]●[/] [dim]with changes:[/] [yellow]{
                stats.dirty_count
            }[/]"
        )
        self.console.print(f"  [dim]total:[/] [white]{total}[/]")
        self.console.print()

    def _show_standard_summary(self, success_count: int, total: int):
        """Standard summary. X/Y processed, green if all good."""
        all_success = success_count == total
        status = "✓" if all_success else "◆"
        color = "green" if all_success else "yellow"

        self.console.print(
            f"[{color}]{status}[/] "
            f"[white]Processed[/] [bold]{success_count}/{total}[/] "
            f"[dim]repositories[/]"
        )
        self.console.print()
