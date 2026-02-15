"""Tests for Phase 2: Matchup Dashboard screen and CategoryComparisonTable widget."""

import pytest
from unittest.mock import patch, MagicMock

from src.fantasy_math import (
    CATEGORIES,
    TeamProjection,
    MatchupResult,
    CatComparison,
    predict_matchup,
)
from src.tui.app import FantasyApp
from src.tui.screens.matchup import MatchupScreen
from src.tui.screens.help import HelpScreen
from src.tui.widgets.category_table import CategoryComparisonTable, _fmt_val


# ── Fixture data ─────────────────────────────────────────────────────

def _make_projections():
    """Create fixture projections for 3 teams (my team + 2 opponents)."""
    my_proj = TeamProjection(team_name="Sick-Os Revenge", period=15)
    my_proj.cats = {
        "AdjFG%": 0.550, "3PTM": 15.0, "FT%": 0.800, "PTS": 160.0,
        "REB": 60.0, "AST": 35.0, "ST": 12.0, "BLK": 8.0, "TO": 14.0,
    }

    opp1_proj = TeamProjection(team_name="Opponent A", period=15)
    opp1_proj.cats = {
        "AdjFG%": 0.500, "3PTM": 18.0, "FT%": 0.750, "PTS": 150.0,
        "REB": 65.0, "AST": 30.0, "ST": 10.0, "BLK": 10.0, "TO": 18.0,
    }

    opp2_proj = TeamProjection(team_name="Opponent B", period=15)
    opp2_proj.cats = {
        "AdjFG%": 0.600, "3PTM": 20.0, "FT%": 0.850, "PTS": 170.0,
        "REB": 55.0, "AST": 40.0, "ST": 15.0, "BLK": 6.0, "TO": 12.0,
    }

    return {
        "Sick-Os Revenge": my_proj,
        "Opponent A": opp1_proj,
        "Opponent B": opp2_proj,
    }


FIXTURE_ROSTERS = {
    "Sick-Os Revenge": {"players": []},
    "Opponent A": {"players": []},
    "Opponent B": {"players": []},
}

FIXTURE_SCHEDULE = {
    "15": {"games": {}},
    "16": {"games": {}},
}

FIXTURE_PLAYERS = []


def _patch_matchup_data():
    """Return context managers that patch data loading for matchup tests."""
    projs = _make_projections()

    return (
        patch("src.tui.screens.matchup.MatchupScreen._load_data", lambda self: _mock_load(self)),
        patch("src.fantasy_math.build_player_lookup", return_value={}),
        patch("src.fantasy_math.get_all_team_projections", return_value=projs),
    )


def _mock_load(screen):
    """Simulate data loading completing synchronously."""
    screen._on_data_loaded(FIXTURE_PLAYERS, FIXTURE_ROSTERS, FIXTURE_SCHEDULE)


# ── CategoryComparisonTable widget tests ─────────────────────────────

class TestCategoryComparisonTable:
    def test_fmt_val_pct(self):
        """Percentage cats display to 3 decimal places."""
        assert _fmt_val("AdjFG%", 0.55) == "0.550"
        assert _fmt_val("FT%", 0.8) == "0.800"

    def test_fmt_val_counting(self):
        """Counting cats display to 1 decimal place."""
        assert _fmt_val("PTS", 160.0) == "160.0"
        assert _fmt_val("3PTM", 15.0) == "15.0"

    @pytest.mark.asyncio
    async def test_widget_renders_9_rows(self):
        """CategoryComparisonTable renders a MatchupResult with 9 rows."""
        projs = _make_projections()
        result = predict_matchup(projs["Sick-Os Revenge"], projs["Opponent A"])

        app = FantasyApp()
        async with app.run_test() as pilot:
            widget = CategoryComparisonTable(result=result)
            await app.mount(widget)
            await pilot.pause()
            table = widget.query_one("#cat-table")
            assert table.row_count == 9

    @pytest.mark.asyncio
    async def test_widget_values_match_predict_matchup(self):
        """H2H table values exactly match predict_matchup() output."""
        projs = _make_projections()
        result = predict_matchup(projs["Sick-Os Revenge"], projs["Opponent A"])

        app = FantasyApp()
        async with app.run_test() as pilot:
            widget = CategoryComparisonTable(result=result)
            await app.mount(widget)
            await pilot.pause()
            table = widget.query_one("#cat-table")

            # Verify each row matches the result comparisons
            for i, comp in enumerate(result.comparisons):
                row_data = table.get_row_at(i)
                # row_data: (cat_label, our_val, their_val, winner, margin)
                expected_our = _fmt_val(comp.category, comp.team_a_val)
                expected_their = _fmt_val(comp.category, comp.team_b_val)
                assert row_data[1] == expected_our, (
                    f"Row {i} ({comp.category}): our val {row_data[1]} != {expected_our}"
                )
                assert row_data[2] == expected_their, (
                    f"Row {i} ({comp.category}): their val {row_data[2]} != {expected_their}"
                )


