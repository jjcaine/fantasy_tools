"""Post-pipeline validation against Fantrax roster/FA data.

Cross-references NCAA player data against Fantrax to detect data contamination
from non-A-10 teams (e.g., Loyola Maryland leaking in as Loyola Chicago).
"""

import json
import re
from pathlib import Path

from src.fantasy_math import (
    FANTRAX_TO_NCAA_TEAM,
    FANTRAX_SHORT_TO_NCAA,
    normalize_fantrax_team,
    _normalize_name,
)

DATA_DIR = Path(__file__).parent.parent / "data"

# Validation result statuses
CLEAN = "CLEAN"
MISMATCH_CONFIRMED = "MISMATCH_CONFIRMED"
NOT_IN_FANTRAX = "NOT_IN_FANTRAX"
NAME_MISMATCH = "NAME_MISMATCH"

# Expected A-10 teams (canonical names)
A10_TEAMS = {
    "Davidson", "Dayton", "Duquesne", "Fordham", "George Mason",
    "George Washington", "La Salle", "Loyola Chicago", "Rhode Island",
    "Richmond", "Saint Joseph's", "Saint Louis", "St. Bonaventure", "VCU",
}


def _load_json(filename: str) -> list | dict:
    path = DATA_DIR / filename
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []


def _build_fantrax_player_lookup(
    rosters: dict,
    free_agents: list[dict],
) -> dict[str, list[dict]]:
    """Build a normalized name -> list of Fantrax player entries lookup.

    Each entry has: name, team (NCAA canonical), source ("rostered"/"FA").
    """
    lookup: dict[str, list[dict]] = {}

    # Rostered players
    for team_name, team_data in rosters.items():
        for player in team_data.get("players", []):
            fantrax_team = player.get("team", "")
            ncaa_team = normalize_fantrax_team(fantrax_team)
            key = _normalize_name(player["name"])
            lookup.setdefault(key, []).append({
                "name": player["name"],
                "ncaa_team": ncaa_team,
                "fantrax_team": fantrax_team,
                "fantasy_team": team_name,
                "source": "rostered",
            })

    # Free agents
    for fa in free_agents:
        fantrax_team = fa.get("team", "")
        ncaa_team = normalize_fantrax_team(fantrax_team)
        key = _normalize_name(fa["name"])
        lookup.setdefault(key, []).append({
            "name": fa["name"],
            "ncaa_team": ncaa_team,
            "fantrax_team": fantrax_team,
            "fantasy_team": None,
            "source": "FA",
        })

    return lookup


def _find_in_fantrax(
    ncaa_name: str,
    ncaa_team: str,
    fantrax_lookup: dict[str, list[dict]],
) -> tuple[str, dict | None, str]:
    """Look up an NCAA player in Fantrax data.

    Returns (status, matched_entry, detail).
    """
    norm_name = _normalize_name(ncaa_name)

    if norm_name in fantrax_lookup:
        entries = fantrax_lookup[norm_name]

        # Check for exact team match
        for entry in entries:
            if entry["ncaa_team"] == ncaa_team:
                return CLEAN, entry, f"Matched in Fantrax ({entry['source']})"

        # Name matches but team doesn't — this is suspicious
        entry = entries[0]
        return (
            MISMATCH_CONFIRMED,
            entry,
            f"NCAA team '{ncaa_team}' != Fantrax team '{entry['ncaa_team']}' "
            f"(Fantrax raw: '{entry['fantrax_team']}')",
        )

    # Try last-name matching as a fuzzy fallback
    parts = ncaa_name.split()
    if len(parts) >= 2:
        last_name = _normalize_name(parts[-1])
        candidates = []
        for key, entries in fantrax_lookup.items():
            key_parts = key.split()
            if key_parts and key_parts[-1] == last_name:
                for entry in entries:
                    if entry["ncaa_team"] == ncaa_team:
                        candidates.append(entry)

        if len(candidates) == 1:
            return (
                NAME_MISMATCH,
                candidates[0],
                f"Last name match: NCAA '{ncaa_name}' ~ Fantrax '{candidates[0]['name']}'",
            )

    return NOT_IN_FANTRAX, None, "Not found in Fantrax rosters or FA pool"


