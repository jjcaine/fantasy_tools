"""Waiver Optimizer screen — placeholder for Phase 3."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Static

from src.tui.screens.help import HelpScreen

HELP_TEXT = """\
Waiver Optimizer

Evaluate free agents by schedule-adjusted z-score,
find best available per category, and simulate
drop/add swaps with before/after projections.

Coming in Phase 3.
"""


class WaiverScreen(Screen):
    """Waiver wire analysis screen (placeholder)."""

    BINDINGS = [("question_mark", "show_help", "Help")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(
            "Waiver Optimizer — coming in Phase 3\n\nPress [bold]?[/bold] for help",
            classes="placeholder-label",
        )

    def action_show_help(self) -> None:
        self.app.push_screen(HelpScreen("Waiver Help", HELP_TEXT))
