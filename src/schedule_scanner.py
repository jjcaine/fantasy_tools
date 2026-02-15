"""Scan A-10 game schedules for playoff periods using the scoreboard API.

Uses conference metadata (conferenceSeo) from the NCAA scoreboard API for
reliable team identification instead of fragile name substring matching.
"""

import json
import time
from datetime import date, timedelta
from pathlib import Path

from src import ncaa_client

DATA_DIR = Path(__file__).parent.parent / "data"

A10_CONFERENCE_SEO = "atlantic-10"

# Canonical A-10 team names keyed by exact NCAA API nameShort values.
# Used only when conferenceSeo is present to get our canonical name.
_NCAA_NAME_SHORT_TO_CANONICAL: dict[str, str] = {
    "Davidson": "Davidson",
    "Dayton": "Dayton",
    "Duquesne": "Duquesne",
    "Fordham": "Fordham",
    "George Mason": "George Mason",
    "George Washington": "George Washington",
    "La Salle": "La Salle",
    "Loyola Chicago": "Loyola Chicago",
    "Rhode Island": "Rhode Island",
    "Richmond": "Richmond",
    "Saint Bonaventure": "St. Bonaventure",
    "St. Bonaventure": "St. Bonaventure",
    "Saint Joseph's": "Saint Joseph's",
    "St. Joseph's": "Saint Joseph's",
    "Saint Louis": "Saint Louis",
    "VCU": "VCU",
}

# Fallback substring matching — used ONLY when conference metadata is missing.
# Each entry must be specific enough to avoid cross-conference collisions.
A10_SEARCH_NAMES = [
    "davidson", "dayton", "duquesne", "fordham", "george mason",
    "george washington", "la salle", "loyola chicago", "rhode island",
    "richmond", "bonaventure", "joseph", "saint louis", "vcu",
]

# Playoff periods
PERIODS = {
    15: (date(2026, 2, 16), date(2026, 2, 22)),  # Round 1
    16: (date(2026, 2, 23), date(2026, 3, 1)),    # Round 2
    17: (date(2026, 3, 2), date(2026, 3, 8)),      # Round 3 (Finals)
}

# Also include current period for context
PERIODS[14] = (date(2026, 2, 9), date(2026, 2, 15))


def _team_has_a10_conference(team_data: dict) -> bool:
    """Check if a team's conference metadata indicates A-10."""
    conferences = team_data.get("conferences", [])
    for conf in conferences:
        if conf.get("conferenceSeo") == A10_CONFERENCE_SEO:
            return True
    return False


def _is_a10_game(game_data: dict) -> bool:
    """Check if a game involves at least one A-10 team using conference metadata.

    Primary: checks conferenceSeo == "atlantic-10".
    Fallback: if neither team has conference data, falls back to name matching.
    """
    away = game_data.get("away", {})
    home = game_data.get("home", {})

    # Check if conference data is available on either team
    away_has_conf = bool(away.get("conferences"))
    home_has_conf = bool(home.get("conferences"))

    if away_has_conf or home_has_conf:
        return _team_has_a10_conference(away) or _team_has_a10_conference(home)

    # Fallback: no conference data at all — use name substring matching
    away_name = away.get("names", {}).get("short", "")
    home_name = home.get("names", {}).get("short", "")
    return _is_a10_team_by_name(away_name) or _is_a10_team_by_name(home_name)


def _is_a10_team_by_name(name: str) -> bool:
    """Fallback name-based check. Only used when conference metadata is missing."""
    name_lower = name.lower()
    return any(t in name_lower for t in A10_SEARCH_NAMES)


