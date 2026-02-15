"""Tests for boxscore collector team ID allowlist filtering."""

import pytest

from src.boxscore_collector import _is_a10_team_by_id, _parse_boxscore_players


SAMPLE_TEAM_IDS = {
    "2178": "Loyola Chicago",
    "946": "Saint Louis",
    "2186": "Dayton",
    "LOYCHI": "Loyola Chicago",
}


class TestIsA10TeamById:
    def test_match_by_id(self):
        assert _is_a10_team_by_id("2178", "Loyola Chicago", SAMPLE_TEAM_IDS)

    def test_match_by_canonical_name(self):
        assert _is_a10_team_by_id("9999", "Dayton", SAMPLE_TEAM_IDS)

    def test_no_match_wrong_id_wrong_name(self):
        assert not _is_a10_team_by_id("1144", "Loyola Maryland", SAMPLE_TEAM_IDS)

    def test_loyola_maryland_rejected(self):
        """Loyola Maryland's team ID (1144) is not in the allowlist."""
        assert not _is_a10_team_by_id("1144", "Loyola Maryland", SAMPLE_TEAM_IDS)

    def test_loyola_chicago_accepted(self):
        assert _is_a10_team_by_id("2178", "Loyola Chicago", SAMPLE_TEAM_IDS)

    def test_empty_allowlist_no_match(self):
        assert not _is_a10_team_by_id("2178", "Loyola Chicago", {})


class TestParseBoxscorePlayers:
    def _make_boxscore(self, team_id, name_short, player_stats):
        return {
            "teams": [{"teamId": team_id, "nameShort": name_short}],
            "teamBoxscore": [{
                "teamId": team_id,
                "playerStats": player_stats,
            }],
        }

    def _make_player_stat(self, first="Test", last="Player", mins="25"):
        return {
            "firstName": first,
            "lastName": last,
            "minutesPlayed": mins,
            "position": "G",
            "fieldGoalsMade": 5, "fieldGoalsAttempted": 10,
            "freeThrowsMade": 2, "freeThrowsAttempted": 3,
            "threePointsMade": 1, "threePointsAttempted": 3,
            "offensiveRebounds": 1, "totalRebounds": 5,
            "assists": 3, "turnovers": 2, "steals": 1,
            "blockedShots": 0, "personalFouls": 2, "points": 13,
        }

    def test_a10_team_included(self):
        box = self._make_boxscore("2178", "Loyola Chicago", [self._make_player_stat()])
        rows = _parse_boxscore_players(box, "game1", "2026-01-01", SAMPLE_TEAM_IDS)
        assert len(rows) == 1
        assert rows[0]["team"] == "Loyola Chicago"
        assert rows[0]["team_id"] == "2178"

    def test_non_a10_team_excluded(self):
        box = self._make_boxscore("1144", "Loyola Maryland", [self._make_player_stat()])
        rows = _parse_boxscore_players(box, "game1", "2026-01-01", SAMPLE_TEAM_IDS)
        assert len(rows) == 0

    def test_zero_minutes_excluded(self):
        box = self._make_boxscore("2178", "Loyola Chicago", [self._make_player_stat(mins="0")])
        rows = _parse_boxscore_players(box, "game1", "2026-01-01", SAMPLE_TEAM_IDS)
        assert len(rows) == 0

    def test_team_id_in_output(self):
        box = self._make_boxscore("2178", "Loyola Chicago", [self._make_player_stat()])
        rows = _parse_boxscore_players(box, "game1", "2026-01-01", SAMPLE_TEAM_IDS)
        assert rows[0]["team_id"] == "2178"
