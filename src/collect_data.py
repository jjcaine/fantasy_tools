"""Pull and cache all data from NCAA API and FanTrax."""

import json
import time
from pathlib import Path

import pandas as pd

from src import ncaa_client, fantrax_client

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def save_json(data, filename: str):
    with open(DATA_DIR / filename, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"  Saved {filename}")


def collect_ncaa_individual_stats():
    """Pull all individual stat categories for A-10 players and merge into one DataFrame."""
    print("Collecting NCAA individual stats...")

    # Start with PPG (136) - richest endpoint with FGM, 3FG, FT, PTS
    all_ppg = ncaa_client.get_individual_stats(136)
    a10_ppg = ncaa_client.filter_a10_players(all_ppg)
    print(f"  PPG: {len(a10_ppg)} A-10 players found")

    # Build base dataframe from PPG data
    df = pd.DataFrame(a10_ppg)
    # Rename columns for clarity
    df = df.rename(columns={"3FG": "ThreePM"})

    time.sleep(0.5)

    # Pull remaining stat categories and merge
    stat_endpoints = {
        137: {"merge_cols": ["REB", "RPG"], "label": "RPG"},
        138: {"merge_cols": ["BLKS", "BKPG"], "label": "BPG"},
        139: {"merge_cols": ["ST", "STPG"], "label": "SPG"},
        140: {"merge_cols": ["AST", "APG"], "label": "APG"},
        141: {"merge_cols": ["FGA", "FG%"], "label": "FG%"},
        142: {"merge_cols": ["FTA", "FT%"], "label": "FT%"},
    }

    for stat_id, info in stat_endpoints.items():
        all_data = ncaa_client.get_individual_stats(stat_id)
        a10_data = ncaa_client.filter_a10_players(all_data)
        print(f"  {info['label']}: {len(a10_data)} A-10 players")

        stat_df = pd.DataFrame(a10_data)[["Name", "Team"] + info["merge_cols"]]
        df = df.merge(stat_df, on=["Name", "Team"], how="outer", suffixes=("", f"_{info['label']}"))
        time.sleep(0.5)

    # Convert numeric columns
    numeric_cols = ["G", "FGM", "ThreePM", "FT", "PTS", "PPG", "REB", "RPG",
                    "BLKS", "BKPG", "ST", "STPG", "AST", "APG", "FGA", "FG%",
                    "FTA", "FT%"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Calculate eFG% = (FGM + 0.5 * 3PM) / FGA
    if all(c in df.columns for c in ["FGM", "ThreePM", "FGA"]):
        df["eFG%"] = ((df["FGM"] + 0.5 * df["ThreePM"]) / df["FGA"]).round(4)

    # Calculate turnovers per game from team stats? Individual TO not directly available
    # from these endpoints - we'll need to handle this differently

    df.to_csv(DATA_DIR / "a10_players.csv", index=False)
    save_json(df.to_dict(orient="records"), "a10_players.json")
    print(f"  Total: {len(df)} A-10 players with merged stats")
    return df


def collect_ncaa_team_stats():
    """Pull team-level stats for A-10 teams."""
    print("Collecting NCAA team stats...")

    team_data = {}
    for stat_id, stat_name in ncaa_client.TEAM_STATS.items():
        all_teams = ncaa_client.get_team_stats(stat_id)
        a10_teams = ncaa_client.filter_a10_teams(all_teams)
        team_data[stat_name] = a10_teams
        print(f"  {stat_name}: {len(a10_teams)} A-10 teams")
        time.sleep(0.5)

    save_json(team_data, "a10_team_stats.json")
    return team_data


def collect_ncaa_standings():
    """Pull A-10 conference standings."""
    print("Collecting A-10 standings...")
    standings = ncaa_client.get_standings()
    save_json(standings, "a10_standings.json")
    print(f"  {len(standings)} teams in standings")
    return standings


def collect_fantrax_data():
    """Pull all FanTrax league data."""
    print("Connecting to FanTrax...")
    league = fantrax_client.get_league()
    print(f"  Connected to: {league.name}")

    print("Pulling standings...")
    standings = fantrax_client.get_standings(league)
    save_json(standings, "fantrax_standings.json")

    print("Pulling all team rosters...")
    rosters = fantrax_client.get_all_rosters(league)
    save_json(rosters, "fantrax_rosters.json")

    print("Pulling matchup history...")
    matchups = fantrax_client.get_matchup_history(league)
    save_json(matchups, "fantrax_matchups.json")

    print("Pulling transactions...")
    transactions = fantrax_client.get_transactions(league)
    save_json(transactions, "fantrax_transactions.json")

    return {
        "standings": standings,
        "rosters": rosters,
        "matchups": matchups,
        "transactions": transactions,
    }


def collect_a10_schedule():
    """Pull A-10 game schedule for playoff periods (Feb-Mar 2026)."""
    print("Collecting A-10 schedule for Feb-Mar 2026...")

    schedule_data = {}
    for month in [2, 3]:
        sched = ncaa_client.get_schedule(2026, month)
        schedule_data[f"2026-{month:02d}"] = sched
        time.sleep(0.5)

    save_json(schedule_data, "a10_schedule.json")
    return schedule_data


if __name__ == "__main__":
    print("=" * 60)
    print("Fantasy Basketball Data Collection")
    print("=" * 60)

    print("\n--- NCAA Data ---")
    collect_ncaa_standings()
    collect_ncaa_individual_stats()
    collect_ncaa_team_stats()
    collect_a10_schedule()

    print("\n--- FanTrax Data ---")
    collect_fantrax_data()

    print("\nDone! All data saved to data/")