def _normalize_team_name(name: str) -> str:
    """Normalize team names to a consistent format.

    Tries exact match on NCAA nameShort first, then falls back to substring matching.
    """
    if name in _NCAA_NAME_SHORT_TO_CANONICAL:
        return _NCAA_NAME_SHORT_TO_CANONICAL[name]

    # Fallback substring matching for non-exact names
    name_lower = name.lower()
    for search, canonical in [
        ("davidson", "Davidson"),
        ("dayton", "Dayton"),
        ("duquesne", "Duquesne"),
        ("fordham", "Fordham"),
        ("george mason", "George Mason"),
        ("george washington", "George Washington"),
        ("la salle", "La Salle"),
        ("loyola chicago", "Loyola Chicago"),
        ("rhode island", "Rhode Island"),
        ("richmond", "Richmond"),
        ("bonaventure", "St. Bonaventure"),
        ("joseph", "Saint Joseph's"),
        ("saint louis", "Saint Louis"),
        ("vcu", "VCU"),
    ]:
        if search in name_lower:
            return canonical
    return name


def _extract_team_id(team_data: dict) -> str | None:
    """Extract numeric team ID from scoreboard team data if available."""
    # The scoreboard API nests IDs in names.char6 or a teamId field;
    # we look in several places depending on API shape.
    names = team_data.get("names", {})
    # Some API responses include teamId directly
    team_id = team_data.get("teamId")
    if team_id:
        return str(team_id)
    # Try seoname as a stable identifier
    seoname = names.get("seo")
    if seoname:
        return seoname
    return None


def scan_date(d: date) -> tuple[list[dict], dict[str, str]]:
    """Get all A-10 games for a given date.

    Returns:
        (games, a10_team_ids): games list and dict mapping team IDs/seonames
        to canonical team names for confirmed A-10 teams.
    """
    try:
        data = ncaa_client.get_scoreboard(d.year, d.month, d.day)
    except Exception:
        return [], {}

    games = data.get("games", [])
    a10_games = []
    a10_team_ids: dict[str, str] = {}

    for g in games:
        game_data = g.get("game", g)

        if not _is_a10_game(game_data):
            continue

        away = game_data.get("away", {})
        home = game_data.get("home", {})
        away_name = away.get("names", {}).get("short", "")
        home_name = home.get("names", {}).get("short", "")

        # Record team IDs for confirmed A-10 teams
        for side_data, side_name in [(away, away_name), (home, home_name)]:
            if _team_has_a10_conference(side_data):
                canonical = _normalize_team_name(side_name)
                # Collect all available IDs
                tid = _extract_team_id(side_data)
                if tid:
                    a10_team_ids[tid] = canonical
                char6 = side_data.get("names", {}).get("char6", "")
                if char6:
                    a10_team_ids[char6] = canonical

        a10_games.append({
            "date": str(d),
            "game_id": game_data.get("gameID", ""),
            "away": _normalize_team_name(away_name),
            "away_score": away.get("score", ""),
            "home": _normalize_team_name(home_name),
            "home_score": home.get("score", ""),
            "state": game_data.get("gameState", game_data.get("currentPeriod", "")),
        })

    return a10_games, a10_team_ids


def scan_period(period_num: int) -> dict:
    """Scan all dates in a scoring period for A-10 games."""
    start, end = PERIODS[period_num]
    all_games = []
    games_per_team = {}

    d = start
    while d <= end:
        print(f"  Scanning {d}...")
        day_games, _ = scan_date(d)
        all_games.extend(day_games)

        for game in day_games:
            for team in [game["away"], game["home"]]:
                if team not in games_per_team:
                    games_per_team[team] = []
                games_per_team[team].append(game["date"])

        d += timedelta(days=1)
        time.sleep(0.3)

    return {
        "period": period_num,
        "start": str(start),
        "end": str(end),
        "games": all_games,
        "games_per_team": {t: len(dates) for t, dates in sorted(games_per_team.items())},
        "game_dates_per_team": games_per_team,
    }


def scan_all_periods():
    """Scan all playoff periods and save results."""
    results = {}
    for period_num in sorted(PERIODS.keys()):
        print(f"Period {period_num}:")
        results[period_num] = scan_period(period_num)
        print(f"  Total games: {len(results[period_num]['games'])}")
        print(f"  Games per team: {results[period_num]['games_per_team']}")
        print()

    DATA_DIR.mkdir(exist_ok=True)
    with open(DATA_DIR / "a10_schedule.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Saved a10_schedule.json")
    return results


if __name__ == "__main__":
    scan_all_periods()
