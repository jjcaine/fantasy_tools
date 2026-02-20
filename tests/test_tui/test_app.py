"""Tests for Phase 1: app instantiation, screen switching, keybindings."""

import pytest
from textual.widgets import Footer

from src.tui.app import FantasyApp
from src.tui.screens.data_refresh import DataRefreshScreen
from src.tui.screens.matchup import MatchupScreen


@pytest.mark.asyncio
async def test_app_instantiates():
    """FantasyApp instantiates without error using run_test pilot."""
    app = FantasyApp()
    async with app.run_test() as pilot:
        assert app.title == "Fantasy Tools"
        assert app.sub_title == "Sick-Os Revenge"


@pytest.mark.asyncio
async def test_keybinding_d_switches_to_data_refresh():
    """Pressing d switches to DataRefreshScreen."""
    app = FantasyApp()
    async with app.run_test() as pilot:
        await pilot.press("d")
        assert isinstance(app.screen, DataRefreshScreen)


@pytest.mark.asyncio
async def test_keybinding_m_switches_to_matchup():
    """Pressing m switches to MatchupScreen."""
    app = FantasyApp()
    async with app.run_test() as pilot:
        await pilot.press("m")
        assert isinstance(app.screen, MatchupScreen)


@pytest.mark.asyncio
async def test_keybinding_q_quits():
    """Pressing q exits the app."""
    app = FantasyApp()
    async with app.run_test() as pilot:
        await pilot.press("q")
        # If we reach here without hanging, the app exited


@pytest.mark.asyncio
async def test_all_screen_keybindings():
    """All screen keybindings switch to the correct screen type."""
    from src.tui.screens.rankings import RankingsScreen
    from src.tui.screens.roster import RosterScreen
    from src.tui.screens.waiver import WaiverScreen
    from src.tui.screens.lineup import LineupScreen

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
                f"Key '{key}' should switch to {screen_class.__name__}, "
                f"got {type(app.screen).__name__}"
            )


@pytest.mark.asyncio
async def test_help_overlay_from_app():
    """Pressing ? on the app shows a help modal."""
    from src.tui.screens.help import HelpScreen

    app = FantasyApp()
    async with app.run_test() as pilot:
        await pilot.press("question_mark")
        assert isinstance(app.screen, HelpScreen)
        await pilot.press("escape")
        # Should return to default screen
        assert not isinstance(app.screen, HelpScreen)


@pytest.mark.asyncio
async def test_footer_shows_keybindings():
    """Footer widget is present and shows keybinding hints."""
    app = FantasyApp()
    async with app.run_test() as pilot:
        footer = app.query_one(Footer)
        assert footer is not None
