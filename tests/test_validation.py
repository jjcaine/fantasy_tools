"""Tests for post-pipeline Fantrax validation."""

import pytest

from src.validation import (
    validate_players,
    CLEAN,
    MISMATCH_CONFIRMED,
    NOT_IN_FANTRAX,
    NAME_MISMATCH,
    A10_TEAMS,
    _build_fantrax_player_lookup,
    _find_in_fantrax,
)


def _make_ncaa_player(name, team, games=20):
    return {"name": name, "team": team, "games": games}


def _make_roster(team_name, players):
    """Build a mock rosters dict entry."""
    return {
        team_name: {
            "players": [
                {"name": p[0], "team": p[1]} for p in players
            ]
        }
    }


def _make_free_agent(name, team):
    return {"name": name, "team": team}


class TestBuildFantraxLookup:
    def test_rostered_player(self):
        rosters = _make_roster("My Team", [("Justin Moore", "Loyola (IL) Ramblers")])
        lookup = _build_fantrax_player_lookup(rosters, [])
        assert "justin moore" in lookup
        entry = lookup["justin moore"][0]
        assert entry["ncaa_team"] == "Loyola Chicago"
        assert entry["source"] == "rostered"
        assert entry["fantasy_team"] == "My Team"

    def test_free_agent(self):
        fa = [_make_free_agent("John Smith", "Dayton Flyers")]
        lookup = _build_fantrax_player_lookup({}, fa)
        assert "john smith" in lookup
        entry = lookup["john smith"][0]
        assert entry["ncaa_team"] == "Dayton"
        assert entry["source"] == "FA"

    def test_short_team_code(self):
        fa = [_make_free_agent("Test Player", "LoyIL")]
        lookup = _build_fantrax_player_lookup({}, fa)
        entry = lookup["test player"][0]
        assert entry["ncaa_team"] == "Loyola Chicago"


class TestFindInFantrax:
    def test_clean_match(self):
        rosters = _make_roster("Team", [("Justin Moore", "Loyola (IL) Ramblers")])
        lookup = _build_fantrax_player_lookup(rosters, [])
        status, match, detail = _find_in_fantrax("Justin Moore", "Loyola Chicago", lookup)
        assert status == CLEAN
        assert match["name"] == "Justin Moore"

    def test_team_mismatch(self):
        rosters = _make_roster("Team", [("Justin Moore", "Loyola (IL) Ramblers")])
        lookup = _build_fantrax_player_lookup(rosters, [])
        status, match, detail = _find_in_fantrax("Justin Moore", "Saint Louis", lookup)
        assert status == MISMATCH_CONFIRMED
        assert "Loyola Chicago" in detail

    def test_not_found(self):
        lookup = _build_fantrax_player_lookup({}, [])
        status, match, detail = _find_in_fantrax("Unknown Player", "Dayton", lookup)
        assert status == NOT_IN_FANTRAX
        assert match is None

    def test_last_name_fallback(self):
        rosters = _make_roster("Team", [("J. Moore", "Loyola (IL) Ramblers")])
        lookup = _build_fantrax_player_lookup(rosters, [])
        status, match, detail = _find_in_fantrax("Justin Moore", "Loyola Chicago", lookup)
        assert status == NAME_MISMATCH
        assert match["name"] == "J. Moore"


class TestValidatePlayers:
    def test_all_clean(self):
        ncaa = [_make_ncaa_player("Justin Moore", "Loyola Chicago")]
        rosters = _make_roster("Team", [("Justin Moore", "Loyola (IL) Ramblers")])
        report = validate_players(ncaa, rosters, [], {})
        assert report["summary"]["counts"][CLEAN] == 1
        assert report["summary"]["counts"][MISMATCH_CONFIRMED] == 0

    def test_non_a10_team_flagged(self):
        ncaa = [_make_ncaa_player("Bad Player", "Loyola Maryland")]
        report = validate_players(ncaa, {}, [], {})
        assert report["summary"]["counts"][MISMATCH_CONFIRMED] == 1
        assert "Loyola Maryland" in report["summary"]["non_a10_teams_found"]

    def test_mixed_results(self):
        ncaa = [
            _make_ncaa_player("Justin Moore", "Loyola Chicago"),
            _make_ncaa_player("Unknown Guy", "Dayton"),
            _make_ncaa_player("Bad Player", "Army"),
        ]
        rosters = _make_roster("Team", [("Justin Moore", "Loyola (IL) Ramblers")])
        report = validate_players(ncaa, rosters, [], {})
        counts = report["summary"]["counts"]
        assert counts[CLEAN] == 1
        assert counts[MISMATCH_CONFIRMED] == 1  # Army is not A-10
        assert counts[NOT_IN_FANTRAX] == 1  # Unknown Guy

    def test_issues_list(self):
        ncaa = [
            _make_ncaa_player("Clean Player", "Dayton"),
            _make_ncaa_player("Bad Player", "Army"),
        ]
        rosters = _make_roster("Team", [("Clean Player", "Dayton Flyers")])
        report = validate_players(ncaa, rosters, [], {})
        # Only Bad Player should be in issues
        assert len(report["issues"]) == 1
        assert report["issues"][0]["name"] == "Bad Player"
