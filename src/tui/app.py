"""Fantasy Tools TUI — main application."""

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header

from src.config import get_my_team
from src.tui.screens.data_refresh import DataRefreshScreen
from src.tui.screens.lineup import LineupScreen
from src.tui.screens.matchup import MatchupScreen
from src.tui.screens.rankings import RankingsScreen
from src.tui.screens.roster import RosterScreen
from src.tui.screens.waiver import WaiverScreen

SCREEN_MAP = {
    "data_refresh": DataRefreshScreen,
    "matchup": MatchupScreen,
    "rankings": RankingsScreen,
    "roster": RosterScreen,
    "waiver": WaiverScreen,
    "lineup": LineupScreen,
}


class FantasyApp(App):
    """A keyboard-driven TUI for fantasy basketball analysis."""

    TITLE = "Fantasy Tools"
    CSS_PATH = "styles/app.tcss"

    BINDINGS = [
        ("d", "goto('data_refresh')", "Data Refresh"),
        ("m", "goto('matchup')", "Matchup"),
        ("r", "goto('rankings')", "Rankings"),
        ("t", "goto('roster')", "Roster"),
        ("w", "goto('waiver')", "Waivers"),
        ("l", "goto('lineup')", "Lineup"),
        ("q", "quit", "Quit"),
        ("question_mark", "help", "Help"),
    ]

    SCREENS = {
        "data_refresh": DataRefreshScreen,
        "matchup": MatchupScreen,
        "rankings": RankingsScreen,
        "roster": RosterScreen,
        "waiver": WaiverScreen,
        "lineup": LineupScreen,
    }

    def on_mount(self) -> None:
        self.sub_title = get_my_team()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

    def action_goto(self, screen_name: str) -> None:
        # Pop back to default screen first, then push the target
        while len(self.screen_stack) > 1:
            self.pop_screen()
        self.push_screen(screen_name)

    def action_help(self) -> None:
        from src.tui.screens.help import HelpScreen
        self.push_screen(
            HelpScreen(
                "Fantasy Tools Help",
                (
                    "Keybindings:\n"
                    "  d  Data Refresh\n"
                    "  m  Matchup Dashboard\n"
                    "  r  Player Rankings\n"
                    "  t  Roster Analysis\n"
                    "  w  Waiver Optimizer\n"
                    "  l  Lineup Optimizer\n"
                    "  q  Quit\n"
                    "  ?  This help screen\n"
                ),
            )
        )


def main() -> None:
    app = FantasyApp()
    app.run()


if __name__ == "__main__":
    main()
