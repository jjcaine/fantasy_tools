"""Player Rankings screen — z-score rankings with filters and sorting."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import DataTable, Header, Input, Label, LoadingIndicator, Select, Static
from textual import work

from src.tui.screens.help import HelpScreen

HELP_TEXT = """\
Player Rankings

View z-score rankings for all A-10 players.

Controls:
  Period         Scoring period for schedule adjustment
  Min GP         Minimum games played filter
  Min MPG        Minimum minutes per game filter
  Sort by        Column to sort by (descending)

Columns:
  Composite Z    Sum of all 9 category z-scores
  Sched-Adj Z    Composite weighted by team's game count
  Per-category   Individual z-scores for each of the 9 cats

Keybindings:
  ?      Show this help
"""

SORT_OPTIONS = [
    ("Composite Z", "composite"),
    ("Sched-Adj Z", "sched_adj"),
    ("AdjFG%", "AdjFG%"),
    ("3PTM", "3PTM"),
    ("FT%", "FT%"),
    ("PTS", "PTS"),
    ("REB", "REB"),
    ("AST", "AST"),
    ("ST", "ST"),
    ("BLK", "BLK"),
    ("TO", "TO"),
]


class RankingsScreen(Screen):
    """Player z-score rankings screen."""

    BINDINGS = [("question_mark", "show_help", "Help")]

    DEFAULT_CSS = """
    #rankings-controls {
        height: 3;
        padding: 0 1;
    }
    #rankings-controls Select {
        width: 1fr;
        margin-right: 1;
    }
    #rankings-controls Input {
        width: 12;
        margin-right: 1;
    }
    #rankings-table {
        height: 1fr;
        margin: 0 1;
    }
    #rankings-loading {
        height: 100%;
    }
    #rankings-error {
        height: 100%;
        content-align: center middle;
        color: $error;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._players: list | None = None
        self._schedule: dict | None = None
        self._periods: list[str] = []
        self._z_data: list[dict] = []
        self._loading = True

    def compose(self) -> ComposeResult:
        yield Header()
        yield LoadingIndicator(id="rankings-loading")

    def on_mount(self) -> None:
        self._load_data()

    @work(exclusive=True, thread=True)
    def _load_data(self) -> None:
        try:
            from src.fantasy_math import load_a10_players, load_schedule
            players = load_a10_players()
            schedule = load_schedule()
            self.app.call_from_thread(self._on_data_loaded, players, schedule)
        except Exception as e:
            self.app.call_from_thread(self._on_data_error, str(e))

    def _on_data_error(self, error: str) -> None:
        self.query_one("#rankings-loading").remove()
        self.mount(
            Static(
                f"Data files missing — press [bold]d[/bold] to refresh\n\n{error}",
                id="rankings-error",
            )
        )
        self.notify(f"Rankings data error: {error}", severity="error")

    def _on_data_loaded(self, players, schedule) -> None:
        self._players = players
        self._schedule = schedule
        self._periods = sorted(schedule.keys(), key=lambda k: int(k))
        self._loading = False

        self.query_one("#rankings-loading").remove()

        period_options = [(f"Period {p}", p) for p in self._periods]

        controls = Horizontal(id="rankings-controls")
        self.mount(controls)
        controls.mount(
            Select(period_options, prompt="Period", id="period-select",
                   value=self._periods[0] if self._periods else Select.BLANK),
            Input(value="5", placeholder="Min GP", id="min-gp-input", type="integer"),
            Input(value="10", placeholder="Min MPG", id="min-mpg-input", type="number"),
            Select(SORT_OPTIONS, prompt="Sort by", id="sort-select", value="composite"),
        )

        table = DataTable(id="rankings-table")
        self.mount(table)
        table.add_columns(
            "Player", "Team", "GP", "MPG", "Comp Z", "Sched Z",
            "AdjFG%", "3PTM", "FT%", "PTS", "REB", "AST", "ST", "BLK", "TO",
        )

        self._refresh_rankings()

    def on_select_changed(self, event: Select.Changed) -> None:
        if not self._loading:
            try:
                self._refresh_rankings()
            except Exception as e:
                self.notify(f"Error refreshing rankings: {e}", severity="error")

    def on_input_changed(self, event: Input.Changed) -> None:
        if not self._loading:
            try:
                self._refresh_rankings()
            except Exception as e:
                self.notify(f"Error refreshing rankings: {e}", severity="error")

    def _refresh_rankings(self) -> None:
        try:
            period_sel = self.query_one("#period-select", Select)
            min_gp_input = self.query_one("#min-gp-input", Input)
            min_mpg_input = self.query_one("#min-mpg-input", Input)
            sort_sel = self.query_one("#sort-select", Select)
        except Exception:
            return

        period = period_sel.value
        if period is Select.BLANK:
            return

        try:
            min_gp = int(min_gp_input.value) if min_gp_input.value else 5
        except ValueError:
            min_gp = 5
        try:
            min_mpg = float(min_mpg_input.value) if min_mpg_input.value else 10.0
        except ValueError:
            min_mpg = 10.0

        sort_key = sort_sel.value if sort_sel.value is not Select.BLANK else "composite"

        from src.fantasy_math import compute_z_scores, composite_z_score, schedule_adjusted_composite

        z_data = compute_z_scores(self._players, min_games=min_gp, min_mpg=min_mpg)

        period_key = str(period)
        period_data = self._schedule.get(period_key, {})
        games_per_team = period_data.get("games_per_team", {})

        for row in z_data:
            row["composite"] = composite_z_score(row["z_scores"])
            team_games = games_per_team.get(row["team"], 0)
            row["sched_adj"] = schedule_adjusted_composite(row["z_scores"], team_games)

        if sort_key == "composite":
            z_data.sort(key=lambda r: r["composite"], reverse=True)
        elif sort_key == "sched_adj":
            z_data.sort(key=lambda r: r["sched_adj"], reverse=True)
        else:
            z_data.sort(key=lambda r: r["z_scores"].get(sort_key) or -999, reverse=True)

        self._z_data = z_data

        table = self.query_one("#rankings-table", DataTable)
        table.clear()
        from src.fantasy_math import CATEGORIES
        for row in z_data:
            zs = row["z_scores"]
            cat_vals = []
            for cat in CATEGORIES:
                v = zs.get(cat)
                cat_vals.append(f"{v:.2f}" if v is not None else "—")
            table.add_row(
                row["name"],
                row["team"],
                str(row["games"]),
                f"{row['mpg']:.1f}",
                f"{row['composite']:.2f}",
                f"{row['sched_adj']:.2f}",
                *cat_vals,
            )

    def action_show_help(self) -> None:
        self.app.push_screen(HelpScreen("Rankings Help", HELP_TEXT))
