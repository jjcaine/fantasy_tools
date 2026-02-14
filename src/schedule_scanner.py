"""Scan A-10 game schedules for playoff periods using the scoreboard API."""

import json
import time
from datetime import date, timedelta
from pathlib import Path

from src import ncaa_client

DATA_DIR = Path(__file__).parent.parent / "data"

A10_SEARCH_NAMES = [
    "davidson", "dayton", "duquesne", "fordham", "george mason",
    "george washington", "la salle", "loyola", "rhode island",
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


def _is_a10_team(name: str) -> bool:
    name_lower = name.lower()
    return any(t in name_lower for t in A10_SEARCH_NAMES)


def _normalize_team_name(name: str) -> str:
    """Normalize team names to a consistent format."""
    name_lower = name.lower()
    for search, canonical in [
        ("davidson", "Davidson"),
        ("dayton", "Dayton"),
        ("duquesne", "Duquesne"),
        ("fordham", "Fordham"),
        ("george mason", "George Mason"),
        ("george washington", "George Washington"),
        ("la salle", "La Salle"),
        ("loyola", "Loyola Chicago"),
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


def scan_date(d: date) -> list[dict]:
    """Get all A-10 games for a given date."""
    try:
        data = ncaa_client.get_scoreboard(d.year, d.month, d.day)
    except Exception:
        return []

    games = data.get("games", [])
    a10_games = []

    for g in games:
        game_data = g.get("game", g)
        away = game_data.get("away", {})
        home = game_data.get("home", {})
        away_name = away.get("names", {}).get("short", "")
        home_name = home.get("names", {}).get("short", "")

        if _is_a10_team(away_name) or _is_a10_team(home_name):
            a10_games.append({
                "date": str(d),
                "game_id": game_data.get("gameID", ""),
                "away": _normalize_team_name(away_name),
                "away_score": away.get("score", ""),
                "home": _normalize_team_name(home_name),
                "home_score": home.get("score", ""),
                "state": game_data.get("gameState", game_data.get("currentPeriod", "")),
            })

    return a10_games


def scan_period(period_num: int) -> dict:
    """Scan all dates in a scoring period for A-10 games."""
    start, end = PERIODS[period_num]
    all_games = []
    games_per_team = {}

    d = start
    while d <= end:
        print(f"  Scanning {d}...")
        day_games = scan_date(d)
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
