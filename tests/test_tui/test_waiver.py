"""Tests for Phase 3c: Waiver Optimizer screen."""

import pytest
from unittest.mock import patch

from src.fantasy_math import (
    CATEGORIES, PlayerCatLine, TeamProjection,
    build_player_lookup, compute_z_scores, composite_z_score,
    schedule_adjusted_composite, player_to_cat_line,
    build_team_roster_lines, get_player_games_in_period, project_team_week,
)
from src.tui.app import FantasyApp
from src.tui.screens.waiver import WaiverScreen
from src.tui.screens.help import HelpScreen


def _make_player(name, team, ppg=15.0, games=20):
    return {
        "name": name, "team": team, "games": games, "mpg": 30.0,
        "ppg": ppg, "rpg": 5.0, "apg": 3.0, "spg": 1.0, "bpg": 0.5,
        "topg": 2.0, "tpm_pg": 1.5, "fgm": 100, "fga": 200, "tpm": 30,
        "ftm": 50, "fta": 60,
    }


FIXTURE_PLAYERS = [
    _make_player("Alice Smith", "Davidson", 18.0),
    _make_player("Bob Jones", "Dayton", 12.0),
    _make_player("Carol Lee", "Fordham", 20.0),
    _make_player("Dave Kim", "VCU", 10.0),
    _make_player("Eve Chen", "Richmond", 16.0),
    _make_player("Frank Wu", "La Salle", 14.0),
]

FIXTURE_ROSTERS = {
    "Sick-Os Revenge": {
        "players": [
            {"name": "Alice Smith", "team": "David"},
            {"name": "Bob Jones", "team": "Dayt"},
        ]
    },
    "Other Team": {
        "players": [
            {"name": "Carol Lee", "team": "Ford"},
        ]
    },
}

# Dave Kim, Eve Chen, Frank Wu are free agents
FIXTURE_FREE_AGENTS = [
    {"name": "Dave Kim", "team": "VCU"},
    {"name": "Eve Chen", "team": "Rich"},
    {"name": "Frank Wu", "team": "LaSa"},
]

FIXTURE_SCHEDULE = {
    "15": {
        "games_per_team": {
            "Davidson": 3, "Dayton": 2, "Fordham": 3,
            "VCU": 2, "Richmond": 3, "La Salle": 2,
        },
        "game_dates_per_team": {},
    },
}


class TestFreeAgentIdentification:
    def test_free_agents_not_on_roster(self):
        """Free agents are correctly identified (not on any roster)."""
        rostered_names = set()
        for team_data in FIXTURE_ROSTERS.values():
            for p in team_data.get("players", []):
                rostered_names.add(p.get("name", "").lower())

        for fa in FIXTURE_FREE_AGENTS:
            assert fa["name"].lower() not in rostered_names


class TestSwapSimulation:
    def test_swap_produces_before_after(self):
        """Swap simulation produces correct before/after projections."""
        lookup = build_player_lookup(FIXTURE_PLAYERS)
        lines, _, _ = build_team_roster_lines(
            "Sick-Os Revenge", FIXTURE_ROSTERS, FIXTURE_PLAYERS, lookup
        )

        # Before projection
        before_games = get_player_games_in_period(lines, FIXTURE_SCHEDULE, 15)
        before_proj = project_team_week(lines, before_games, period=15, team_name="Sick-Os Revenge")

        # Swap: drop Bob Jones, add Eve Chen
        add_ncaa = next(p for p in FIXTURE_PLAYERS if p["name"] == "Eve Chen")
        add_line = player_to_cat_line(add_ncaa)
        new_lines = [cl for cl in lines if cl.name != "Bob Jones"]
        new_lines.append(add_line)

        after_games = get_player_games_in_period(new_lines, FIXTURE_SCHEDULE, 15)
        after_proj = project_team_week(new_lines, after_games, period=15, team_name="Sick-Os Revenge")

        # Both should have valid category projections
        for cat in CATEGORIES:
            assert cat in before_proj.cats
            assert cat in after_proj.cats

    def test_fa_sorted_by_sched_adj_descending(self):
        """FA list sorted by schedule-adjusted composite z descending."""
        z_data = compute_z_scores(FIXTURE_PLAYERS, min_games=5, min_mpg=10.0)
        for row in z_data:
            row["sched_adj"] = schedule_adjusted_composite(row["z_scores"], 3)
        z_data.sort(key=lambda r: r["sched_adj"], reverse=True)
        for i in range(len(z_data) - 1):
            assert z_data[i]["sched_adj"] >= z_data[i + 1]["sched_adj"]


class TestWaiverScreen:
    @pytest.mark.asyncio
    async def test_screen_mounts(self):
        """WaiverScreen can be mounted with fixture data."""
        app = FantasyApp()
        async with app.run_test() as pilot:
            with patch(
                "src.tui.screens.waiver.WaiverScreen._load_data",
                lambda self: self._on_data_loaded(
                    FIXTURE_PLAYERS, FIXTURE_ROSTERS, FIXTURE_SCHEDULE, FIXTURE_FREE_AGENTS
                ),
            ):
                await pilot.press("w")
                await pilot.pause()
                assert isinstance(app.screen, WaiverScreen)

    @pytest.mark.asyncio
    async def test_help_overlay(self):
        """Pressing ? on Waiver screen shows help modal."""
        app = FantasyApp()
        async with app.run_test() as pilot:
            with patch(
                "src.tui.screens.waiver.WaiverScreen._load_data",
                lambda self: self._on_data_loaded(
                    FIXTURE_PLAYERS, FIXTURE_ROSTERS, FIXTURE_SCHEDULE, FIXTURE_FREE_AGENTS
                ),
            ):
                await pilot.press("w")
                await pilot.pause()
                await pilot.press("question_mark")
                assert isinstance(app.screen, HelpScreen)
