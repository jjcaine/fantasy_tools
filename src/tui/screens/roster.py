"""Roster Analysis screen — placeholder for Phase 3."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Static

from src.tui.screens.help import HelpScreen

HELP_TEXT = """\
Roster Analysis

View your roster breakdown with per-game stats,
period projections, and category rank analysis.

Coming in Phase 3.
"""


class RosterScreen(Screen):
    """Roster analysis screen (placeholder)."""

    BINDINGS = [("question_mark", "show_help", "Help")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(
            "Roster Analysis — coming in Phase 3\n\nPress [bold]?[/bold] for help",
            classes="placeholder-label",
        )

    def action_show_help(self) -> None:
        self.app.push_screen(HelpScreen("Roster Help", HELP_TEXT))
