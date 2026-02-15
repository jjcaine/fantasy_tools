"""Tests for src/config.py — Phase 1 completion criteria."""

from datetime import date

from src.config import get_periods, get_gp_max, get_my_team, get_categories


def test_get_periods_returns_dict():
    """get_periods() returns period date ranges."""
    periods = get_periods()
    assert isinstance(periods, dict)
    assert len(periods) >= 4
    for num, (start, end) in periods.items():
        assert isinstance(num, int)
        assert isinstance(start, date)
        assert isinstance(end, date)
        assert start < end


def test_get_periods_has_expected_periods():
    """Config has periods 14-17."""
    periods = get_periods()
    for p in [14, 15, 16, 17]:
        assert p in periods


def test_get_gp_max_default():
    """get_gp_max() returns 15 (default) for periods without override."""
    assert get_gp_max(15) == 15


def test_get_gp_max_no_period():
    """get_gp_max() without period returns default."""
    assert get_gp_max() == 15


def test_get_my_team():
    """get_my_team() returns team name from config."""
    team = get_my_team()
    assert team == "Sick-Os Revenge"


def test_get_categories():
    """get_categories() returns 9 category names."""
    cats = get_categories()
    assert len(cats) == 9
    assert "AdjFG%" in cats
    assert "TO" in cats
