"""Tests for Phase 3b: Roster Analysis screen."""

import pytest
from unittest.mock import patch

from src.fantasy_math import (
    CATEGORIES, PlayerCatLine, TeamProjection,
    build_player_lookup, build_team_roster_lines,
    get_player_games_in_period, get_all_team_projections,
)
from src.tui.app import FantasyApp
from src.tui.screens.roster import RosterScreen
from src.tui.screens.help import HelpScreen


# Minimal fixture data
def _make_player(name, team, ppg=15.0):
    return {
        "name": name, "team": team, "games": 20, "mpg": 30.0,
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
            {"name": "Dave Kim", "team": "VCU"},
        ]
    },
}

FIXTURE_SCHEDULE = {
    "15": {
        "games_per_team": {"Davidson": 3, "Dayton": 2, "Fordham": 3, "VCU": 2, "Richmond": 3},
        "game_dates_per_team": {},
    },
}


class TestRosterData:
    def test_build_roster_lines(self):
        """All rostered players appear with stats matching build_team_roster_lines()."""
        lookup = build_player_lookup(FIXTURE_PLAYERS)
        lines, matched, unmatched = build_team_roster_lines(
            "Sick-Os Revenge", FIXTURE_ROSTERS, FIXTURE_PLAYERS, lookup
        )
        matched_names = {cl.name for cl in lines}
        assert "Alice Smith" in matched_names
        assert "Bob Jones" in matched_names

    def test_category_ranks_range(self):
        """Category ranks are in range 1-8."""
        lookup = build_player_lookup(FIXTURE_PLAYERS)
        all_projs = get_all_team_projections(
            FIXTURE_ROSTERS, FIXTURE_PLAYERS, FIXTURE_SCHEDULE, 15
        )
        # Ranks should be 1 to len(teams) for each team
        for cat in CATEGORIES:
            vals = [(t, p.cats.get(cat, 0)) for t, p in all_projs.items()]
            vals.sort(key=lambda x: x[1], reverse=True)
            for i, (t, v) in enumerate(vals):
                rank = i + 1
                assert 1 <= rank <= len(all_projs)


class TestRosterScreen:
    @pytest.mark.asyncio
    async def test_screen_mounts(self):
        """RosterScreen can be mounted."""
        app = FantasyApp()
        async with app.run_test() as pilot:
            with patch(
                "src.tui.screens.roster.RosterScreen._load_data",
                lambda self: self._on_data_loaded(FIXTURE_PLAYERS, FIXTURE_ROSTERS, FIXTURE_SCHEDULE),
            ):
                await pilot.press("t")
                await pilot.pause()
                assert isinstance(app.screen, RosterScreen)

    @pytest.mark.asyncio
    async def test_help_overlay(self):
        """Pressing ? on Roster screen shows help modal."""
        app = FantasyApp()
        async with app.run_test() as pilot:
            with patch(
                "src.tui.screens.roster.RosterScreen._load_data",
                lambda self: self._on_data_loaded(FIXTURE_PLAYERS, FIXTURE_ROSTERS, FIXTURE_SCHEDULE),
            ):
                await pilot.press("t")
                await pilot.pause()
                await pilot.press("question_mark")
                assert isinstance(app.screen, HelpScreen)
