"""Tests for Phase 4: Polish — keybindings, loading, error handling, persistence."""

import pytest
from unittest.mock import patch

from src.tui.app import FantasyApp
from src.tui.screens.data_refresh import DataRefreshScreen
from src.tui.screens.matchup import MatchupScreen
from src.tui.screens.rankings import RankingsScreen
from src.tui.screens.roster import RosterScreen
from src.tui.screens.waiver import WaiverScreen
from src.tui.screens.lineup import LineupScreen
from src.tui.screens.help import HelpScreen


class TestGlobalKeybindings:
    """Phase 4 criterion 1: Every global keybinding switches to the correct screen."""

    @pytest.mark.asyncio
    async def test_all_keybindings_correct_screen(self):
        bindings = {
            "d": DataRefreshScreen,
            "m": MatchupScreen,
            "r": RankingsScreen,
            "t": RosterScreen,
            "w": WaiverScreen,
            "l": LineupScreen,
        }
        app = FantasyApp()
        async with app.run_test() as pilot:
            for key, screen_class in bindings.items():
                await pilot.press(key)
                assert isinstance(app.screen, screen_class), (
                    f"Key '{key}' should switch to {screen_class.__name__}"
                )

    @pytest.mark.asyncio
    async def test_help_keybinding(self):
        app = FantasyApp()
        async with app.run_test() as pilot:
            await pilot.press("question_mark")
            assert isinstance(app.screen, HelpScreen)


class TestLoadingIndicators:
    """Phase 4 criterion 2: Loading indicators appear and disappear correctly."""

    @pytest.mark.asyncio
    async def test_matchup_loading_indicator(self):
        """MatchupScreen shows loading indicator on mount then removes it."""
        app = FantasyApp()
        async with app.run_test() as pilot:
            with patch(
                "src.tui.screens.matchup.MatchupScreen._load_data",
                lambda self: self._on_data_error("test"),
            ):
                await pilot.press("m")
                await pilot.pause()
                # After error, loading indicator should be removed
                from textual.widgets import LoadingIndicator
                indicators = app.screen.query(LoadingIndicator)
                assert len(indicators) == 0


class TestCorruptDataHandling:
    """Phase 4 criterion 3: Corrupt/missing data produces notifications, not exceptions."""

    @pytest.mark.asyncio
    async def test_matchup_missing_data_no_crash(self):
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
    async def test_rankings_missing_data_no_crash(self):
        app = FantasyApp()
        async with app.run_test() as pilot:
            with patch(
                "src.tui.screens.rankings.RankingsScreen._load_data",
                lambda self: self._on_data_error("File not found"),
            ):
                await pilot.press("r")
                await pilot.pause()
                error = app.screen.query_one("#rankings-error")
                assert error is not None

    @pytest.mark.asyncio
    async def test_roster_missing_data_no_crash(self):
        app = FantasyApp()
        async with app.run_test() as pilot:
            with patch(
                "src.tui.screens.roster.RosterScreen._load_data",
                lambda self: self._on_data_error("File not found"),
            ):
                await pilot.press("t")
                await pilot.pause()
                error = app.screen.query_one("#roster-error")
                assert error is not None

    @pytest.mark.asyncio
    async def test_waiver_missing_data_no_crash(self):
        app = FantasyApp()
        async with app.run_test() as pilot:
            with patch(
                "src.tui.screens.waiver.WaiverScreen._load_data",
                lambda self: self._on_data_error("File not found"),
            ):
                await pilot.press("w")
                await pilot.pause()
                error = app.screen.query_one("#waiver-error")
                assert error is not None

    @pytest.mark.asyncio
    async def test_lineup_missing_data_no_crash(self):
        app = FantasyApp()
        async with app.run_test() as pilot:
            with patch(
                "src.tui.screens.lineup.LineupScreen._load_data",
                lambda self: self._on_data_error("File not found"),
            ):
                await pilot.press("l")
                await pilot.pause()
                error = app.screen.query_one("#lineup-error")
                assert error is not None


class TestScreenPersistence:
    """Phase 4 criterion 9: Screen switching preserves state."""

    @pytest.mark.asyncio
    async def test_screen_instance_preserved(self):
        """Same screen instance is returned after switching away and back."""
        app = FantasyApp()
        async with app.run_test() as pilot:
            await pilot.press("d")
            screen1 = app.screen
            assert isinstance(screen1, DataRefreshScreen)

            await pilot.press("m")
            assert isinstance(app.screen, MatchupScreen)

            await pilot.press("d")
            screen2 = app.screen
            assert screen1 is screen2  # Same instance = state preserved
