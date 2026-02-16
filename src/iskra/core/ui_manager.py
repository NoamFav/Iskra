"""
UI Manager. Handles all the user-facing output and prompts.
"""

from rich.console import Console
from iskra.ui.formatting import print_header, style, get_color
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
                f"{style('⚠', 'warning')}  {style('dry run mode', 'warning')} {style('— no changes will be made', 'dim')}\n"
            )

        if args.status_only:
            mode_text = f"{style('ℹ', 'primary')}  {style('status only mode', 'primary')}"
            if args.compact:
                mode_text += f" {style('— compact display for clean repos', 'dim')}"
            self.console.print(f"{mode_text}\n")

    def show_repository_summary(self, repo_count: int, message: str = ""):
        """Tell em how many repos we found."""
        if not self.rich_enabled:
            return

        if message:
            self.console.print(f"{style(message, 'dim')}\n")

        self.console.print(
            f"Found {style(str(repo_count), 'highlight')} repositories\n"
        )

    def confirm_processing(self, repo_count: int) -> bool:
        """Are you sure you wanna do this? Y/n"""
        if not self.rich_enabled:
            return True

        if not Confirm.ask(
            f"Process {repo_count} repositories?",
            default=True,
        ):
            self.console.print(style("cancelled", "warning"))
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
        self.console.print(style("Summary:", "dim"))
        self.console.print(
            f"  {style('✓', 'success')} {style('clean:', 'dim')} {style(str(stats.clean_count), 'success')}"
        )
        self.console.print(
            f"  {style('●', 'warning')} {style('with changes:', 'dim')} {style(str(stats.dirty_count), 'warning')}"
        )
        self.console.print(f"  {style('total:', 'dim')} {style(str(total), 'highlight')}")
        self.console.print()

    def _show_standard_summary(self, success_count: int, total: int):
        """Standard summary. X/Y processed, green if all good."""
        all_success = success_count == total
        status = "✓" if all_success else "◆"
        color_key = "success" if all_success else "warning"

        self.console.print(
            f"{style(status, color_key)} Processed {style(f'{success_count}/{total}', 'highlight')} {style('repositories', 'dim')}"
        )
        self.console.print()
