"""Tests for the NCAA API client. Requires the NCAA API Docker container running on port 3000."""

import pytest
from src import ncaa_client


@pytest.fixture(scope="module")
def a10_standings():
    return ncaa_client.get_standings()


class TestNcaaStandings:
    def test_returns_14_teams(self, a10_standings):
        assert len(a10_standings) == 14

    def test_has_expected_teams(self, a10_standings):
        school_names = {s["School"] for s in a10_standings}
        assert "Saint Louis" in school_names
        assert "VCU" in school_names
        assert "Dayton" in school_names

    def test_has_required_fields(self, a10_standings):
        for team in a10_standings:
            assert "School" in team
            assert "Conference W" in team
            assert "Conference L" in team
            assert "Overall W" in team
            assert "Overall L" in team


class TestNcaaIndividualStats:
    def test_ppg_returns_data(self):
        data = ncaa_client.get_individual_stats(136)
        assert len(data) > 100  # Should have many players nationally

    def test_ppg_has_correct_fields(self):
        data = ncaa_client.get_individual_stats(136)
        first = data[0]
        for field in ["Rank", "Name", "Team", "G", "FGM", "3FG", "FT", "PTS", "PPG"]:
            assert field in first, f"Missing field: {field}"

    def test_rpg_has_correct_fields(self):
        data = ncaa_client.get_individual_stats(137)
        first = data[0]
        for field in ["Name", "Team", "G", "REB", "RPG"]:
            assert field in first

    def test_fg_pct_has_correct_fields(self):
        data = ncaa_client.get_individual_stats(141)
        first = data[0]
        for field in ["Name", "Team", "G", "FGM", "FGA", "FG%"]:
            assert field in first

    def test_ft_pct_has_correct_fields(self):
        data = ncaa_client.get_individual_stats(142)
        first = data[0]
        for field in ["Name", "Team", "G", "FT", "FTA", "FT%"]:
            assert field in first


class TestNcaaTeamStats:
    def test_scoring_offense_returns_data(self):
        data = ncaa_client.get_team_stats(145)
        assert len(data) > 50

    def test_turnovers_per_game_returns_data(self):
        data = ncaa_client.get_team_stats(217)
        assert len(data) > 50


class TestA10Filtering:
    def test_filter_a10_players(self):
        all_ppg = ncaa_client.get_individual_stats(136)
        a10 = ncaa_client.filter_a10_players(all_ppg)
        assert len(a10) > 0
        assert len(a10) < len(all_ppg)
        # All filtered players should be from A-10 teams
        for p in a10:
            team = p.get("Team", "")
            assert any(t.lower() in team.lower() for t in ncaa_client.A10_TEAMS), \
                f"Non-A10 player found: {p['Name']} from {team}"

    def test_filter_a10_teams(self):
        all_teams = ncaa_client.get_team_stats(145)
        a10 = ncaa_client.filter_a10_teams(all_teams)
        assert len(a10) >= 13  # At least 13 A-10 teams should appear
        assert len(a10) <= 14


class TestNcaaScoreboard:
    def test_scoreboard_returns_games(self):
        # Use a date we know had games (Feb 14, 2026)
        data = ncaa_client.get_scoreboard(2026, 2, 14)
        games = data.get("games", [])
        assert len(games) > 0

    def test_game_structure(self):
        data = ncaa_client.get_scoreboard(2026, 2, 14)
        game = data["games"][0]
        game_data = game.get("game", game)
        assert "away" in game_data
        assert "home" in game_data
        assert "gameID" in game_data
