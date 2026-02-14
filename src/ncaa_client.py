"""Client for the local NCAA API (henrygd/ncaa-api) running in Docker."""

import requests
import time

BASE_URL = "http://localhost:3000"

# A-10 team names as they appear on ncaa.com
A10_TEAMS = [
    "Davidson", "Dayton", "Duquesne", "Fordham", "George Mason",
    "George Washington", "La Salle", "Loyola Chicago", "Rhode Island",
    "Richmond", "Saint Bonaventure", "Saint Joseph's", "Saint Louis", "VCU",
]

# Short names used in FanTrax player pool config
A10_SHORT_NAMES = {
    "Davidson": "David",
    "Dayton": "Dayt",
    "Duquesne": "Duques",
    "Fordham": "Ford",
    "George Mason": "GMas",
    "George Washington": "GrgWas",
    "La Salle": "LaSal",
    "Loyola Chicago": "LoyIL",
    "Rhode Island": "URI",
    "Richmond": "Rich",
    "Saint Bonaventure": "StBon",
    "Saint Joseph's": "StJos",
    "Saint Louis": "StLou",
    "VCU": "VCU",
}

# Verified individual stat endpoint IDs
INDIVIDUAL_STATS = {
    136: {"name": "Points Per Game", "fields": ["G", "FGM", "3FG", "FT", "PTS", "PPG"]},
    137: {"name": "Rebounds Per Game", "fields": ["G", "REB", "RPG"]},
    138: {"name": "Blocks Per Game", "fields": ["G", "BLKS", "BKPG"]},
    139: {"name": "Steals Per Game", "fields": ["G", "ST", "STPG"]},
    140: {"name": "Assists Per Game", "fields": ["G", "AST", "APG"]},
    141: {"name": "Field Goal %", "fields": ["G", "FGM", "FGA", "FG%"]},
    142: {"name": "Free Throw %", "fields": ["G", "FT", "FTA", "FT%"]},
    143: {"name": "3-Point %", "fields": ["G", "3FG", "3FGA", "3FG%"]},
    144: {"name": "3-Pointers Per Game", "fields": ["G", "3FG", "3PG"]},
}

# Verified team stat endpoint IDs
TEAM_STATS = {
    145: "Scoring Offense",
    146: "Scoring Defense",
    147: "Scoring Margin",
    148: "Field Goal Percentage",
    149: "Field Goal Percentage Defense",
    150: "Free Throw Percentage",
    151: "Rebound Margin",
    152: "Three Point Percentage",
    153: "Three Pointers Per Game",
    168: "Winning Percentage",
    214: "Blocks Per Game",
    215: "Steals Per Game",
    216: "Assists Per Game",
    217: "Turnovers Per Game",
}


def _get(path: str, params: dict | None = None) -> dict:
    """Make a GET request to the NCAA API."""
    resp = requests.get(f"{BASE_URL}{path}", params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _get_all_pages(path: str, delay: float = 0.2) -> list[dict]:
    """Fetch all pages of a paginated endpoint and return combined data rows."""
    all_data = []
    page = 1
    while True:
        result = _get(path, params={"page": page})
        all_data.extend(result.get("data", []))
        if page >= result.get("pages", 1):
            break
        page += 1
        time.sleep(delay)
    return all_data


def get_standings() -> list[dict]:
    """Get A-10 conference standings."""
    data = _get("/standings/basketball-men/d1")
    for conf in data.get("data", []):
        if "Atlantic 10" in conf.get("conference", ""):
            return conf["standings"]
    return []


def get_team_stats(stat_id: int) -> list[dict]:
    """Get team stats for a given stat category ID. Returns all pages combined."""
    return _get_all_pages(f"/stats/basketball-men/d1/current/team/{stat_id}")


def get_individual_stats(stat_id: int) -> list[dict]:
    """Get individual player stats for a given stat category ID. Returns all pages."""
    return _get_all_pages(f"/stats/basketball-men/d1/current/individual/{stat_id}")


def get_schedule(year: int, month: int) -> dict:
    """Get game schedule for a given month."""
    return _get(f"/schedule/basketball-men/d1/{year}/{month:02d}")


def get_scoreboard(year: int, month: int, day: int) -> dict:
    """Get scoreboard for a specific date."""
    return _get(f"/scoreboard/basketball-men/d1/{year}/{month:02d}/{day:02d}/all-conf")


def get_game_boxscore(game_id: str) -> dict:
    """Get box score for a specific game."""
    return _get(f"/game/{game_id}/boxscore")


def filter_a10_players(players: list[dict]) -> list[dict]:
    """Filter a list of player stat rows to only A-10 teams."""
    filtered = []
    for p in players:
        team = p.get("Team", "") or p.get("team", "")
        if any(name.lower() in team.lower() for name in A10_TEAMS):
            filtered.append(p)
    return filtered


def filter_a10_teams(teams: list[dict]) -> list[dict]:
    """Filter a list of team stat rows to only A-10 teams."""
    filtered = []
    for t in teams:
        team = t.get("Team", "") or t.get("team", "")
        if any(name.lower() in team.lower() for name in A10_TEAMS):
            filtered.append(t)
    return filtered
