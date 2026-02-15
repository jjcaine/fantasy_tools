"""Lineup Optimizer screen — placeholder for Phase 3."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Static

from src.tui.screens.help import HelpScreen

HELP_TEXT = """\
Lineup Optimizer

View your game calendar, GP budget tracker,
optimal daily lineups, and streaming recommendations.

Coming in Phase 3.
"""


class LineupScreen(Screen):
    """Lineup optimization screen (placeholder)."""

    BINDINGS = [("question_mark", "show_help", "Help")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(
            "Lineup Optimizer — coming in Phase 3\n\nPress [bold]?[/bold] for help",
            classes="placeholder-label",
        )

    def action_show_help(self) -> None:
        self.app.push_screen(HelpScreen("Lineup Help", HELP_TEXT))
