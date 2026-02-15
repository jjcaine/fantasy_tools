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

    def on_mount(self) -> None:
        self.sub_title = get_my_team()
        # install_screen preserves instances between switches
        self.install_screen(DataRefreshScreen(), name="data_refresh")
        self.install_screen(MatchupScreen(), name="matchup")
        self.install_screen(RankingsScreen(), name="rankings")
        self.install_screen(RosterScreen(), name="roster")
        self.install_screen(WaiverScreen(), name="waiver")
        self.install_screen(LineupScreen(), name="lineup")

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

    SCREEN_TITLES = {
        "data_refresh": "Data Refresh",
        "matchup": "Matchup Dashboard",
        "rankings": "Player Rankings",
        "roster": "Roster Analysis",
        "waiver": "Waiver Optimizer",
        "lineup": "Lineup Optimizer",
    }

    def action_goto(self, screen_name: str) -> None:
        # Pop back to default screen first, then push the target
        while len(self.screen_stack) > 1:
            self.pop_screen()
        self.sub_title = self.SCREEN_TITLES.get(screen_name, screen_name)
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
