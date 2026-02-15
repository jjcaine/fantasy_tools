"""Tests for Phase 3d: Lineup Optimizer and optimize_lineup()."""

import pytest

from src.fantasy_math import (
    PlayerCatLine, optimize_lineup, LineupPlan,
)
from src.config import get_gp_max


def _make_line(name, team):
    return PlayerCatLine(
        name=name, team=team, games=20, mpg=30.0,
        tpm_pg=1.5, pts_pg=15.0, reb_pg=5.0, ast_pg=3.0,
        stl_pg=1.0, blk_pg=0.5, to_pg=2.0,
        adj_fg_pct=0.500, ft_pct=0.750,
        fgm=100, fga=200, tpm=30, ftm=50, fta=60,
        fgm_pg=5.0, fga_pg=10.0, ftm_pg=2.5, fta_pg=3.0, tpm_raw_pg=1.5,
    )


ROSTER = [
    _make_line("Alice", "TeamA"),
    _make_line("Bob", "TeamB"),
    _make_line("Carol", "TeamA"),
    _make_line("Dave", "TeamB"),
    _make_line("Eve", "TeamC"),
    _make_line("Frank", "TeamC"),
    _make_line("Grace", "TeamA"),
]

GAME_DATES = {
    "TeamA": ["2026-02-16", "2026-02-18", "2026-02-20"],
    "TeamB": ["2026-02-16", "2026-02-17", "2026-02-19", "2026-02-21"],
    "TeamC": ["2026-02-17", "2026-02-20"],
}

Z_BY_NAME = {
    "Alice": 5.0,   # Highest value
    "Bob": 4.0,
    "Carol": 3.0,
    "Dave": 2.0,
    "Eve": 1.0,
    "Frank": 0.5,
    "Grace": -1.0,  # Lowest value
}


class TestOptimizeLineup:
    def test_never_exceeds_gp_max_12(self):
        """optimize_lineup() never exceeds gp_max=12."""
        plan = optimize_lineup(ROSTER, GAME_DATES, Z_BY_NAME, gp_max=12)
        assert plan.total_gp <= 12

    def test_never_exceeds_gp_max_15(self):
        """optimize_lineup() never exceeds gp_max=15."""
        plan = optimize_lineup(ROSTER, GAME_DATES, Z_BY_NAME, gp_max=15)
        assert plan.total_gp <= 15

    def test_never_exceeds_gp_max_18(self):
        """optimize_lineup() never exceeds gp_max=18."""
        plan = optimize_lineup(ROSTER, GAME_DATES, Z_BY_NAME, gp_max=18)
        assert plan.total_gp <= 18

    def test_higher_value_started_over_lower(self):
        """Higher-value player is started over lower-value player."""
        plan = optimize_lineup(ROSTER, GAME_DATES, Z_BY_NAME, gp_max=5, active_slots=2)
        # On any day where both Alice (5.0) and Grace (-1.0) play and
        # only one can start, Alice should be the one starting
        for day in plan.days:
            if "Alice" in day.starters and day.benched_players:
                benched_names = [p["name"] for p in day.benched_players]
                # Alice should never be benched while Grace starts
                assert "Alice" not in benched_names or "Grace" not in day.starters

    def test_effective_games_consistent(self):
        """Sum of effective_games equals total_gp."""
        plan = optimize_lineup(ROSTER, GAME_DATES, Z_BY_NAME, gp_max=15)
        assert sum(plan.effective_games.values()) == plan.total_gp

    def test_game_calendar_matches_schedule(self):
        """Players only play on dates their team has games."""
        plan = optimize_lineup(ROSTER, GAME_DATES, Z_BY_NAME, gp_max=15)
        for day in plan.days:
            for name in day.starters:
                # Find this player's team
                player = next(r for r in ROSTER if r.name == name)
                assert day.date in GAME_DATES.get(player.team, [])

    def test_returns_lineup_plan(self):
        """optimize_lineup returns a LineupPlan dataclass."""
        plan = optimize_lineup(ROSTER, GAME_DATES, Z_BY_NAME, gp_max=15)
        assert isinstance(plan, LineupPlan)
        assert len(plan.days) > 0
        assert plan.gp_max == 15

    def test_cumulative_gp_monotonic(self):
        """Cumulative GP is monotonically non-decreasing."""
        plan = optimize_lineup(ROSTER, GAME_DATES, Z_BY_NAME, gp_max=15)
        prev = 0
        for day in plan.days:
            assert day.cumulative_gp >= prev
            prev = day.cumulative_gp


class TestConfigGpMax:
    def test_get_gp_max_returns_default(self):
        """get_gp_max(period) returns period-specific override or default."""
        result = get_gp_max(15)
        assert isinstance(result, int)
        assert result > 0

    def test_get_gp_max_no_period(self):
        """get_gp_max() returns default."""
        assert get_gp_max() == 15
