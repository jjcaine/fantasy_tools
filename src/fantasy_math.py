"""Shared computation logic for fantasy basketball analysis.

Provides data loaders, player matching, category math, z-scores,
weekly projections, and matchup analysis — all testable without notebooks.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent.parent / "data"

# ── Fantasy categories (order matches FanTrax) ──────────────────────────
CATEGORIES = ["AdjFG%", "3PTM", "FT%", "PTS", "REB", "AST", "ST", "BLK", "TO"]
COUNTING_CATS = ["3PTM", "PTS", "REB", "AST", "ST", "BLK"]
PCT_CATS = ["AdjFG%", "FT%"]
INVERSE_CATS = ["TO"]  # lower is better

# ── Team name mapping ───────────────────────────────────────────────────
# FanTrax full team name → NCAA normalized name
FANTRAX_TO_NCAA_TEAM: dict[str, str] = {
    "Davidson Wildcats": "Davidson",
    "Dayton Flyers": "Dayton",
    "Duquesne Dukes": "Duquesne",
    "Fordham Rams": "Fordham",
    "George Mason Patriots": "George Mason",
    "George Washington Revolutionaries": "George Washington",
    "La Salle Explorers": "La Salle",
    "Loyola (IL) Ramblers": "Loyola Chicago",
    "Rhode Island Rams": "Rhode Island",
    "Richmond Spiders": "Richmond",
    "St. Bonaventure Bonnies": "St. Bonaventure",
    "Saint Joseph's Hawks": "Saint Joseph's",
    "Saint Louis Billikens": "Saint Louis",
    "VCU Rams": "VCU",
}

# FanTrax short code → NCAA normalized name
FANTRAX_SHORT_TO_NCAA: dict[str, str] = {
    "David": "Davidson",
    "Dayt": "Dayton",
    "Duques": "Duquesne",
    "Ford": "Fordham",
    "GMas": "George Mason",
    "GrgWas": "George Washington",
    "LaSal": "La Salle",
    "LoyIL": "Loyola Chicago",
    "URI": "Rhode Island",
    "Rich": "Richmond",
    "StBon": "St. Bonaventure",
    "StJos": "Saint Joseph's",
    "StLou": "Saint Louis",
    "VCU": "VCU",
}

# Known name mismatches: (fantrax_name_lower) -> ncaa_name
MANUAL_OVERRIDES: dict[str, str] = {
    "dejour reaves": "DeJour Reaves",
    "deuce jones ii": "Deuce Jones II",
}


def normalize_fantrax_team(fantrax_team: str) -> str:
    """Convert a FanTrax team name (full or short) to NCAA normalized name."""
    if fantrax_team in FANTRAX_TO_NCAA_TEAM:
        return FANTRAX_TO_NCAA_TEAM[fantrax_team]
    if fantrax_team in FANTRAX_SHORT_TO_NCAA:
        return FANTRAX_SHORT_TO_NCAA[fantrax_team]
    return fantrax_team


# ── Data loaders ────────────────────────────────────────────────────────

def load_a10_players() -> list[dict]:
    """Load aggregated A-10 player stats from data/a10_players.json."""
    with open(DATA_DIR / "a10_players.json") as f:
        return json.load(f)


def load_fantrax_rosters() -> dict:
    """Load FanTrax rosters from data/fantrax_rosters.json."""
    with open(DATA_DIR / "fantrax_rosters.json") as f:
        return json.load(f)


def load_matchup_history() -> dict:
    """Load matchup history from data/fantrax_all_matchups.json."""
    with open(DATA_DIR / "fantrax_all_matchups.json") as f:
        return json.load(f)


def load_schedule() -> dict:
    """Load A-10 schedule from data/a10_schedule.json."""
    with open(DATA_DIR / "a10_schedule.json") as f:
        return json.load(f)


def load_free_agents() -> list[dict]:
    """Load free agents from data/fantrax_free_agents.json if it exists."""
    path = DATA_DIR / "fantrax_free_agents.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []


def load_boxscores_raw() -> list[dict]:
    """Load raw per-game box score rows from data/a10_boxscores_raw.json."""
    path = DATA_DIR / "a10_boxscores_raw.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []


# ── Player name matching ───────────────────────────────────────────────

def _normalize_name(name: str) -> str:
    """Normalize a player name for fuzzy matching.

    Lowercase, strip suffixes (Jr., Sr., II, III, IV), remove apostrophes/periods.
    """
    n = name.lower().strip()
    # Strip common suffixes (handle optional comma: "Name, Jr." or "Name Jr.")
    n = re.sub(r",?\s+(jr\.?|sr\.?|ii|iii|iv)\s*$", "", n)
    # Remove apostrophes, periods, hyphens for matching
    n = n.replace("'", "").replace(".", "").replace("-", " ")
    # Collapse whitespace
    n = re.sub(r"\s+", " ", n).strip()
    return n


def build_player_lookup(players: list[dict]) -> dict[str, list[int]]:
    """Build a normalized name → list of player indices lookup.

    Returns a dict mapping normalized names to lists of indices into the
    players list, allowing duplicate name resolution by team.
    """
    lookup: dict[str, list[int]] = {}
    for i, p in enumerate(players):
        key = _normalize_name(p["name"])
        lookup.setdefault(key, []).append(i)
    return lookup


def match_player(
    fantrax_name: str,
    fantrax_team: str,
    lookup: dict[str, list[int]],
    players: list[dict],
) -> Optional[dict]:
    """Resolve a FanTrax player to their NCAA stats entry.

    Strategy:
    1. Check MANUAL_OVERRIDES
    2. Exact normalized name match
    3. If multiple matches, filter by team
    4. Fallback: last name + team match
    """
    ncaa_team = normalize_fantrax_team(fantrax_team)

    # Check manual overrides
    override_key = fantrax_name.lower().strip()
    if override_key in MANUAL_OVERRIDES:
        override_name = MANUAL_OVERRIDES[override_key]
        norm = _normalize_name(override_name)
        if norm in lookup:
            for idx in lookup[norm]:
                if players[idx]["team"] == ncaa_team:
                    return players[idx]
            # If team doesn't match, still return first match
            return players[lookup[norm][0]]

    # Exact normalized match
    norm = _normalize_name(fantrax_name)
    if norm in lookup:
        indices = lookup[norm]
        if len(indices) == 1:
            return players[indices[0]]
        # Multiple matches — filter by team
        for idx in indices:
            if players[idx]["team"] == ncaa_team:
                return players[idx]
        # No team match, return first
        return players[indices[0]]

    # Fallback: last name + team
    last_name = fantrax_name.split()[-1].lower() if fantrax_name.split() else ""
    for p in players:
        p_last = p["name"].split()[-1].lower() if p["name"].split() else ""
        if p_last == last_name and p["team"] == ncaa_team:
            return p

    return None


# ── Fantasy category math ──────────────────────────────────────────────

def calc_adj_fg_pct(fgm: int | float, tpm: int | float, fga: int | float) -> float | None:
    """Adjusted FG%: (FGM + 0.5*3PM) / FGA."""
    if fga == 0:
        return None
    return (fgm + 0.5 * tpm) / fga


@dataclass
class PlayerCatLine:
    """Per-game category line for a player, plus raw totals for volume weighting."""
    name: str
    team: str
    games: int
    mpg: float

    # Per-game counting stats
    tpm_pg: float
    pts_pg: float
    reb_pg: float
    ast_pg: float
    stl_pg: float
    blk_pg: float
    to_pg: float

    # Percentage stats (season-level, NOT per-game averages)
    adj_fg_pct: float | None
    ft_pct: float | None

    # Raw totals for volume weighting
    fgm: int = 0
    fga: int = 0
    tpm: int = 0
    ftm: int = 0
    fta: int = 0

    # Per-game volume (for volume weighting in team projections)
    fgm_pg: float = 0.0
    fga_pg: float = 0.0
    ftm_pg: float = 0.0
    fta_pg: float = 0.0
    tpm_raw_pg: float = 0.0  # raw 3pm per game for adj fg% calc


def player_to_cat_line(p: dict) -> PlayerCatLine:
    """Convert a player stats dict to a PlayerCatLine."""
    games = p.get("games", 0) or 0
    if games == 0:
        games = 1  # avoid division by zero

    fgm = p.get("fgm", 0) or 0
    fga = p.get("fga", 0) or 0
    tpm = p.get("tpm", 0) or 0
    ftm = p.get("ftm", 0) or 0
    fta = p.get("fta", 0) or 0

    adj_fg = calc_adj_fg_pct(fgm, tpm, fga)
    ft_pct = (ftm / fta) if fta > 0 else None

    return PlayerCatLine(
        name=p.get("name", ""),
        team=p.get("team", ""),
        games=p.get("games", 0) or 0,
        mpg=p.get("mpg", 0.0) or 0.0,
        tpm_pg=p.get("tpm_pg", 0.0) or 0.0,
        pts_pg=p.get("ppg", 0.0) or 0.0,
        reb_pg=p.get("rpg", 0.0) or 0.0,
        ast_pg=p.get("apg", 0.0) or 0.0,
        stl_pg=p.get("spg", 0.0) or 0.0,
        blk_pg=p.get("bpg", 0.0) or 0.0,
        to_pg=p.get("topg", 0.0) or 0.0,
        adj_fg_pct=adj_fg,
        ft_pct=ft_pct,
        fgm=fgm,
        fga=fga,
        tpm=tpm,
        ftm=ftm,
        fta=fta,
        fgm_pg=fgm / games,
        fga_pg=fga / games,
        ftm_pg=ftm / games,
        fta_pg=fta / games,
        tpm_raw_pg=tpm / games,
    )


def _cat_value(cl: PlayerCatLine, cat: str) -> float | None:
    """Extract a single category value from a PlayerCatLine."""
    mapping = {
        "AdjFG%": cl.adj_fg_pct,
        "3PTM": cl.tpm_pg,
        "FT%": cl.ft_pct,
        "PTS": cl.pts_pg,
        "REB": cl.reb_pg,
        "AST": cl.ast_pg,
        "ST": cl.stl_pg,
        "BLK": cl.blk_pg,
        "TO": cl.to_pg,
    }
    return mapping.get(cat)


def compute_z_scores(
    players: list[dict],
    min_games: int = 5,
    min_mpg: float = 10.0,
) -> list[dict]:
    """Compute z-scores across all 9 fantasy categories.

    Returns a list of dicts with player info + z-score per category.
    Population = qualified players (games >= min_games, mpg >= min_mpg).
    Pct cats require minimum volume: 2+ FGA/g for AdjFG%, 1+ FTA/g for FT%.
    TO is inverted (lower = better → higher z-score).
    """
    # Filter qualified players
    qualified = []
    for p in players:
        games = p.get("games", 0) or 0
        mpg = p.get("mpg", 0.0) or 0.0
        if games >= min_games and mpg >= min_mpg:
            qualified.append(p)

    if not qualified:
        return []

    cat_lines = [player_to_cat_line(p) for p in qualified]

    # Compute mean/std for each category
    stats: dict[str, dict] = {}
    for cat in CATEGORIES:
        values = []
        for cl in cat_lines:
            val = _cat_value(cl, cat)
            if val is None:
                continue
            # Volume filters for pct cats
            if cat == "AdjFG%" and cl.fga_pg < 2.0:
                continue
            if cat == "FT%" and cl.fta_pg < 1.0:
                continue
            values.append(val)

        if not values:
            stats[cat] = {"mean": 0, "std": 1}
            continue

        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = variance ** 0.5 if variance > 0 else 1.0
        stats[cat] = {"mean": mean, "std": std, "n": len(values)}

    # Compute z-scores for each player
    results = []
    for p, cl in zip(qualified, cat_lines):
        z_scores: dict[str, float | None] = {}
        for cat in CATEGORIES:
            val = _cat_value(cl, cat)
            if val is None:
                z_scores[cat] = None
                continue
            # Volume check
            if cat == "AdjFG%" and cl.fga_pg < 2.0:
                z_scores[cat] = None
                continue
            if cat == "FT%" and cl.fta_pg < 1.0:
                z_scores[cat] = None
                continue

            z = (val - stats[cat]["mean"]) / stats[cat]["std"]
            # Invert TO (lower is better)
            if cat in INVERSE_CATS:
                z = -z
            z_scores[cat] = round(z, 2)

        results.append({
            "name": p["name"],
            "team": p["team"],
            "games": p.get("games", 0),
            "mpg": p.get("mpg", 0.0),
            "cat_line": cl,
            "z_scores": z_scores,
        })

    return results


def composite_z_score(
    z_scores: dict[str, float | None],
    weights: dict[str, float] | None = None,
) -> float:
    """Sum of z-scores, optionally weighted for punt strategies.

    None values (unqualified pct cats) are treated as 0.
    """
    total = 0.0
    for cat in CATEGORIES:
        z = z_scores.get(cat)
        if z is None:
            continue
        w = weights.get(cat, 1.0) if weights else 1.0
        total += z * w
    return round(total, 2)


def schedule_adjusted_composite(
    z_scores: dict[str, float | None],
    team_games: int,
    baseline_games: float = 2.0,
    weights: dict[str, float] | None = None,
) -> float:
    """Composite z-score with counting cats scaled by schedule.

    Counting cat z-scores × (team_games / baseline).
    Pct cats and TO are unscaled (they don't benefit from more games).
    """
    multiplier = team_games / baseline_games if baseline_games > 0 else 1.0
    total = 0.0
    for cat in CATEGORIES:
        z = z_scores.get(cat)
        if z is None:
            continue
        w = weights.get(cat, 1.0) if weights else 1.0
        if cat in COUNTING_CATS:
            total += z * w * multiplier
        else:
            total += z * w
    return round(total, 2)


# ── Weekly projections ──────────────────────────────────────────────────

@dataclass
class TeamProjection:
    """Projected category totals for a team in a scoring period."""
    team_name: str
    period: int | str
    cats: dict[str, float] = field(default_factory=dict)
    player_lines: list[PlayerCatLine] = field(default_factory=list)
    games_per_player: dict[str, int] = field(default_factory=dict)


def project_team_week(
    roster_cat_lines: list[PlayerCatLine],
    games_per_player: dict[str, int],
    period: int | str = 0,
    team_name: str = "",
) -> TeamProjection:
    """Project team category totals for a scoring period.

    Counting cats: per_game_stat × player_games, summed across roster.
    Pct cats: volume-weighted — sum(makes×games) / sum(attempts×games).
    TO: sum of topg × games.
    """
    proj = TeamProjection(team_name=team_name, period=period)
    proj.player_lines = roster_cat_lines
    proj.games_per_player = games_per_player

    total_tpm = 0.0
    total_pts = 0.0
    total_reb = 0.0
    total_ast = 0.0
    total_stl = 0.0
    total_blk = 0.0
    total_to = 0.0

    # Volume accumulators for pct cats
    total_fgm_adj = 0.0  # FGM + 0.5*3PM
    total_fga = 0.0
    total_ftm = 0.0
    total_fta = 0.0

    for cl in roster_cat_lines:
        g = games_per_player.get(cl.name, 0)
        if g == 0:
            continue

        total_tpm += cl.tpm_pg * g
        total_pts += cl.pts_pg * g
        total_reb += cl.reb_pg * g
        total_ast += cl.ast_pg * g
        total_stl += cl.stl_pg * g
        total_blk += cl.blk_pg * g
        total_to += cl.to_pg * g

        # Volume for pct cats
        total_fgm_adj += (cl.fgm_pg + 0.5 * cl.tpm_raw_pg) * g
        total_fga += cl.fga_pg * g
        total_ftm += cl.ftm_pg * g
        total_fta += cl.fta_pg * g

    proj.cats = {
        "AdjFG%": round(total_fgm_adj / total_fga, 4) if total_fga > 0 else 0.0,
        "3PTM": round(total_tpm, 1),
        "FT%": round(total_ftm / total_fta, 4) if total_fta > 0 else 0.0,
        "PTS": round(total_pts, 1),
        "REB": round(total_reb, 1),
        "AST": round(total_ast, 1),
        "ST": round(total_stl, 1),
        "BLK": round(total_blk, 1),
        "TO": round(total_to, 1),
    }

    return proj


# ── Matchup analysis ───────────────────────────────────────────────────

@dataclass
class CatComparison:
    """Single category comparison between two teams."""
    category: str
    team_a_val: float
    team_b_val: float
    winner: str  # "A", "B", or "T" (tie)
    margin: float


@dataclass
class MatchupResult:
    """Full matchup projection between two teams."""
    team_a: str
    team_b: str
    comparisons: list[CatComparison]
    wins_a: int = 0
    wins_b: int = 0
    ties: int = 0

    @property
    def result_str(self) -> str:
        return f"{self.wins_a}-{self.wins_b}-{self.ties}"


def compare_categories(
    team_a_proj: TeamProjection,
    team_b_proj: TeamProjection,
) -> MatchupResult:
    """Category-by-category comparison with winner + margin."""
    comps = []
    wins_a = wins_b = ties = 0

    for cat in CATEGORIES:
        a_val = team_a_proj.cats.get(cat, 0.0)
        b_val = team_b_proj.cats.get(cat, 0.0)

        # TO is inverse — lower wins
        if cat in INVERSE_CATS:
            if a_val < b_val:
                winner = "A"
                wins_a += 1
            elif b_val < a_val:
                winner = "B"
                wins_b += 1
            else:
                winner = "T"
                ties += 1
            margin = abs(a_val - b_val)
        else:
            if a_val > b_val:
                winner = "A"
                wins_a += 1
            elif b_val > a_val:
                winner = "B"
                wins_b += 1
            else:
                winner = "T"
                ties += 1
            margin = abs(a_val - b_val)

        comps.append(CatComparison(
            category=cat,
            team_a_val=a_val,
            team_b_val=b_val,
            winner=winner,
            margin=round(margin, 4),
        ))

    return MatchupResult(
        team_a=team_a_proj.team_name,
        team_b=team_b_proj.team_name,
        comparisons=comps,
        wins_a=wins_a,
        wins_b=wins_b,
        ties=ties,
    )


def predict_matchup(
    team_a_proj: TeamProjection,
    team_b_proj: TeamProjection,
) -> MatchupResult:
    """Projected W-L-T result with cats sorted by margin."""
    result = compare_categories(team_a_proj, team_b_proj)
    # Sort comparisons by margin descending (biggest advantages first)
    result.comparisons.sort(key=lambda c: c.margin, reverse=True)
    return result


# ── Historical analysis ─────────────────────────────────────────────────

def team_historical_cats(
    matchup_history: dict,
    team_name: str,
) -> list[dict]:
    """Extract a team's category values across all periods.

    Returns list of {period, cat_values} dicts sorted by period.
    """
    results = []
    for period_str, period_data in matchup_history.items():
        rows = period_data.get("rows", [])
        for row in rows:
            if row.get("team_name") == team_name:
                cats = {}
                for cat in CATEGORIES:
                    val_str = row.get(cat, "")
                    try:
                        cats[cat] = float(val_str)
                    except (ValueError, TypeError):
                        cats[cat] = None
                # Also grab W/L/T
                results.append({
                    "period": int(period_str),
                    "cats": cats,
                    "W": int(row.get("W", 0)),
                    "L": int(row.get("L", 0)),
                    "T": int(row.get("T", 0)),
                })
                break

    results.sort(key=lambda r: r["period"])
    return results


def team_category_ranks(
    matchup_history: dict,
    period: int | str | None = None,
) -> dict[str, dict[str, int]]:
    """Rank all 8 teams per category for a given period (or latest).

    Returns {team_name: {cat: rank}} where rank 1 = best.
    For TO, rank 1 = lowest (fewest turnovers).
    """
    if period is not None:
        period_key = str(period)
        if period_key not in matchup_history:
            return {}
        periods_to_use = [period_key]
    else:
        # Use the latest period
        period_keys = sorted(matchup_history.keys(), key=lambda k: int(k))
        if not period_keys:
            return {}
        periods_to_use = [period_keys[-1]]

    period_key = periods_to_use[0]
    rows = matchup_history[period_key].get("rows", [])

    # Extract values
    team_vals: dict[str, dict[str, float]] = {}
    for row in rows:
        name = row.get("team_name", "")
        if not name:
            continue
        cats = {}
        for cat in CATEGORIES:
            try:
                cats[cat] = float(row.get(cat, 0))
            except (ValueError, TypeError):
                cats[cat] = 0.0
        team_vals[name] = cats

    # Rank per category
    ranks: dict[str, dict[str, int]] = {t: {} for t in team_vals}
    for cat in CATEGORIES:
        reverse = cat not in INVERSE_CATS  # higher is better except TO
        sorted_teams = sorted(
            team_vals.keys(),
            key=lambda t: team_vals[t].get(cat, 0),
            reverse=reverse,
        )
        for rank, team in enumerate(sorted_teams, 1):
            ranks[team][cat] = rank

    return ranks


# ── Roster building helpers ─────────────────────────────────────────────

def build_team_roster_lines(
    fantasy_team_name: str,
    rosters: dict,
    players: list[dict],
    lookup: dict[str, list[int]],
) -> tuple[list[PlayerCatLine], list[dict], list[dict]]:
    """Build PlayerCatLines for a fantasy team's roster.

    Returns (matched_lines, matched_info, unmatched_players).
    matched_info has fantrax player dict + matched ncaa dict for verification.
    """
    team_roster = rosters.get(fantasy_team_name, {})
    roster_players = team_roster.get("players", [])

    matched_lines = []
    matched_info = []
    unmatched = []

    for fp in roster_players:
        ncaa = match_player(fp["name"], fp.get("team", ""), lookup, players)
        if ncaa:
            cl = player_to_cat_line(ncaa)
            matched_lines.append(cl)
            matched_info.append({"fantrax": fp, "ncaa": ncaa})
        else:
            unmatched.append(fp)

    return matched_lines, matched_info, unmatched


def get_player_games_in_period(
    roster_cat_lines: list[PlayerCatLine],
    schedule: dict,
    period: int | str,
) -> dict[str, int]:
    """Get number of games each rostered player's team has in a period."""
    period_key = str(period)
    period_data = schedule.get(period_key, {})
    games_per_team = period_data.get("games_per_team", {})

    result = {}
    for cl in roster_cat_lines:
        team_games = games_per_team.get(cl.team, 0)
        result[cl.name] = team_games

    return result


def get_all_team_projections(
    rosters: dict,
    players: list[dict],
    schedule: dict,
    period: int | str,
) -> dict[str, TeamProjection]:
    """Build projections for all 8 fantasy teams for a given period."""
    lookup = build_player_lookup(players)
    projections = {}

    for team_name in rosters:
        lines, _, _ = build_team_roster_lines(team_name, rosters, players, lookup)
        games = get_player_games_in_period(lines, schedule, period)
        proj = project_team_week(lines, games, period=period, team_name=team_name)
        projections[team_name] = proj

    return projections


# ── Data quality ────────────────────────────────────────────────────────

@dataclass
class DataQualityReport:
    """Summary of data quality checks."""
    checks: list[dict] = field(default_factory=list)

    def add(self, name: str, passed: bool, detail: str = ""):
        self.checks.append({"name": name, "passed": passed, "detail": detail})

    @property
    def all_passed(self) -> bool:
        return all(c["passed"] for c in self.checks)

    @property
    def summary(self) -> str:
        passed = sum(1 for c in self.checks if c["passed"])
        total = len(self.checks)
        return f"{passed}/{total} checks passed"


def run_player_data_quality(players: list[dict]) -> DataQualityReport:
    """Run data quality checks on player stats."""
    report = DataQualityReport()

    # Check 1: Minimum player count
    report.add(
        "Player count >= 200",
        len(players) >= 200,
        f"{len(players)} players loaded",
    )

    # Check 2: All 14 A-10 teams represented
    teams = set(p["team"] for p in players)
    expected_teams = {
        "Davidson", "Dayton", "Duquesne", "Fordham", "George Mason",
        "George Washington", "La Salle", "Loyola Chicago", "Rhode Island",
        "Richmond", "Saint Joseph's", "Saint Louis", "St. Bonaventure", "VCU",
    }
    missing = expected_teams - teams
    report.add(
        "All 14 A-10 teams present",
        len(missing) == 0,
        f"Missing: {missing}" if missing else "All teams present",
    )

    # Check 3: No negative stat values
    stat_fields = ["fgm", "fga", "ftm", "fta", "tpm", "reb", "ast", "stl", "blk", "to", "pts"]
    neg_count = 0
    for p in players:
        for f in stat_fields:
            if (p.get(f) or 0) < 0:
                neg_count += 1
    report.add(
        "No negative stat values",
        neg_count == 0,
        f"{neg_count} negative values found" if neg_count else "Clean",
    )

    # Check 4: FGM <= FGA for all players
    violations = [p["name"] for p in players if (p.get("fgm", 0) or 0) > (p.get("fga", 0) or 0)]
    report.add(
        "FGM <= FGA for all players",
        len(violations) == 0,
        f"Violations: {violations}" if violations else "Clean",
    )

    # Check 5: FTM <= FTA
    violations = [p["name"] for p in players if (p.get("ftm", 0) or 0) > (p.get("fta", 0) or 0)]
    report.add(
        "FTM <= FTA for all players",
        len(violations) == 0,
        f"Violations: {violations}" if violations else "Clean",
    )

    # Check 6: 3PM <= FGM (3-pointers are a subset of field goals)
    violations = [p["name"] for p in players if (p.get("tpm", 0) or 0) > (p.get("fgm", 0) or 0)]
    report.add(
        "3PM <= FGM for all players",
        len(violations) == 0,
        f"Violations: {violations}" if violations else "Clean",
    )

    # Check 7: PTS = 2*(FGM-3PM) + 3*3PM + FTM
    pts_mismatches = []
    for p in players:
        fgm = p.get("fgm", 0) or 0
        tpm = p.get("tpm", 0) or 0
        ftm = p.get("ftm", 0) or 0
        pts = p.get("pts", 0) or 0
        expected_pts = 2 * (fgm - tpm) + 3 * tpm + ftm
        if pts != expected_pts:
            pts_mismatches.append({
                "name": p["name"],
                "team": p["team"],
                "actual": pts,
                "expected": expected_pts,
                "diff": pts - expected_pts,
            })
    report.add(
        "PTS = 2*(FGM-3PM) + 3*3PM + FTM",
        len(pts_mismatches) == 0,
        f"{len(pts_mismatches)} mismatches" if pts_mismatches else "Clean",
    )

    # Check 8: Reasonable MPG range (0-45)
    high_mpg = [p["name"] for p in players if (p.get("mpg", 0) or 0) > 45]
    report.add(
        "MPG <= 45 for all players",
        len(high_mpg) == 0,
        f"High MPG: {high_mpg}" if high_mpg else "Clean",
    )

    # Check 9: At least 5 players per team with 5+ games
    for team in sorted(expected_teams):
        team_qual = [p for p in players if p["team"] == team and (p.get("games", 0) or 0) >= 5]
        report.add(
            f"{team}: 5+ qualified players",
            len(team_qual) >= 5,
            f"{len(team_qual)} players with 5+ games",
        )

    return report


def run_roster_match_quality(
    rosters: dict,
    players: list[dict],
    lookup: dict[str, list[int]],
) -> DataQualityReport:
    """Check how well FanTrax rosters match to NCAA stats."""
    report = DataQualityReport()

    total_players = 0
    total_matched = 0
    unmatched_all = []

    for team_name, team_data in rosters.items():
        roster_players = team_data.get("players", [])
        matched = 0
        unmatched = []
        for fp in roster_players:
            ncaa = match_player(fp["name"], fp.get("team", ""), lookup, players)
            if ncaa:
                matched += 1
            else:
                unmatched.append(f"{fp['name']} ({fp.get('team', 'N/A')})")
        total_players += len(roster_players)
        total_matched += matched
        unmatched_all.extend(unmatched)

        report.add(
            f"{team_name}: roster match",
            matched == len(roster_players),
            f"{matched}/{len(roster_players)} matched"
            + (f" | Unmatched: {', '.join(unmatched)}" if unmatched else ""),
        )

    match_rate = total_matched / total_players if total_players > 0 else 0
    report.add(
        "Overall match rate >= 90%",
        match_rate >= 0.9,
        f"{total_matched}/{total_players} ({match_rate:.1%})",
    )

    return report


def run_matchup_data_quality(matchup_history: dict) -> DataQualityReport:
    """Check matchup history data quality."""
    report = DataQualityReport()

    # Check period count
    report.add(
        "At least 10 periods of history",
        len(matchup_history) >= 10,
        f"{len(matchup_history)} periods found",
    )

    # Check each period has 8 teams
    for period_str, data in sorted(matchup_history.items(), key=lambda x: int(x[0])):
        rows = data.get("rows", [])
        report.add(
            f"Period {period_str}: 8 teams",
            len(rows) == 8,
            f"{len(rows)} teams",
        )

    # Check W+L = 9 for each team (9 H2H categories)
    bad_wl = []
    for period_str, data in matchup_history.items():
        for row in data.get("rows", []):
            w = int(row.get("W", 0))
            l = int(row.get("L", 0))
            t = int(row.get("T", 0))
            if w + l + t != 9:
                bad_wl.append(f"P{period_str} {row.get('team_name')}: {w}W-{l}L-{t}T")
    report.add(
        "W+L+T = 9 for all teams/periods",
        len(bad_wl) == 0,
        f"Violations: {bad_wl[:5]}" if bad_wl else "Clean",
    )

    return report


def run_schedule_data_quality(schedule: dict) -> DataQualityReport:
    """Check schedule data quality."""
    report = DataQualityReport()

    for period_str in ["14", "15", "16", "17"]:
        present = period_str in schedule
        report.add(
            f"Period {period_str} present",
            present,
            "Found" if present else "Missing",
        )
        if present:
            gpt = schedule[period_str].get("games_per_team", {})
            a10_teams_in_sched = [t for t in gpt if t in {
                "Davidson", "Dayton", "Duquesne", "Fordham", "George Mason",
                "George Washington", "La Salle", "Loyola Chicago", "Rhode Island",
                "Richmond", "Saint Joseph's", "Saint Louis", "St. Bonaventure", "VCU",
            }]
            report.add(
                f"Period {period_str}: 14 A-10 teams scheduled",
                len(a10_teams_in_sched) >= 12,  # some periods may have bye weeks
                f"{len(a10_teams_in_sched)} A-10 teams have games",
            )

    return report
