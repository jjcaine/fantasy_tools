"""Collect box scores for all A-10 games and aggregate player stats.

Supports incremental updates - only scans new dates and pulls new box scores
since the last run. Re-aggregates all stats after collecting new data.

Uses conference-based filtering from schedule_scanner and a team ID allowlist
for boxscore parsing instead of fragile name substring matching.
"""

import json
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from src import ncaa_client
from src.schedule_scanner import _normalize_team_name, scan_date

DATA_DIR = Path(__file__).parent.parent / "data"

SEASON_START = date(2025, 11, 3)
SEASON_END = date(2026, 3, 8)  # End of Period 17

TEAM_IDS_PATH = DATA_DIR / "a10_team_ids.json"


def _today() -> date:
    return date.today()


def _load_team_ids() -> dict[str, str]:
    """Load the A-10 team ID allowlist from disk."""
    if TEAM_IDS_PATH.exists():
        with open(TEAM_IDS_PATH) as f:
            return json.load(f)
    return {}


def _save_team_ids(team_ids: dict[str, str]) -> None:
    """Save the A-10 team ID allowlist to disk."""
    DATA_DIR.mkdir(exist_ok=True)
    with open(TEAM_IDS_PATH, "w") as f:
        json.dump(team_ids, f, indent=2, sort_keys=True)


def collect_all_a10_game_ids() -> list[dict]:
    """Scan season dates for A-10 games. Incrementally scans only new dates.

    Also builds and saves an A-10 team ID allowlist from confirmed A-10 games
    (teams identified by conferenceSeo in the scoreboard API).
    """
    cache_path = DATA_DIR / "a10_all_games.json"
    meta_path = DATA_DIR / "a10_all_games_meta.json"

    # Load existing data and metadata
    existing_games = []
    seen_ids = set()
    last_scanned = None

    if cache_path.exists():
        with open(cache_path) as f:
            existing_games = json.load(f)
        seen_ids = {g["game_id"] for g in existing_games if g.get("game_id")}

    if meta_path.exists():
        with open(meta_path) as f:
            meta = json.load(f)
        last_scanned = date.fromisoformat(meta["last_scanned_date"])

    # Load existing team IDs (accumulate across runs)
    all_team_ids = _load_team_ids()

    # Determine scan range
    scan_start = (last_scanned + timedelta(days=1)) if last_scanned else SEASON_START
    scan_end = min(_today(), SEASON_END)

    if scan_start > scan_end:
        print(f"  Games already up to date through {last_scanned}")
        return existing_games

    print(f"  Scanning {scan_start} through {scan_end}...")
    new_games = []
    d = scan_start
    while d <= scan_end:
        games, day_team_ids = scan_date(d)
        all_team_ids.update(day_team_ids)
        for g in games:
            gid = g.get("game_id")
            if gid and gid not in seen_ids:
                seen_ids.add(gid)
                new_games.append(g)
        d += timedelta(days=1)
        time.sleep(0.15)

    all_games = existing_games + new_games
    print(f"  Found {len(new_games)} new games ({len(all_games)} total)")

    # Save updated cache and team IDs
    DATA_DIR.mkdir(exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(all_games, f, indent=2)
    with open(meta_path, "w") as f:
        json.dump({"last_scanned_date": scan_end.isoformat()}, f)

    _save_team_ids(all_team_ids)
    print(f"  Saved {len(all_team_ids)} A-10 team IDs to a10_team_ids.json")

    return all_games


def _is_a10_team_by_id(team_id: str, team_name: str, team_ids: dict[str, str]) -> bool:
    """Check if a team is A-10 using the team ID allowlist.

    Checks team_id (numeric) first, then falls back to checking if the
    team name matches any known A-10 canonical name in the allowlist values.
    """
    if str(team_id) in team_ids:
        return True
    # Check by canonical team name (values in the allowlist)
    canonical = _normalize_team_name(team_name)
    return canonical in team_ids.values()


def _parse_boxscore_players(
    box: dict,
    game_id: str,
    game_date: str,
    team_ids: dict[str, str],
) -> list[dict]:
    """Extract A-10 player stat rows from a single box score response.

    Uses the team ID allowlist for filtering instead of name substring matching.
    """
    rows = []
    teams_info = {t["teamId"]: t for t in box.get("teams", [])}

    for team_box in box.get("teamBoxscore", []):
        team_id = str(team_box.get("teamId", ""))
        team_info = teams_info.get(team_id, teams_info.get(
            int(team_id) if team_id.isdigit() else team_id, {}
        ))
        team_name = team_info.get("nameShort", "")

        if not _is_a10_team_by_id(team_id, team_name, team_ids):
            continue

        team_name = _normalize_team_name(team_name)

        for ps in team_box.get("playerStats", []):
            mins_raw = ps.get("minutesPlayed", "0")
            try:
                mins = round(float(mins_raw))
            except (ValueError, TypeError):
                mins = 0
            if mins == 0:
                continue

            rows.append({
                "game_id": game_id,
                "date": game_date,
                "team": team_name,
                "team_id": team_id,
                "first_name": ps.get("firstName", ""),
                "last_name": ps.get("lastName", ""),
                "position": ps.get("position", ""),
                "minutes": mins,
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

    return rows


def collect_boxscores(game_list: list[dict]) -> list[dict]:
    """Pull box scores for games. Incrementally fetches only new game IDs.

    Uses the team ID allowlist for A-10 filtering in boxscore parsing.
    """
    cache_path = DATA_DIR / "a10_boxscores_raw.json"

    # Load existing box score data
    existing_rows = []
    fetched_game_ids = set()

    if cache_path.exists():
        with open(cache_path) as f:
            existing_rows = json.load(f)
        fetched_game_ids = {r["game_id"] for r in existing_rows}

    # Find games we haven't fetched yet
    new_games = [g for g in game_list if g.get("game_id") and g["game_id"] not in fetched_game_ids]

    if not new_games:
        print(f"  Box scores already up to date ({len(existing_rows)} player rows)")
        return existing_rows

    # Load team ID allowlist
    team_ids = _load_team_ids()
    if not team_ids:
        print("  WARNING: No team ID allowlist found. Run game collection first.")

    print(f"  Fetching box scores for {len(new_games)} new games...")
    new_rows = []
    errors = []

    for i, game in enumerate(new_games):
        game_id = game["game_id"]
        game_date = game.get("date", "")

        try:
            box = ncaa_client.get_game_boxscore(game_id)
            new_rows.extend(_parse_boxscore_players(box, game_id, game_date, team_ids))
        except Exception as e:
            errors.append({"game_id": game_id, "error": str(e)})

        if (i + 1) % 25 == 0:
            print(f"    Processed {i + 1}/{len(new_games)} new games")
        time.sleep(0.15)

    all_rows = existing_rows + new_rows
    print(f"  Added {len(new_rows)} new player rows ({len(all_rows)} total)")

    if errors:
        print(f"  {len(errors)} games had errors")

    # Save updated cache
    with open(cache_path, "w") as f:
        json.dump(all_rows, f, indent=2)

    return all_rows


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
    agg.to_csv(DATA_DIR / "a10_players.csv", index=False)
    agg.to_json(DATA_DIR / "a10_players.json", orient="records", indent=2)
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
