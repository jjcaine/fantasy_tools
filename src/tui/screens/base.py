"""Base screen with shared navigation bindings and footer."""

from textual.screen import Screen


class BaseScreen(Screen):
    """Base class for all TUI screens — provides navigation keybindings."""

    BINDINGS = [
        ("escape", "go_home", "Home"),
        ("d", "goto('data_refresh')", "Data Refresh"),
        ("m", "goto('matchup')", "Matchup"),
        ("r", "goto('rankings')", "Rankings"),
        ("t", "goto('roster')", "Roster"),
        ("w", "goto('waiver')", "Waivers"),
        ("l", "goto('lineup')", "Lineup"),
        ("q", "quit", "Quit"),
        ("question_mark", "show_help", "Help"),
    ]

    def action_go_home(self) -> None:
        """Pop back to the default (home) screen."""
        while len(self.app.screen_stack) > 1:
            self.app.pop_screen()
        from src.config import get_my_team
        self.app.sub_title = get_my_team()

    def action_goto(self, screen_name: str) -> None:
        """Switch to a named screen."""
        # Pop to home first, then push target
        while len(self.app.screen_stack) > 1:
            self.app.pop_screen()
        from src.tui.app import FantasyApp
        self.app.sub_title = FantasyApp.SCREEN_TITLES.get(screen_name, screen_name)
        self.app.push_screen(screen_name)

    def action_show_help(self) -> None:
        """Override in subclasses to show screen-specific help."""
        pass
