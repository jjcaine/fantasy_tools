"""Tests for the FanTrax client. Requires valid .env credentials and internet access."""

import pytest
from src import fantrax_client


LEAGUE_ID = "l6r9clmimgohg3yp"
MY_TEAM = "Sick-Os Revenge"
EXPECTED_TEAMS = 8
CATEGORIES = ["AdjFG%", "3PTM", "FT%", "PTS", "REB", "AST", "ST", "BLK", "TO"]


@pytest.fixture(scope="module")
def league():
    return fantrax_client.get_league()


class TestLeagueConnection:
    def test_league_name(self, league):
        assert league.name == "A10 Fantasy"

    def test_league_has_8_teams(self, league):
        assert len(league.teams) == EXPECTED_TEAMS

    def test_our_team_exists(self, league):
        team_names = [t.name for t in league.teams]
        assert MY_TEAM in team_names


class TestStandings:
    def test_returns_8_teams(self, league):
        standings = fantrax_client.get_standings(league)
        assert len(standings) == EXPECTED_TEAMS

    def test_has_required_fields(self, league):
        standings = fantrax_client.get_standings(league)
        for rank, record in standings.items():
            assert "team_name" in record
            assert "wins" in record
            assert "losses" in record
            assert "ties" in record

    def test_wins_losses_are_positive(self, league):
        standings = fantrax_client.get_standings(league)
        for rank, record in standings.items():
            assert record["wins"] >= 0
            assert record["losses"] >= 0


class TestRosters:
    def test_returns_all_teams(self, league):
        rosters = fantrax_client.get_all_rosters(league)
        assert len(rosters) == EXPECTED_TEAMS

    def test_our_roster_has_players(self, league):
        rosters = fantrax_client.get_all_rosters(league)
        our_roster = rosters[MY_TEAM]
        assert len(our_roster["players"]) > 0

    def test_player_has_required_fields(self, league):
        rosters = fantrax_client.get_all_rosters(league)
        for team_name, roster_info in rosters.items():
            for p in roster_info["players"]:
                assert "name" in p
                assert "player_id" in p
                assert "team" in p


class TestMatchupData:
    def test_can_fetch_period(self, league):
        data = fantrax_client.get_matchup_period_data(league, 14)
        assert data["period"] == 14
        assert len(data["rows"]) == EXPECTED_TEAMS

    def test_has_all_categories_in_columns(self, league):
        data = fantrax_client.get_matchup_period_data(league, 14)
        for cat in CATEGORIES:
            assert cat in data["columns"], f"Missing category: {cat}"

    def test_rows_have_win_loss(self, league):
        data = fantrax_client.get_matchup_period_data(league, 14)
        for row in data["rows"]:
            assert "W" in row
            assert "L" in row
            assert "team_name" in row


class TestFreeAgents:
    def test_returns_players(self):
        fas = fantrax_client.get_free_agents()
        assert len(fas) > 50  # Should have many free agents

    def test_player_has_required_fields(self):
        fas = fantrax_client.get_free_agents()
        for fa in fas:
            assert "name" in fa
            assert "player_id" in fa
            assert "team" in fa
            assert "position" in fa
            assert "status" in fa
            assert fa["status"] in ("FA", "WW")

    def test_no_rostered_players_in_results(self):
        fas = fantrax_client.get_free_agents()
        fa_ids = {fa["player_id"] for fa in fas}
        # Verify none of these are marked as on a team
        for fa in fas:
            assert fa["status"] != "T"


class TestPublicAPI:
    def test_get_league_info(self):
        info = fantrax_client.get_league_info()
        assert info["leagueName"] == "A10 Fantasy"
        assert "playerInfo" in info
        assert "teamInfo" in info

    def test_get_player_ids(self):
        players = fantrax_client.get_player_ids()
        assert len(players) > 1000  # Many NCAAB players
        # Check a sample has expected fields
        sample = next(iter(players.values()))
        assert "name" in sample
        assert "fantraxId" in sample
