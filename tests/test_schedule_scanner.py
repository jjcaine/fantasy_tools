"""Tests for the schedule scanner with conference-based filtering."""

import pytest
from datetime import date

from src.schedule_scanner import (
    _is_a10_game,
    _is_a10_team_by_name,
    _normalize_team_name,
    _team_has_a10_conference,
    _extract_team_id,
    A10_CONFERENCE_SEO,
    PERIODS,
)


def _make_team(name_short, conference_seo=None, team_id=None, char6=None, seo=None):
    """Build a mock team dict matching the NCAA scoreboard API shape."""
    team = {
        "names": {"short": name_short},
    }
    if conference_seo is not None:
        team["conferences"] = [{"conferenceSeo": conference_seo}]
    else:
        team["conferences"] = []
    if team_id:
        team["teamId"] = team_id
    if char6:
        team["names"]["char6"] = char6
    if seo:
        team["names"]["seo"] = seo
    return team


def _make_game(away_team, home_team):
    """Build a mock game_data dict."""
    return {"away": away_team, "home": home_team}


class TestTeamHasA10Conference:
    def test_a10_team(self):
        team = _make_team("Loyola Chicago", "atlantic-10")
        assert _team_has_a10_conference(team)

    def test_non_a10_team(self):
        team = _make_team("Loyola Maryland", "patriot")
        assert not _team_has_a10_conference(team)

    def test_no_conference_data(self):
        team = _make_team("Some Team")
        assert not _team_has_a10_conference(team)


class TestIsA10Game:
    def test_a10_vs_a10(self):
        game = _make_game(
            _make_team("Dayton", "atlantic-10"),
            _make_team("VCU", "atlantic-10"),
        )
        assert _is_a10_game(game)

    def test_a10_vs_non_a10(self):
        game = _make_game(
            _make_team("Dayton", "atlantic-10"),
            _make_team("Duke", "acc"),
        )
        assert _is_a10_game(game)

    def test_non_a10_vs_non_a10(self):
        game = _make_game(
            _make_team("Duke", "acc"),
            _make_team("Kentucky", "sec"),
        )
        assert not _is_a10_game(game)

    def test_loyola_maryland_rejected(self):
        """The specific bug: Loyola Maryland (Patriot) should NOT match."""
        game = _make_game(
            _make_team("Loyola Maryland", "patriot"),
            _make_team("Army", "patriot"),
        )
        assert not _is_a10_game(game)

    def test_loyola_chicago_accepted(self):
        game = _make_game(
            _make_team("Loyola Chicago", "atlantic-10"),
            _make_team("Army", "patriot"),
        )
        assert _is_a10_game(game)

    def test_fallback_no_conference_data(self):
        """When neither team has conference data, falls back to name matching."""
        game = _make_game(
            _make_team("Dayton"),  # no conference data
            _make_team("Duke"),
        )
        # Dayton matches via A10_SEARCH_NAMES fallback
        assert _is_a10_game(game)

    def test_fallback_loyola_no_conf_uses_specific_name(self):
        """Fallback matching uses 'loyola chicago' (not just 'loyola')."""
        game = _make_game(
            _make_team("Loyola Maryland"),  # no conference data
            _make_team("Army"),
        )
        # Should NOT match — "loyola maryland" doesn't contain "loyola chicago"
        assert not _is_a10_game(game)

    def test_one_team_has_conf_other_doesnt(self):
        """If one team has conference data, use it (don't fall back)."""
        game = _make_game(
            _make_team("Duke", "acc"),  # has conference data, not A-10
            _make_team("Dayton"),  # no conference data
        )
        # Since away has conference data, we use conference-based check.
        # Duke is ACC, not A-10. Dayton has no conference data but since
        # away HAS conference data, we don't fall back.
        # Dayton's conferences list is empty, so _team_has_a10_conference returns False.
        assert not _is_a10_game(game)


class TestIsA10TeamByName:
    def test_positive(self):
        assert _is_a10_team_by_name("Dayton")
        assert _is_a10_team_by_name("VCU")
        assert _is_a10_team_by_name("Saint Louis")
        assert _is_a10_team_by_name("George Mason")
        assert _is_a10_team_by_name("Loyola Chicago")

    def test_negative(self):
        assert not _is_a10_team_by_name("Duke")
        assert not _is_a10_team_by_name("Kentucky")
        assert not _is_a10_team_by_name("Notre Dame")

    def test_loyola_maryland_rejected(self):
        """'Loyola Maryland' should NOT match since we search for 'loyola chicago'."""
        assert not _is_a10_team_by_name("Loyola Maryland")


class TestNormalizeTeamName:
    def test_exact_matches(self):
        assert _normalize_team_name("VCU") == "VCU"
        assert _normalize_team_name("Dayton") == "Dayton"
        assert _normalize_team_name("Loyola Chicago") == "Loyola Chicago"
        assert _normalize_team_name("Saint Bonaventure") == "St. Bonaventure"
        assert _normalize_team_name("St. Bonaventure") == "St. Bonaventure"

    def test_unknown_passthrough(self):
        assert _normalize_team_name("Duke") == "Duke"

    def test_fallback_substring(self):
        assert _normalize_team_name("VCU Rams") == "VCU"
        assert _normalize_team_name("Dayton Flyers") == "Dayton"


class TestExtractTeamId:
    def test_with_team_id(self):
        team = _make_team("Dayton", team_id="2186")
        assert _extract_team_id(team) == "2186"

    def test_with_seo(self):
        team = _make_team("Dayton", seo="dayton")
        assert _extract_team_id(team) == "dayton"

    def test_team_id_preferred_over_seo(self):
        team = _make_team("Dayton", team_id="2186", seo="dayton")
        assert _extract_team_id(team) == "2186"

    def test_no_id(self):
        team = _make_team("Dayton")
        assert _extract_team_id(team) is None


class TestPeriods:
    def test_periods_defined(self):
        assert 14 in PERIODS
        assert 15 in PERIODS
        assert 16 in PERIODS
        assert 17 in PERIODS
