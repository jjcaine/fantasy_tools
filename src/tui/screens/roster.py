"""Roster Analysis screen — player breakdown and category ranks."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Label, LoadingIndicator, Select, Static
from textual import work

from src.config import get_my_team
from src.tui.screens.base import BaseScreen
from src.tui.screens.help import HelpScreen

HELP_TEXT = """\
Roster Analysis

View your roster breakdown with per-game stats,
period projections, and category rank analysis.

Panel 1 — Player Breakdown:
  Per-game stats and projected games for each player

Panel 2 — Category Ranks:
  Your team's projected rank (1-8) in each category
  Green = top 3 (strength), Red = bottom 3 (weakness)

Keybindings:
  ?      Show this help
"""


class RosterScreen(BaseScreen):
    """Roster analysis screen."""

    DEFAULT_CSS = """
    #roster-controls {
        height: 3;
        padding: 0 1;
    }
    #roster-controls Select {
        width: 1fr;
    }
    #roster-players {
        height: 1fr;
        margin: 0 1;
    }
    #roster-ranks {
        height: auto;
        max-height: 14;
        margin: 0 1;
    }
    #roster-loading {
        height: 100%;
    }
    #roster-error {
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
        yield LoadingIndicator(id="roster-loading")
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
        self.query_one("#roster-loading").remove()
        self.mount(
            Static(
                f"Data files missing — press [bold]d[/bold] to refresh\n\n{error}",
                id="roster-error",
            )
        )
        self.notify(f"Roster data error: {error}", severity="error")

    def _on_data_loaded(self, players, rosters, schedule) -> None:
        self._players = players
        self._rosters = rosters
        self._schedule = schedule
        self._periods = sorted(schedule.keys(), key=lambda k: int(k))
        self._loading = False

        self.query_one("#roster-loading").remove()

        period_options = [(f"Period {p}", p) for p in self._periods]
        controls = Horizontal(id="roster-controls")
        self.mount(controls)
        controls.mount(
            Select(period_options, prompt="Period", id="period-select",
                   value=self._periods[0] if self._periods else Select.BLANK),
        )

        self.mount(Label(f"[bold]{self._my_team}[/bold] — Roster Breakdown", id="roster-title"))

        player_table = DataTable(id="roster-players")
        self.mount(player_table)
        player_table.add_columns(
            "Player", "Team", "GP", "MPG", "PPG", "RPG", "APG",
            "SPG", "BPG", "TOPG", "3PM", "AdjFG%", "FT%", "Games",
        )

        self.mount(Label("[bold]Category Ranks (1=best, 8=worst)[/bold]"))
        rank_table = DataTable(id="roster-ranks")
        self.mount(rank_table)
        from src.fantasy_math import CATEGORIES
        rank_table.add_columns("Category", "Value", "Rank", "Label")

        self._refresh_roster()

    def on_select_changed(self, event: Select.Changed) -> None:
        if not self._loading:
            try:
                self._refresh_roster()
            except Exception as e:
                self.notify(f"Error refreshing roster: {e}", severity="error")

    def _refresh_roster(self) -> None:
        try:
            period_sel = self.query_one("#period-select", Select)
        except Exception:
            return

        period = period_sel.value
        if period is Select.BLANK:
            return

        from src.fantasy_math import (
            CATEGORIES,
            build_player_lookup,
            build_team_roster_lines,
            get_player_games_in_period,
            project_team_week,
            get_all_team_projections,
        )

        lookup = build_player_lookup(self._players)
        lines, matched, unmatched = build_team_roster_lines(
            self._my_team, self._rosters, self._players, lookup
        )
        games_map = get_player_games_in_period(lines, self._schedule, int(period))

        # Player breakdown table
        player_table = self.query_one("#roster-players", DataTable)
        player_table.clear()
        for cl in lines:
            gp = games_map.get(cl.name, 0)
            player_table.add_row(
                cl.name, cl.team, str(cl.games), f"{cl.mpg:.1f}",
                f"{cl.pts_pg:.1f}", f"{cl.reb_pg:.1f}", f"{cl.ast_pg:.1f}",
                f"{cl.stl_pg:.1f}", f"{cl.blk_pg:.1f}", f"{cl.to_pg:.1f}",
                f"{cl.tpm_pg:.1f}",
                f"{cl.adj_fg_pct:.3f}" if cl.adj_fg_pct is not None else "—",
                f"{cl.ft_pct:.3f}" if cl.ft_pct is not None else "—",
                str(gp),
            )

        # Category ranks
        all_projs = get_all_team_projections(
            self._rosters, self._players, self._schedule, int(period)
        )

        rank_table = self.query_one("#roster-ranks", DataTable)
        rank_table.clear()

        my_proj = all_projs.get(self._my_team)
        if my_proj is None:
            return

        for cat in CATEGORIES:
            my_val = my_proj.cats.get(cat, 0)
            # Rank among all teams
            all_vals = []
            for team_name, proj in all_projs.items():
                all_vals.append((team_name, proj.cats.get(cat, 0)))
            # Sort: higher is better, except TO (lower is better)
            from src.fantasy_math import INVERSE_CATS
            reverse = cat not in INVERSE_CATS
            all_vals.sort(key=lambda x: x[1], reverse=reverse)
            rank = next(i + 1 for i, (t, _) in enumerate(all_vals) if t == self._my_team)

            if rank <= 3:
                label = "[green]Strength[/green]"
            elif rank >= 6:
                label = "[red]Weakness[/red]"
            else:
                label = "Average"

            fmt = f"{my_val:.3f}" if cat in ("AdjFG%", "FT%") else f"{my_val:.1f}"
            rank_table.add_row(cat, fmt, str(rank), label)

    def action_show_help(self) -> None:
        self.app.push_screen(HelpScreen("Roster Help", HELP_TEXT))