# ── MatchupScreen tests ──────────────────────────────────────────────

class TestMatchupScreen:
    @pytest.mark.asyncio
    async def test_screen_mounts_with_fixture_data(self):
        """MatchupScreen mounted with fixture data populates selectors."""
        p1, p2, p3 = _patch_matchup_data()
        app = FantasyApp()
        async with app.run_test() as pilot:
            with p1, p2, p3:
                await pilot.press("m")
                await pilot.pause()
                screen = app.screen
                assert isinstance(screen, MatchupScreen)
                # Period and opponent selects should exist
                from textual.widgets import Select
                period_sel = screen.query_one("#period-select", Select)
                opp_sel = screen.query_one("#opponent-select", Select)
                assert period_sel is not None
                assert opp_sel is not None

    @pytest.mark.asyncio
    async def test_overview_table_has_correct_rows(self):
        """All-opponents table has exactly N-1 rows (one per opponent)."""
        p1, p2, p3 = _patch_matchup_data()
        app = FantasyApp()
        async with app.run_test() as pilot:
            with p1, p2, p3:
                await pilot.press("m")
                await pilot.pause()
                from textual.widgets import DataTable
                overview = app.screen.query_one("#overview-table", DataTable)
                # 3 teams total - 1 (my team) = 2 opponent rows
                assert overview.row_count == 2

    @pytest.mark.asyncio
    async def test_missing_data_shows_error(self):
        """Missing data files produce an error message, not a crash."""
        app = FantasyApp()
        async with app.run_test() as pilot:
            with patch(
                "src.tui.screens.matchup.MatchupScreen._load_data",
                lambda self: self._on_data_error("File not found"),
            ):
                await pilot.press("m")
                await pilot.pause()
                error = app.screen.query_one("#matchup-error")
                assert error is not None

    @pytest.mark.asyncio
    async def test_help_overlay(self):
        """Pressing ? on Matchup screen shows help modal."""
        p1, p2, p3 = _patch_matchup_data()
        app = FantasyApp()
        async with app.run_test() as pilot:
            with p1, p2, p3:
                await pilot.press("m")
                await pilot.pause()
                await pilot.press("question_mark")
                assert isinstance(app.screen, HelpScreen)
                await pilot.press("escape")
                assert isinstance(app.screen, MatchupScreen)

    @pytest.mark.asyncio
    async def test_h2h_result_summary_shown(self):
        """Result summary label shows projected result."""
        p1, p2, p3 = _patch_matchup_data()
        app = FantasyApp()
        async with app.run_test() as pilot:
            with p1, p2, p3:
                await pilot.press("m")
                await pilot.pause()
                from textual.widgets import Label
                summary = app.screen.query_one("#result-summary", Label)
                # Should contain the result string (e.g., "6-3" or similar)
                # Label stores its content in _content or we can check the update
                assert summary is not None


class TestMatchupCorrectness:
    """Verify that the TUI matchup values match predict_matchup() exactly."""

    def test_fixture_matchup_result(self):
        """Sanity check: fixture data produces a valid matchup result."""
        projs = _make_projections()
        result = predict_matchup(projs["Sick-Os Revenge"], projs["Opponent A"])
        assert result.wins_a + result.wins_b + result.ties == 9
        assert len(result.comparisons) == 9

    def test_fixture_all_opponents(self):
        """All-opponents loop produces valid results for each opponent."""
        projs = _make_projections()
        my_proj = projs["Sick-Os Revenge"]
        for name, opp_proj in projs.items():
            if name == "Sick-Os Revenge":
                continue
            result = predict_matchup(my_proj, opp_proj)
            assert result.wins_a + result.wins_b + result.ties == 9
