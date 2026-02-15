"""Player Rankings screen — placeholder for Phase 3."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Static

from src.tui.screens.help import HelpScreen

HELP_TEXT = """\
Player Rankings

View z-score rankings for all A-10 players,
filterable by games played, minutes, and sortable
by composite or per-category z-scores.

Coming in Phase 3.
"""


class RankingsScreen(Screen):
    """Player z-score rankings screen (placeholder)."""

    BINDINGS = [("question_mark", "show_help", "Help")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(
            "Player Rankings — coming in Phase 3\n\nPress [bold]?[/bold] for help",
            classes="placeholder-label",
        )

    def action_show_help(self) -> None:
        self.app.push_screen(HelpScreen("Rankings Help", HELP_TEXT))
