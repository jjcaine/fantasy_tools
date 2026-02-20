"""Matchup Dashboard — H2H matchup analysis with projections."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Label, LoadingIndicator, Select, Static
from textual import work

from src.config import get_my_team
from src.tui.screens.base import BaseScreen
from src.tui.screens.help import HelpScreen
from src.tui.widgets.category_table import CategoryComparisonTable

HELP_TEXT = """\
Matchup Dashboard

Compare your team's projected stats against any opponent
for a given scoring period.

Controls:
  Period selector     Choose the scoring period
  Opponent selector   Choose an opponent to compare

Display:
  Result summary      Projected W-L-T result
  H2H table           9-category comparison with margins
  All-opponents       Projected results vs all teams

Color coding:
  Green   Category you're winning
  Red     Category you're losing
  Yellow  Tie

Keybindings:
  ?      Show this help
  Esc    Return to previous screen
"""


class MatchupScreen(BaseScreen):
    """H2H matchup analysis screen."""

    DEFAULT_CSS = """
    #matchup-controls {
        height: 3;
        padding: 0 1;
    }
    #matchup-controls Select {
        width: 1fr;
        margin-right: 1;
    }
    #result-summary {
        height: 1;
        padding: 0 1;
        text-style: bold;
    }
    #h2h-section {
        height: 1fr;
        margin: 0 1;
    }
    #overview-section {
        height: 1fr;
        margin: 0 1;
    }
    #overview-table {
        height: 1fr;
    }
    #matchup-loading {
        height: 100%;
    }
    #matchup-error {
        height: 100%;
        content-align: center middle;
        color: $error;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._my_team = get_my_team()
        self._all_projections: dict | None = None
        self._rosters: dict | None = None
        self._players: list | None = None
        self._schedule: dict | None = None
        self._periods: list[str] = []
        self._opponents: list[str] = []
        self._loading = True

    def compose(self) -> ComposeResult:
        yield Header()
        yield LoadingIndicator(id="matchup-loading")
        yield Footer()

    def on_mount(self) -> None:
        self._load_data()

    @work(exclusive=True, thread=True)
    def _load_data(self) -> None:
        """Load all data files in a background thread."""
        try:
            from src.fantasy_math import (
                load_a10_players,
                load_fantrax_rosters,
                load_schedule,
            )
            players = load_a10_players()
            rosters = load_fantrax_rosters()
            schedule = load_schedule()
            self.app.call_from_thread(
                self._on_data_loaded, players, rosters, schedule
            )
        except Exception as e:
            self.app.call_from_thread(self._on_data_error, str(e))

    def _on_data_error(self, error: str) -> None:
        self.query_one("#matchup-loading").remove()
        self.mount(
            Static(
                f"Data files missing or corrupt — press [bold]d[/bold] to refresh\n\n{error}",
                id="matchup-error",
            )
        )
        self.notify(f"Matchup data error: {error}", severity="error")

    def _on_data_loaded(self, players, rosters, schedule) -> None:
        self._players = players
        self._rosters = rosters
        self._schedule = schedule
        self._periods = sorted(schedule.keys(), key=lambda k: int(k))
        self._opponents = [t for t in sorted(rosters.keys()) if t != self._my_team]
        self._loading = False

        self.query_one("#matchup-loading").remove()

        self.mount(Static(
            "Compare your projected stats against an opponent. Pick a period and opponent, "
            "then check which 5 of 9 categories you're winning. "
            "Swing categories (small margins) are where waiver moves matter most.",
            classes="screen-intro",
        ))

        period_options = [(f"Period {p}", p) for p in self._periods]
        opponent_options = [(name, name) for name in self._opponents]

        controls = Horizontal(id="matchup-controls")
        self.mount(controls)
        controls.mount(
            Select(period_options, prompt="Period", id="period-select", value=self._periods[0] if self._periods else Select.BLANK),
            Select(opponent_options, prompt="Opponent", id="opponent-select", value=self._opponents[0] if self._opponents else Select.BLANK),
        )

        self.mount(Label("", id="result-summary"))

        h2h = Vertical(id="h2h-section")
        self.mount(h2h)
        h2h.mount(CategoryComparisonTable(id="cat-comparison"))

        overview = Vertical(id="overview-section")
        self.mount(overview)
        overview.mount(Label("[bold]All Opponents[/bold] — your projected record vs every team this period"))
        overview_table = DataTable(id="overview-table")
        overview.mount(overview_table)
        overview_table.add_columns("Opponent", "Result", "Our Wins", "Their Wins", "Ties")

        self._refresh_projection()

    def on_select_changed(self, event: Select.Changed) -> None:
        if not self._loading:
            try:
                self._refresh_projection()
            except Exception as e:
                self.notify(f"Error refreshing matchup: {e}", severity="error")

    def _refresh_projection(self) -> None:
        """Recompute projections based on current selector values."""
        try:
            period_sel = self.query_one("#period-select", Select)
            opp_sel = self.query_one("#opponent-select", Select)
        except Exception:
            return

        period = period_sel.value
        opponent = opp_sel.value

        if period is Select.BLANK or opponent is Select.BLANK:
            return

        from src.fantasy_math import (
            build_player_lookup,
            get_all_team_projections,
            predict_matchup,
        )

        lookup = build_player_lookup(self._players)
        all_projs = get_all_team_projections(
            self._rosters, self._players, self._schedule, int(period)
        )
        self._all_projections = all_projs

        my_proj = all_projs.get(self._my_team)
        opp_proj = all_projs.get(opponent)

        if my_proj is None or opp_proj is None:
            self.query_one("#result-summary", Label).update("Team not found in projections")
            return

        # H2H vs selected opponent
        result = predict_matchup(my_proj, opp_proj)
        self._update_h2h(result)

        # All-opponents overview
        self._update_overview(all_projs, my_proj)

    def _update_h2h(self, result) -> None:
        """Update the H2H display with a MatchupResult."""
        summary = self.query_one("#result-summary", Label)
        w, l, t = result.wins_a, result.wins_b, result.ties
        if w > l:
            color = "green"
            outcome = "WIN"
        elif w < l:
            color = "red"
            outcome = "LOSS"
        else:
            color = "yellow"
            outcome = "TIE"
        summary.update(
            f"Projected: [{color}]{result.result_str} {outcome}[/{color}] "
            f"vs {result.team_b}"
        )

        cat_table = self.query_one("#cat-comparison", CategoryComparisonTable)
        cat_table.update_result(result)

    def _update_overview(self, all_projs, my_proj) -> None:
        """Update the all-opponents overview table."""
        from src.fantasy_math import predict_matchup

        table = self.query_one("#overview-table", DataTable)
        table.clear()

        for team_name in sorted(all_projs.keys()):
            if team_name == self._my_team:
                continue
            opp_proj = all_projs[team_name]
            result = predict_matchup(my_proj, opp_proj)
            if result.wins_a > result.wins_b:
                outcome = "[green]WIN[/green]"
            elif result.wins_a < result.wins_b:
                outcome = "[red]LOSS[/red]"
            else:
                outcome = "[yellow]TIE[/yellow]"
            table.add_row(
                team_name,
                outcome,
                str(result.wins_a),
                str(result.wins_b),
                str(result.ties),
            )

    def action_show_help(self) -> None:
        self.app.push_screen(HelpScreen("Matchup Help", HELP_TEXT))