def validate_players(
    ncaa_players: list[dict] | None = None,
    rosters: dict | None = None,
    free_agents: list[dict] | None = None,
    team_ids: dict[str, str] | None = None,
) -> dict:
    """Validate NCAA player data against Fantrax.

    Returns a validation report with per-player results and summary.
    """
    if ncaa_players is None:
        ncaa_players = _load_json("a10_players.json")
    if rosters is None:
        rosters = _load_json("fantrax_rosters.json")
    if free_agents is None:
        free_agents = _load_json("fantrax_free_agents.json")
    if team_ids is None:
        team_ids = _load_json("a10_team_ids.json")
        if not team_ids:
            team_ids = {}

    fantrax_lookup = _build_fantrax_player_lookup(rosters, free_agents)
    a10_team_names = set(team_ids.values()) if team_ids else A10_TEAMS

    results = []
    counts = {CLEAN: 0, MISMATCH_CONFIRMED: 0, NOT_IN_FANTRAX: 0, NAME_MISMATCH: 0}

    # Check for non-A-10 teams in the dataset
    non_a10_teams = set()
    for player in ncaa_players:
        if player["team"] not in A10_TEAMS:
            non_a10_teams.add(player["team"])

    for player in ncaa_players:
        name = player.get("name", "")
        team = player.get("team", "")

        status, match, detail = _find_in_fantrax(name, team, fantrax_lookup)

        # For NOT_IN_FANTRAX, check if team is actually A-10
        if status == NOT_IN_FANTRAX and team not in A10_TEAMS:
            status = MISMATCH_CONFIRMED
            detail = f"Team '{team}' is not an A-10 school — likely data contamination"

        result = {
            "name": name,
            "ncaa_team": team,
            "status": status,
            "detail": detail,
            "games": player.get("games", 0),
        }
        if match:
            result["fantrax_name"] = match["name"]
            result["fantrax_team"] = match["fantrax_team"]
            result["fantrax_source"] = match["source"]
            if match.get("fantasy_team"):
                result["fantasy_team"] = match["fantasy_team"]

        results.append(result)
        counts[status] += 1

    report = {
        "summary": {
            "total_players": len(ncaa_players),
            "counts": counts,
            "non_a10_teams_found": sorted(non_a10_teams),
            "clean_pct": round(counts[CLEAN] / len(ncaa_players) * 100, 1) if ncaa_players else 0,
        },
        "issues": [r for r in results if r["status"] != CLEAN],
        "all_results": results,
    }

    return report


def print_validation_report(report: dict) -> None:
    """Print a human-readable validation report."""
    summary = report["summary"]
    counts = summary["counts"]

    print("\n" + "=" * 60)
    print("VALIDATION REPORT")
    print("=" * 60)
    print(f"Total players checked: {summary['total_players']}")
    print(f"  CLEAN:              {counts[CLEAN]}")
    print(f"  MISMATCH_CONFIRMED: {counts[MISMATCH_CONFIRMED]}")
    print(f"  NOT_IN_FANTRAX:     {counts[NOT_IN_FANTRAX]}")
    print(f"  NAME_MISMATCH:      {counts[NAME_MISMATCH]}")
    print(f"  Clean rate:         {summary['clean_pct']}%")

    if summary["non_a10_teams_found"]:
        print(f"\nNon-A-10 teams found in data: {summary['non_a10_teams_found']}")

    issues = report["issues"]
    if issues:
        print(f"\n--- Issues ({len(issues)}) ---")
        mismatches = [i for i in issues if i["status"] == MISMATCH_CONFIRMED]
        if mismatches:
            print(f"\nMISMATCH_CONFIRMED ({len(mismatches)}):")
            for m in mismatches:
                print(f"  {m['name']} ({m['ncaa_team']}, {m['games']}g) — {m['detail']}")

        name_mismatches = [i for i in issues if i["status"] == NAME_MISMATCH]
        if name_mismatches:
            print(f"\nNAME_MISMATCH ({len(name_mismatches)}):")
            for m in name_mismatches:
                print(f"  {m['name']} ({m['ncaa_team']}) — {m['detail']}")

        not_found = [i for i in issues if i["status"] == NOT_IN_FANTRAX]
        if not_found:
            print(f"\nNOT_IN_FANTRAX ({len(not_found)}):")
            # Only show players with meaningful minutes (5+ games)
            significant = [n for n in not_found if n.get("games", 0) >= 5]
            minor = [n for n in not_found if n.get("games", 0) < 5]
            if significant:
                print(f"  Significant (5+ games):")
                for n in significant:
                    print(f"    {n['name']} ({n['ncaa_team']}, {n['games']}g)")
            if minor:
                print(f"  Minor (<5 games): {len(minor)} players")
    else:
        print("\nNo issues found!")

    print("=" * 60)


def save_validation_report(report: dict) -> Path:
    """Save the validation report to disk."""
    DATA_DIR.mkdir(exist_ok=True)
    path = DATA_DIR / "validation_report.json"
    with open(path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    return path


def run_validation() -> dict:
    """Run full validation pipeline and print/save results."""
    report = validate_players()
    print_validation_report(report)
    path = save_validation_report(report)
    print(f"\nSaved validation report to {path}")
    return report


if __name__ == "__main__":
    run_validation()
