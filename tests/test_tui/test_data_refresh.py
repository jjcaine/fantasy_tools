"""Tests for DataRefreshScreen — Phase 1 completion criteria."""

import pytest
from unittest.mock import patch, MagicMock

from textual.widgets import RichLog, Button

from src.tui.app import FantasyApp
from src.tui.screens.data_refresh import DataRefreshScreen
from src.tui.screens.help import HelpScreen


@pytest.mark.asyncio
async def test_data_refresh_screen_mounts():
    """DataRefreshScreen can be mounted independently."""
    app = FantasyApp()
    async with app.run_test() as pilot:
        await pilot.press("d")
        assert isinstance(app.screen, DataRefreshScreen)
        # Check that key widgets exist
        log = app.screen.query_one("#refresh-log", RichLog)
        btn = app.screen.query_one("#start-collection", Button)
        assert log is not None
        assert btn is not None


@pytest.mark.asyncio
async def test_collection_worker_with_mocks():
    """Clicking Start Collection triggers the worker and logs success messages."""
    app = FantasyApp()
    async with app.run_test() as pilot:
        await pilot.press("d")

        with (
            patch("src.tui.screens.data_refresh.DataRefreshScreen._step_ncaa_standings") as mock_ncaa,
            patch("src.tui.screens.data_refresh.DataRefreshScreen._step_player_stats") as mock_stats,
            patch("src.tui.screens.data_refresh.DataRefreshScreen._step_schedule") as mock_sched,
            patch("src.tui.screens.data_refresh.DataRefreshScreen._step_fantrax") as mock_ftx,
            patch("src.tui.screens.data_refresh.DataRefreshScreen._step_validation") as mock_val,
        ):
            await pilot.click("#start-collection")
            await pilot.pause(delay=0.5)
            # Wait for worker to complete
            await app.workers.wait_for_complete()
            await pilot.pause()

            # All steps should have been called
            mock_ncaa.assert_called_once()
            mock_stats.assert_called_once()
            mock_sched.assert_called_once()
            mock_ftx.assert_called_once()
            mock_val.assert_called_once()


@pytest.mark.asyncio
async def test_collection_step_failure_continues():
    """A failure in one step logs an error and continues to the next step."""
    app = FantasyApp()
    async with app.run_test() as pilot:
        await pilot.press("d")

        def fail_step(log_fn):
            raise RuntimeError("Simulated failure")

        with (
            patch("src.tui.screens.data_refresh.DataRefreshScreen._step_ncaa_standings", side_effect=fail_step),
            patch("src.tui.screens.data_refresh.DataRefreshScreen._step_player_stats") as mock_stats,
            patch("src.tui.screens.data_refresh.DataRefreshScreen._step_schedule") as mock_sched,
            patch("src.tui.screens.data_refresh.DataRefreshScreen._step_fantrax") as mock_ftx,
            patch("src.tui.screens.data_refresh.DataRefreshScreen._step_validation") as mock_val,
        ):
            await pilot.click("#start-collection")
            await pilot.pause(delay=0.5)
            await app.workers.wait_for_complete()
            await pilot.pause()

            # Despite first step failing, remaining steps should still run
            mock_stats.assert_called_once()
            mock_sched.assert_called_once()
            mock_ftx.assert_called_once()
            mock_val.assert_called_once()


@pytest.mark.asyncio
async def test_help_overlay_on_data_refresh():
    """Pressing ? on Data Refresh screen shows a help modal that closes on escape."""
    app = FantasyApp()
    async with app.run_test() as pilot:
        await pilot.press("d")
        assert isinstance(app.screen, DataRefreshScreen)
        await pilot.press("question_mark")
        assert isinstance(app.screen, HelpScreen)
        await pilot.press("escape")
        assert isinstance(app.screen, DataRefreshScreen)
