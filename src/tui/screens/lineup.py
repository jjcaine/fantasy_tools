"""Lineup Optimizer screen — game calendar, GP tracker, optimal lineup, streaming."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Input, Label, LoadingIndicator, Select, Static
from textual import work

from src.config import get_my_team, get_gp_max
from src.tui.screens.base import BaseScreen
from src.tui.screens.help import HelpScreen

HELP_TEXT = """\
Lineup Optimizer

Optimize your daily lineups within the GP budget.

Panel 1 — Game Calendar:
  Player rows x date columns, showing who plays when

Panel 2 — GP Budget Tracker:
  Total available starts vs GP max

Panel 3 — Optimal Daily Lineup:
  Greedy by z-score value, respecting GP budget
  Higher-value players are started over lower-value ones

Panel 4 — Streaming Recommendations:
  Days with open roster spots and best available FAs

Controls:
  Period         Scoring period
  GP Max         Maximum games played (editable)

Keybindings:
  ?      Show this help
"""


class LineupScreen(BaseScreen):
    """Lineup optimization screen."""

    DEFAULT_CSS = """
    #lineup-controls {
        height: 3;
        padding: 0 1;
    }
    #lineup-controls Select {
        width: 1fr;
        margin-right: 1;
    }
    #lineup-controls Input {
        width: 12;
        margin-right: 1;
    }
    #gp-tracker {
        height: 2;
        padding: 0 1;
    }
    #calendar-table {
        height: 1fr;
        max-height: 16;
        margin: 0 1;
    }
    #lineup-table {
        height: 1fr;
        margin: 0 1;
    }
    #streaming-label {
        padding: 0 1;
    }
    #streaming-table {
        height: auto;
        max-height: 10;
        margin: 0 1;
    }
    #lineup-loading {
        height: 100%;
    }
    #lineup-error {
        height: 100%;
        content-align: center middle;
        color: $error;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._my_team = get_my_team()
        self._players: list | None = None
        self._rosters: dict | None = None
        self._schedule: dict | None = None
        self._periods: list[str] = []
        self._loading = True

    def compose(self) -> ComposeResult:
        yield Header()
        yield LoadingIndicator(id="lineup-loading")
        yield Footer()

    def on_mount(self) -> None:
        self._load_data()

    @work(exclusive=True, thread=True)
    def _load_data(self) -> None:
        try:
            from src.fantasy_math import load_a10_players, load_fantrax_rosters, load_schedule
            players = load_a10_players()
            rosters = load_fantrax_rosters()
            schedule = load_schedule()
            self.app.call_from_thread(self._on_data_loaded, players, rosters, schedule)
        except Exception as e:
            self.app.call_from_thread(self._on_data_error, str(e))

    def _on_data_error(self, error: str) -> None:
        self.query_one("#lineup-loading").remove()
        self.mount(
            Static(
                f"Data files missing — press [bold]d[/bold] to refresh\n\n{error}",
                id="lineup-error",
            )
        )
        self.notify(f"Lineup data error: {error}", severity="error")

    def _on_data_loaded(self, players, rosters, schedule) -> None:
        self._players = players
        self._rosters = rosters
        self._schedule = schedule
        self._periods = sorted(schedule.keys(), key=lambda k: int(k))
        self._loading = False

        self.query_one("#lineup-loading").remove()

        self.mount(Static(
            "Optimize daily start/sit decisions within the GP budget. "
            "Higher-z players start first. Open slots are streaming opportunities.",
            classes="screen-intro",
        ))

        period_options = [(f"Period {p}", p) for p in self._periods]
        default_period = self._periods[0] if self._periods else Select.BLANK
        default_gp = get_gp_max(int(default_period)) if default_period is not Select.BLANK else 15

        controls = Horizontal(id="lineup-controls")
        self.mount(controls)
        controls.mount(
            Select(period_options, prompt="Period", id="period-select", value=default_period),
            Input(value=str(default_gp), placeholder="GP Max", id="gp-max-input", type="integer"),
        )

        self.mount(Label("", id="gp-tracker"))

        self.mount(Label("[bold]Game Calendar[/bold] — who plays when (X = game day)"))
        self.mount(DataTable(id="calendar-table"))

        self.mount(Label("[bold]Optimal Daily Lineup[/bold] — greedy by z-score, respecting GP max"))
        self.mount(DataTable(id="lineup-table"))

        self.mount(Label("[bold]Streaming Recommendations[/bold] — days with open roster spots and best available FAs", id="streaming-label"))
        self.mount(DataTable(id="streaming-table"))

        self._refresh_lineup()

    def on_select_changed(self, event: Select.Changed) -> None:
        if not self._loading:
            try:
                if event.select.id == "period-select" and event.value is not Select.BLANK:
                    gp_input = self.query_one("#gp-max-input", Input)
                    gp_input.value = str(get_gp_max(int(event.value)))
                self._refresh_lineup()
            except Exception as e:
                self.notify(f"Error refreshing lineup: {e}", severity="error")

    def on_input_changed(self, event: Input.Changed) -> None:
        if not self._loading:
            try:
                self._refresh_lineup()
            except Exception as e:
                self.notify(f"Error refreshing lineup: {e}", severity="error")

    def _refresh_lineup(self) -> None:
        try:
            period_sel = self.query_one("#period-select", Select)
            gp_input = self.query_one("#gp-max-input", Input)
        except Exception:
            return

        period = period_sel.value
        if period is Select.BLANK:
            return

        try:
            gp_max = int(gp_input.value) if gp_input.value else 15
        except ValueError:
            gp_max = 15

        from src.fantasy_math import (
            build_player_lookup, build_team_roster_lines,
            compute_z_scores, composite_z_score, optimize_lineup,
        )

        lookup = build_player_lookup(self._players)
        lines, matched_info, _ = build_team_roster_lines(
            self._my_team, self._rosters, self._players, lookup
        )

        period_key = str(period)
        period_data = self._schedule.get(period_key, {})
        game_dates = period_data.get("game_dates_per_team", {})

        # Compute z-scores for our roster
        our_z = compute_z_scores(
            [m["ncaa"] for m in matched_info], min_games=1, min_mpg=0
        )
        z_by_name = {r["name"]: composite_z_score(r["z_scores"]) for r in our_z}

        # All dates in period
        all_dates = sorted({d for dates in game_dates.values() for d in dates})

        # Game calendar
        cal_table = self.query_one("#calendar-table", DataTable)
        cal_table.clear(columns=True)
        date_cols = [d[5:] for d in all_dates]  # MM-DD format
        cal_table.add_columns("Player", "Team", "Z", "GP", *date_cols)

        cal_rows = []
        for cl in lines:
            team_dates = game_dates.get(cl.team, [])
            gp = len([d for d in team_dates if d in all_dates])
            z_val = z_by_name.get(cl.name, 0)
            day_marks = ["X" if d in team_dates else "" for d in all_dates]
            cal_rows.append((cl.name, cl.team, z_val, gp, day_marks))

        cal_rows.sort(key=lambda x: x[2], reverse=True)
        for name, team, z_val, gp, marks in cal_rows:
            cal_table.add_row(name, team, f"{z_val:.1f}", str(gp), *marks)

        # GP budget tracker
        total_available = sum(r[3] for r in cal_rows)
        tracker = self.query_one("#gp-tracker", Label)
        if total_available <= gp_max:
            tracker.update(
                f"Available: {total_available} | GP Max: {gp_max} — "
                "[green]Can start everyone, no benching needed[/green]"
            )
        else:
            tracker.update(
                f"Available: {total_available} | GP Max: {gp_max} — "
                f"[yellow]{total_available - gp_max} starts must be benched[/yellow]"
            )

        # Optimize lineup
        plan = optimize_lineup(lines, game_dates, z_by_name, gp_max=gp_max)

        lineup_table = self.query_one("#lineup-table", DataTable)
        lineup_table.clear(columns=True)
        lineup_table.add_columns("Date", "Playing", "Starting", "Benched", "Starters", "Benched Players", "Cum GP")
        for day in plan.days:
            benched_str = ", ".join(
                f"{p['name']} (z={p['value']:.1f})" for p in day.benched_players
            ) if day.benched_players else "—"
            lineup_table.add_row(
                day.date[5:] if len(day.date) > 5 else day.date,
                str(day.playing),
                str(day.starting),
                str(day.benched),
                ", ".join(day.starters) if day.starters else "—",
                benched_str,
                str(day.cumulative_gp),
            )

        # Streaming recommendations
        streaming_table = self.query_one("#streaming-table", DataTable)
        streaming_table.clear(columns=True)
        streaming_table.add_columns("Date", "Open Slots", "Best Available FAs")

        open_days = []
        for day in plan.days:
            if day.playing < 6:
                open_days.append((day.date, 6 - day.playing))

        if not open_days:
            streaming_table.add_row("—", "—", "No open slots — all days have full lineups")
        else:
            # Find FAs playing on open days
            from src.fantasy_math import match_player, load_free_agents
            try:
                free_agents = load_free_agents()
            except Exception:
                free_agents = []

            rostered_names = set()
            for team_data in self._rosters.values():
                for p in team_data.get("players", []):
                    ncaa = match_player(p["name"], p.get("team", ""), lookup, self._players)
                    if ncaa:
                        rostered_names.add(ncaa["name"])

            fa_players = [p for p in self._players if p["name"] not in rostered_names]
            fa_z = compute_z_scores(fa_players, min_games=5, min_mpg=10)

            for day_date, slots in open_days:
                teams_playing = [t for t, dates in game_dates.items() if day_date in dates]
                fas_playing = [r for r in fa_z if r["team"] in teams_playing]
                fas_playing.sort(key=lambda x: composite_z_score(x["z_scores"]), reverse=True)
                top = fas_playing[:5]
                if top:
                    names = ", ".join(
                        f"{r['name']} ({r['team']}, z={composite_z_score(r['z_scores']):+.1f})"
                        for r in top
                    )
                else:
                    names = "No qualified FAs playing"
                streaming_table.add_row(
                    day_date[5:] if len(day_date) > 5 else day_date,
                    str(slots),
                    names,
                )

    def action_show_help(self) -> None:
        self.app.push_screen(HelpScreen("Lineup Help", HELP_TEXT))
