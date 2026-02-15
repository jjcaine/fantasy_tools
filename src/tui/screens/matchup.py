"""Matchup Dashboard screen — placeholder for Phase 2."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Static

from src.tui.screens.help import HelpScreen

HELP_TEXT = """\
Matchup Dashboard

Compare your team's projected stats against any opponent
for a given scoring period.

Coming in Phase 2.
"""


class MatchupScreen(Screen):
    """H2H matchup analysis screen (placeholder)."""

    BINDINGS = [("question_mark", "show_help", "Help")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(
            "Matchup Dashboard — coming in Phase 2\n\nPress [bold]?[/bold] for help",
            classes="placeholder-label",
        )

    def action_show_help(self) -> None:
        self.app.push_screen(HelpScreen("Matchup Help", HELP_TEXT))
