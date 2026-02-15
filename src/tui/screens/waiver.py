"""Waiver Optimizer screen — FA rankings, best-per-category, swap simulator."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Header, Label, LoadingIndicator, Select, Static
from textual import work

from src.config import get_my_team
from src.tui.screens.help import HelpScreen

HELP_TEXT = """\
Waiver Optimizer

Evaluate free agents and simulate roster swaps.

Panel 1 — Free Agent Rankings:
  Ranked by schedule-adjusted composite z-score
  Higher = more valuable for this period

Panel 2 — Best Available Per Category:
  Top 5 free agents for each of the 9 categories

Panel 3 — Swap Simulator:
  Select a player to drop and a FA to add
  Shows before/after projected team category totals

Keybindings:
  ?      Show this help
"""


class WaiverScreen(Screen):
    """Waiver wire analysis screen."""

    BINDINGS = [("question_mark", "show_help", "Help")]

    DEFAULT_CSS = """
    #waiver-controls {
        height: 3;
        padding: 0 1;
    }
    #waiver-controls Select {
        width: 1fr;
        margin-right: 1;
    }
    #fa-table {
        height: 1fr;
        margin: 0 1;
    }
    #best-per-cat {
        height: auto;
        max-height: 14;
        margin: 0 1;
    }
    #swap-controls {
        height: 3;
        padding: 0 1;
    }
    #swap-controls Select {
        width: 1fr;
        margin-right: 1;
    }
    #swap-result {
        height: auto;
        max-height: 14;
        margin: 0 1;
    }
    #waiver-loading {
        height: 100%;
    }
    #waiver-error {
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
        self._free_agents: list | None = None
        self._periods: list[str] = []
        self._fa_z_data: list[dict] = []
        self._roster_lines = []
        self._lookup = {}
        self._loading = True

    def compose(self) -> ComposeResult:
        yield Header()
        yield LoadingIndicator(id="waiver-loading")

    def on_mount(self) -> None:
        self._load_data()

    @work(exclusive=True, thread=True)
    def _load_data(self) -> None:
        try:
            from src.fantasy_math import (
                load_a10_players, load_fantrax_rosters, load_schedule,
                load_free_agents, build_player_lookup,
            )
            players = load_a10_players()
            rosters = load_fantrax_rosters()
            schedule = load_schedule()
            free_agents = load_free_agents()
            self.app.call_from_thread(
                self._on_data_loaded, players, rosters, schedule, free_agents
            )
        except Exception as e:
            self.app.call_from_thread(self._on_data_error, str(e))

    def _on_data_error(self, error: str) -> None:
        self.query_one("#waiver-loading").remove()
        self.mount(
            Static(
                f"Data files missing — press [bold]d[/bold] to refresh\n\n{error}",
                id="waiver-error",
            )
        )
        self.notify(f"Waiver data error: {error}", severity="error")

    def _on_data_loaded(self, players, rosters, schedule, free_agents) -> None:
        self._players = players
        self._rosters = rosters
        self._schedule = schedule
        self._free_agents = free_agents
        self._periods = sorted(schedule.keys(), key=lambda k: int(k))
        self._loading = False

        from src.fantasy_math import build_player_lookup
        self._lookup = build_player_lookup(players)

        self.query_one("#waiver-loading").remove()

        period_options = [(f"Period {p}", p) for p in self._periods]
        controls = Horizontal(id="waiver-controls")
        self.mount(controls)
        controls.mount(
            Select(period_options, prompt="Period", id="period-select",
                   value=self._periods[0] if self._periods else Select.BLANK),
        )

        # FA rankings table
        self.mount(Label("[bold]Free Agent Rankings[/bold] (by schedule-adjusted z)"))
        fa_table = DataTable(id="fa-table")
        self.mount(fa_table)
        fa_table.add_columns("Rank", "Player", "Team", "GP", "Comp Z", "Sched Z")

        # Best per category
        self.mount(Label("[bold]Best Available Per Category[/bold] (top 5)"))
        best_table = DataTable(id="best-per-cat")
        self.mount(best_table)
        from src.fantasy_math import CATEGORIES
        best_table.add_columns("Category", "#1", "#2", "#3", "#4", "#5")

        # Swap simulator
        self.mount(Label("[bold]Swap Simulator[/bold]"))
        swap_controls = Horizontal(id="swap-controls")
        self.mount(swap_controls)
        swap_controls.mount(
            Select([], prompt="Drop player", id="drop-select", value=Select.BLANK),
            Select([], prompt="Add player", id="add-select", value=Select.BLANK),
        )
        swap_table = DataTable(id="swap-result")
        self.mount(swap_table)
        swap_table.add_columns("Category", "Before", "After", "Change")

        self._refresh_waiver()

    def on_select_changed(self, event: Select.Changed) -> None:
        if self._loading:
            return
        try:
            if event.select.id in ("drop-select", "add-select"):
                self._refresh_swap()
            else:
                self._refresh_waiver()
        except Exception as e:
            self.notify(f"Error refreshing waivers: {e}", severity="error")

    def _refresh_waiver(self) -> None:
        try:
            period_sel = self.query_one("#period-select", Select)
        except Exception:
            return

        period = period_sel.value
        if period is Select.BLANK:
            return

        from src.fantasy_math import (
            CATEGORIES, compute_z_scores, composite_z_score,
            schedule_adjusted_composite, build_team_roster_lines,
            match_player, normalize_fantrax_team,
        )

        # Identify rostered player names to exclude
        rostered_names = set()
        for team_name, team_data in self._rosters.items():
            for p in team_data.get("players", []):
                rostered_names.add(p.get("name", "").lower())

        # Match free agents to NCAA stats
        fa_matched = []
        for fa in self._free_agents:
            fa_name = fa.get("name", "")
            fa_team = fa.get("team", "")
            ncaa = match_player(fa_name, fa_team, self._lookup, self._players)
            if ncaa:
                fa_matched.append(ncaa)

        # Compute z-scores for FA pool
        fa_z = compute_z_scores(fa_matched, min_games=3, min_mpg=5.0)

        period_key = str(period)
        period_data = self._schedule.get(period_key, {})
        games_per_team = period_data.get("games_per_team", {})

        for row in fa_z:
            row["composite"] = composite_z_score(row["z_scores"])
            team_games = games_per_team.get(row["team"], 0)
            row["sched_adj"] = schedule_adjusted_composite(row["z_scores"], team_games)

        fa_z.sort(key=lambda r: r["sched_adj"], reverse=True)
        self._fa_z_data = fa_z

        # FA rankings table
        fa_table = self.query_one("#fa-table", DataTable)
        fa_table.clear()
        for i, row in enumerate(fa_z[:50], 1):
            fa_table.add_row(
                str(i), row["name"], row["team"], str(row["games"]),
                f"{row['composite']:.2f}", f"{row['sched_adj']:.2f}",
            )

        # Best per category
        best_table = self.query_one("#best-per-cat", DataTable)
        best_table.clear()
        for cat in CATEGORIES:
            sorted_fa = sorted(
                fa_z,
                key=lambda r: r["z_scores"].get(cat) or -999,
                reverse=True,
            )
            top5 = [f"{r['name']} ({r['z_scores'].get(cat, 0):.1f})" for r in sorted_fa[:5]]
            while len(top5) < 5:
                top5.append("—")
            best_table.add_row(cat, *top5)

        # Populate swap selectors
        lines, _, _ = build_team_roster_lines(
            self._my_team, self._rosters, self._players, self._lookup
        )
        self._roster_lines = lines

        drop_options = [(cl.name, cl.name) for cl in lines]
        add_options = [(r["name"], r["name"]) for r in fa_z[:30]]

        drop_sel = self.query_one("#drop-select", Select)
        add_sel = self.query_one("#add-select", Select)
        drop_sel.set_options(drop_options)
        add_sel.set_options(add_options)

    def _refresh_swap(self) -> None:
        try:
            period_sel = self.query_one("#period-select", Select)
            drop_sel = self.query_one("#drop-select", Select)
            add_sel = self.query_one("#add-select", Select)
        except Exception:
            return

        period = period_sel.value
        drop_name = drop_sel.value
        add_name = add_sel.value

        if period is Select.BLANK or drop_name is Select.BLANK or add_name is Select.BLANK:
            return

        from src.fantasy_math import (
            CATEGORIES, PCT_CATS, player_to_cat_line, match_player,
            get_player_games_in_period, project_team_week,
        )

        # Before: current roster projection
        before_games = get_player_games_in_period(self._roster_lines, self._schedule, int(period))
        before_proj = project_team_week(
            self._roster_lines, before_games, period=int(period), team_name=self._my_team
        )

        # After: swap drop for add
        add_player = None
        for row in self._fa_z_data:
            if row["name"] == add_name:
                add_player = row
                break
        if add_player is None:
            return

        # Find the NCAA stats dict for the add player
        add_ncaa = match_player(add_name, add_player["team"], self._lookup, self._players)
        if add_ncaa is None:
            return
        add_line = player_to_cat_line(add_ncaa)

        new_lines = [cl for cl in self._roster_lines if cl.name != drop_name]
        new_lines.append(add_line)

        after_games = get_player_games_in_period(new_lines, self._schedule, int(period))
        after_proj = project_team_week(
            new_lines, after_games, period=int(period), team_name=self._my_team
        )

        swap_table = self.query_one("#swap-result", DataTable)
        swap_table.clear()
        for cat in CATEGORIES:
            before_val = before_proj.cats.get(cat, 0)
            after_val = after_proj.cats.get(cat, 0)
            diff = after_val - before_val

            fmt = ".3f" if cat in PCT_CATS else ".1f"
            if diff > 0.001:
                change = f"[green]+{diff:{fmt}}[/green]"
            elif diff < -0.001:
                change = f"[red]{diff:{fmt}}[/red]"
            else:
                change = f"{diff:{fmt}}"

            swap_table.add_row(
                cat, f"{before_val:{fmt}}", f"{after_val:{fmt}}", change
            )

    def action_show_help(self) -> None:
        self.app.push_screen(HelpScreen("Waiver Help", HELP_TEXT))
