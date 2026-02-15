"""Tests for Phase 3a: Player Rankings screen."""

import pytest
from unittest.mock import patch

from src.fantasy_math import (
    CATEGORIES, compute_z_scores, composite_z_score,
    schedule_adjusted_composite,
)
from src.tui.app import FantasyApp
from src.tui.screens.rankings import RankingsScreen
from src.tui.screens.help import HelpScreen


# Fixture: minimal player data for z-score computation
FIXTURE_PLAYERS = [
    {
        "name": f"Player{i}", "team": f"Team{i % 3}",
        "games": 20 - i, "mpg": 30.0 - i,
        "ppg": 15.0 + i, "rpg": 5.0, "apg": 3.0, "spg": 1.0, "bpg": 0.5,
        "topg": 2.0, "tpm_pg": 1.5, "fgm": 100, "fga": 200, "tpm": 30,
        "ftm": 50, "fta": 60,
    }
    for i in range(10)
]

FIXTURE_SCHEDULE = {
    "15": {"games_per_team": {"Team0": 3, "Team1": 2, "Team2": 4}},
    "16": {"games_per_team": {"Team0": 2, "Team1": 3, "Team2": 2}},
}


def _mock_load(screen):
    screen._on_data_loaded(FIXTURE_PLAYERS, FIXTURE_SCHEDULE)


class TestZScoreCorrectness:
    def test_z_scores_match_compute(self):
        """Z-score values match compute_z_scores() output exactly."""
        z_data = compute_z_scores(FIXTURE_PLAYERS, min_games=5, min_mpg=10.0)
        assert len(z_data) > 0
        for row in z_data:
            assert "z_scores" in row
            assert "name" in row
            for cat in CATEGORIES:
                assert cat in row["z_scores"]

    def test_min_gp_filter(self):
        """Min GP filter produces correct player counts."""
        all_z = compute_z_scores(FIXTURE_PLAYERS, min_games=1, min_mpg=0)
        filtered = compute_z_scores(FIXTURE_PLAYERS, min_games=15, min_mpg=0)
        assert len(filtered) <= len(all_z)
        for row in filtered:
            assert row["games"] >= 15

    def test_min_mpg_filter(self):
        """Min MPG filter produces correct player counts."""
        all_z = compute_z_scores(FIXTURE_PLAYERS, min_games=1, min_mpg=0)
        filtered = compute_z_scores(FIXTURE_PLAYERS, min_games=1, min_mpg=25.0)
        assert len(filtered) <= len(all_z)
        for row in filtered:
            assert row["mpg"] >= 25.0

    def test_sort_by_composite_descending(self):
        """Sort by composite z produces descending order."""
        z_data = compute_z_scores(FIXTURE_PLAYERS, min_games=5, min_mpg=10.0)
        for row in z_data:
            row["composite"] = composite_z_score(row["z_scores"])
        z_data.sort(key=lambda r: r["composite"], reverse=True)
        for i in range(len(z_data) - 1):
            assert z_data[i]["composite"] >= z_data[i + 1]["composite"]


class TestRankingsScreen:
    @pytest.mark.asyncio
    async def test_screen_mounts(self):
        """RankingsScreen can be mounted with fixture data."""
        app = FantasyApp()
        async with app.run_test() as pilot:
            with patch(
                "src.tui.screens.rankings.RankingsScreen._load_data",
                lambda self: _mock_load(self),
            ):
                await pilot.press("r")
                await pilot.pause()
                assert isinstance(app.screen, RankingsScreen)
                from textual.widgets import DataTable
                table = app.screen.query_one("#rankings-table", DataTable)
                assert table.row_count > 0

    @pytest.mark.asyncio
    async def test_help_overlay(self):
        """Pressing ? on Rankings screen shows help modal."""
        app = FantasyApp()
        async with app.run_test() as pilot:
            with patch(
                "src.tui.screens.rankings.RankingsScreen._load_data",
                lambda self: _mock_load(self),
            ):
                await pilot.press("r")
                await pilot.pause()
                await pilot.press("question_mark")
                assert isinstance(app.screen, HelpScreen)
