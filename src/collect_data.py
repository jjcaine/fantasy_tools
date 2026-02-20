"""Pull and cache all data from NCAA API, FanTrax, and box scores."""

import json
from pathlib import Path
from typing import Callable

from src import ncaa_client, fantrax_client
from src.boxscore_collector import collect_all_a10_game_ids, collect_boxscores, aggregate_player_stats
from src.schedule_scanner import scan_all_periods
from src.validation import run_validation

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def save_json(data, filename: str, log: Callable[..., object] = print):
    with open(DATA_DIR / filename, "w") as f:
        json.dump(data, f, indent=2, default=str)
    log(f"  Saved {filename}")


def collect_ncaa_standings(log: Callable[..., object] = print):
    """Pull A-10 conference standings."""
    log("Collecting A-10 standings...")
    standings = ncaa_client.get_standings()
    save_json(standings, "a10_standings.json", log=log)
    log(f"  {len(standings)} teams in standings")
    return standings


def collect_player_stats(log: Callable[..., object] = print):
    """Collect complete A-10 player stats from box scores."""
    log("Collecting A-10 player stats from box scores...")
    games = collect_all_a10_game_ids()
    rows = collect_boxscores(games)
    df = aggregate_player_stats(rows)
    return df


def collect_fantrax_data(log: Callable[..., object] = print):
    """Pull all FanTrax league data."""
    log("Connecting to FanTrax...")
    league = fantrax_client.get_league()
    log(f"  Connected to: {league.name}")

    log("Pulling standings...")
    standings = fantrax_client.get_standings(league)
    save_json(standings, "fantrax_standings.json", log=log)

    log("Pulling all team rosters...")
    rosters = fantrax_client.get_all_rosters(league)
    save_json(rosters, "fantrax_rosters.json", log=log)

    log("Pulling matchup history (all periods)...")
    all_matchups = {}
    for period_num in range(1, 18):
        data = fantrax_client.get_matchup_period_data(league, period_num)
        if data["rows"]:
            all_matchups[period_num] = data
    save_json(all_matchups, "fantrax_all_matchups.json", log=log)

    log("Pulling free agents...")
    free_agents = fantrax_client.get_free_agents()
    save_json(free_agents, "fantrax_free_agents.json", log=log)

    return {
        "standings": standings,
        "rosters": rosters,
        "matchups": all_matchups,
        "free_agents": free_agents,
    }


if __name__ == "__main__":
    print("=" * 60)
    print("Fantasy Basketball Data Collection")
    print("=" * 60)

    print("\n--- NCAA Data ---")
    collect_ncaa_standings()
    collect_player_stats()

    print("\n--- A-10 Schedule ---")
    scan_all_periods()

    print("\n--- FanTrax Data ---")
    collect_fantrax_data()

    print("\n--- Validation ---")
    run_validation()

    print("\nDone! All data saved to data/")
