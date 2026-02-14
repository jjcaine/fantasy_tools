"""Collect box scores for all A-10 games and aggregate player stats."""

import json
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from src import ncaa_client
from src.schedule_scanner import _is_a10_team, _normalize_team_name, scan_date

DATA_DIR = Path(__file__).parent.parent / "data"

# Full season: Nov 3, 2025 - current (Feb 14, 2026)
SEASON_START = date(2025, 11, 3)
SEASON_END = date(2026, 2, 14)


def collect_all_a10_game_ids() -> list[dict]:
    """Scan every date of the season to find all A-10 games."""
    cache_path = DATA_DIR / "a10_all_games.json"
    if cache_path.exists():
        with open(cache_path) as f:
            return json.load(f)

    all_games = []
    seen_ids = set()
    d = SEASON_START
    while d <= SEASON_END:
        if d.month in (4, 5, 6, 7, 8, 9, 10):  # Skip off-season months
            d += timedelta(days=1)
            continue
        games = scan_date(d)
        for g in games:
            gid = g.get("game_id")
            if gid and gid not in seen_ids:
                seen_ids.add(gid)
                all_games.append(g)
        if d.day == 1:
            print(f"  Scanned through {d}... ({len(all_games)} games found)")
        d += timedelta(days=1)
        time.sleep(0.15)

    DATA_DIR.mkdir(exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(all_games, f, indent=2)
    print(f"  Total: {len(all_games)} A-10 games found")
    return all_games


def collect_boxscores(game_list: list[dict]) -> list[dict]:
    """Pull box scores for a list of games. Returns list of player stat rows."""
    cache_path = DATA_DIR / "a10_boxscores_raw.json"
    if cache_path.exists():
        with open(cache_path) as f:
            return json.load(f)

    all_player_stats = []
    errors = []

    for i, game in enumerate(game_list):
        game_id = game.get("game_id", "")
        game_date = game.get("date", "")
        if not game_id:
            continue

        try:
            box = ncaa_client.get_game_boxscore(game_id)
        except Exception as e:
            errors.append({"game_id": game_id, "error": str(e)})
            time.sleep(0.3)
            continue

        teams_info = {t["teamId"]: t for t in box.get("teams", [])}
        for team_box in box.get("teamBoxscore", []):
            team_id = str(team_box.get("teamId", ""))
            team_info = teams_info.get(team_id, teams_info.get(int(team_id) if team_id.isdigit() else team_id, {}))
            team_name = team_info.get("nameShort", "")

            if not _is_a10_team(team_name):
                continue

            team_name = _normalize_team_name(team_name)

            for ps in team_box.get("playerStats", []):
                # Skip players with 0 minutes (DNP)
                mins = ps.get("minutesPlayed", "0")
                if mins == "0" or mins == "":
                    continue

                all_player_stats.append({
                    "game_id": game_id,
                    "date": game_date,
                    "team": team_name,
                    "first_name": ps.get("firstName", ""),
                    "last_name": ps.get("lastName", ""),
                    "position": ps.get("position", ""),
                    "minutes": int(mins) if mins.isdigit() else 0,
                    "fgm": int(ps.get("fieldGoalsMade", 0) or 0),
                    "fga": int(ps.get("fieldGoalsAttempted", 0) or 0),
                    "ftm": int(ps.get("freeThrowsMade", 0) or 0),
                    "fta": int(ps.get("freeThrowsAttempted", 0) or 0),
                    "tpm": int(ps.get("threePointsMade", 0) or 0),
                    "tpa": int(ps.get("threePointsAttempted", 0) or 0),
                    "oreb": int(ps.get("offensiveRebounds", 0) or 0),
                    "reb": int(ps.get("totalRebounds", 0) or 0),
                    "ast": int(ps.get("assists", 0) or 0),
                    "to": int(ps.get("turnovers", 0) or 0),
                    "stl": int(ps.get("steals", 0) or 0),
                    "blk": int(ps.get("blockedShots", 0) or 0),
                    "pf": int(ps.get("personalFouls", 0) or 0),
                    "pts": int(ps.get("points", 0) or 0),
                })

        if (i + 1) % 25 == 0:
            print(f"  Processed {i + 1}/{len(game_list)} games ({len(all_player_stats)} player rows)")
        time.sleep(0.15)

    with open(cache_path, "w") as f:
        json.dump(all_player_stats, f, indent=2)

    if errors:
        with open(DATA_DIR / "boxscore_errors.json", "w") as f:
            json.dump(errors, f, indent=2)
        print(f"  {len(errors)} games had errors (saved to boxscore_errors.json)")

    print(f"  Total: {len(all_player_stats)} player-game rows collected")
    return all_player_stats


def aggregate_player_stats(player_game_rows: list[dict]) -> pd.DataFrame:
    """Aggregate per-game stats into season totals and per-game averages."""
    df = pd.DataFrame(player_game_rows)

    if df.empty:
        return df

    df["name"] = df["first_name"] + " " + df["last_name"]

    # Aggregate season totals
    agg = df.groupby(["name", "team", "position"]).agg(
        games=("game_id", "nunique"),
        total_minutes=("minutes", "sum"),
        fgm=("fgm", "sum"),
        fga=("fga", "sum"),
        ftm=("ftm", "sum"),
        fta=("fta", "sum"),
        tpm=("tpm", "sum"),
        tpa=("tpa", "sum"),
        reb=("reb", "sum"),
        ast=("ast", "sum"),
        stl=("stl", "sum"),
        blk=("blk", "sum"),
        to=("to", "sum"),
        pts=("pts", "sum"),
        pf=("pf", "sum"),
    ).reset_index()

    # Per-game averages
    agg["ppg"] = (agg["pts"] / agg["games"]).round(1)
    agg["rpg"] = (agg["reb"] / agg["games"]).round(1)
    agg["apg"] = (agg["ast"] / agg["games"]).round(1)
    agg["spg"] = (agg["stl"] / agg["games"]).round(1)
    agg["bpg"] = (agg["blk"] / agg["games"]).round(1)
    agg["topg"] = (agg["to"] / agg["games"]).round(1)
    agg["tpm_pg"] = (agg["tpm"] / agg["games"]).round(1)
    agg["mpg"] = (agg["total_minutes"] / agg["games"]).round(1)

    # Percentages
    agg["fg_pct"] = (agg["fgm"] / agg["fga"]).round(4)
    agg["ft_pct"] = (agg["ftm"] / agg["fta"]).round(4)
    agg["tp_pct"] = (agg["tpm"] / agg["tpa"]).round(4)
    agg["efg_pct"] = ((agg["fgm"] + 0.5 * agg["tpm"]) / agg["fga"]).round(4)

    # Sort by PPG descending
    agg = agg.sort_values("ppg", ascending=False).reset_index(drop=True)

    # Save
    agg.to_csv(DATA_DIR / "a10_players_complete.csv", index=False)
    agg.to_json(DATA_DIR / "a10_players_complete.json", orient="records", indent=2)
    print(f"  Saved {len(agg)} players with complete stats")

    return agg


if __name__ == "__main__":
    print("=" * 60)
    print("A-10 Box Score Collection & Aggregation")
    print("=" * 60)

    print("\nStep 1: Finding all A-10 games this season...")
    games = collect_all_a10_game_ids()

    print(f"\nStep 2: Pulling box scores for {len(games)} games...")
    rows = collect_boxscores(games)

    print("\nStep 3: Aggregating player stats...")
    df = aggregate_player_stats(rows)

    print(f"\nDone! {len(df)} players with complete season stats.")
    print("\nTop 15 by PPG:")
    print(df[["name", "team", "games", "ppg", "rpg", "apg", "spg", "bpg", "tpm_pg", "topg", "efg_pct", "ft_pct"]].head(15).to_string(index=False))
