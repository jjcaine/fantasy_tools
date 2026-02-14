"""Tests for the schedule scanner. Requires NCAA API Docker container running."""

import pytest
from src.schedule_scanner import scan_date, _is_a10_team, _normalize_team_name, PERIODS
from datetime import date


class TestTeamNameHelpers:
    def test_is_a10_team_positive(self):
        assert _is_a10_team("Dayton")
        assert _is_a10_team("VCU")
        assert _is_a10_team("Saint Louis")
        assert _is_a10_team("George Mason")
        assert _is_a10_team("St. Bonaventure")
        assert _is_a10_team("Loyola Chicago")

    def test_is_a10_team_negative(self):
        assert not _is_a10_team("Duke")
        assert not _is_a10_team("Kentucky")
        assert not _is_a10_team("Notre Dame")

    def test_normalize_team_name(self):
        assert _normalize_team_name("VCU") == "VCU"
        assert _normalize_team_name("Dayton") == "Dayton"
        assert _normalize_team_name("St. Bonaventure") == "St. Bonaventure"
        assert _normalize_team_name("Loyola Chicago") == "Loyola Chicago"

    def test_periods_defined(self):
        assert 14 in PERIODS
        assert 15 in PERIODS
        assert 16 in PERIODS
        assert 17 in PERIODS


class TestScanDate:
    def test_scan_known_game_date(self):
        # Feb 12, 2026 should have some A-10 games
        games = scan_date(date(2026, 2, 12))
        # May or may not have games, but shouldn't error
        assert isinstance(games, list)

    def test_game_structure(self):
        games = scan_date(date(2026, 2, 12))
        for g in games:
            assert "date" in g
            assert "away" in g
            assert "home" in g
            assert "game_id" in g
