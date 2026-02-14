"""Authenticated FanTrax API client using fantraxapi library with Selenium login."""

import os
import pickle
import time
from pathlib import Path

import requests as req
from dotenv import load_dotenv
from requests import Session
from selenium import webdriver
from selenium.webdriver import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from fantraxapi import League, NotLoggedIn, api
from fantraxapi.api import Method

load_dotenv()

LEAGUE_ID = "l6r9clmimgohg3yp"
COOKIE_PATH = Path(__file__).parent.parent / "data" / "fantrax_cookies.pkl"


def _add_cookie_to_session(session: Session, ignore_cookie: bool = False) -> None:
    """Log in via Selenium and store cookies, or load cached cookies."""
    if not ignore_cookie and COOKIE_PATH.exists():
        with open(COOKIE_PATH, "rb") as f:
            for cookie in pickle.load(f):
                session.cookies.set(cookie["name"], cookie["value"])
        return

    username = os.environ["FANTRAX_USERNAME"]
    password = os.environ["FANTRAX_PASSWORD"]

    service = Service(ChromeDriverManager().install())
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1600")

    with webdriver.Chrome(service=service, options=options) as driver:
        driver.get("https://www.fantrax.com/login")
        username_box = WebDriverWait(driver, 15).until(
            expected_conditions.presence_of_element_located(
                (By.XPATH, "//input[@formcontrolname='email']")
            )
        )
        username_box.send_keys(username)
        password_box = WebDriverWait(driver, 15).until(
            expected_conditions.presence_of_element_located(
                (By.XPATH, "//input[@formcontrolname='password']")
            )
        )
        password_box.send_keys(password)
        password_box.send_keys(Keys.ENTER)
        time.sleep(5)

        cookies = driver.get_cookies()
        COOKIE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(COOKIE_PATH, "wb") as f:
            pickle.dump(cookies, f)

        for cookie in cookies:
            session.cookies.set(cookie["name"], cookie["value"])


# Monkey-patch the fantraxapi request function to handle auth
_old_request = api.request


def _authed_request(league: "League", methods: list[Method] | Method) -> dict:
    try:
        if not league.logged_in:
            _add_cookie_to_session(league.session)
        return _old_request(league, methods)
    except NotLoggedIn:
        _add_cookie_to_session(league.session, ignore_cookie=True)
        return _authed_request(league, methods)


api.request = _authed_request


def get_league() -> League:
    """Get an authenticated League instance."""
    return League(LEAGUE_ID)


def get_standings(league: League) -> dict:
    """Get current league standings with records."""
    standings = league.standings()
    results = {}
    for rank, record in standings.ranks.items():
        results[rank] = {
            "rank": record.rank,
            "team_name": record.team.name,
            "team_id": record.team.id if hasattr(record.team, "id") else None,
            "wins": record.win,
            "losses": record.loss,
            "ties": record.tie,
            "points_for": record.points_for,
            "points_against": record.points_against,
            "waiver_order": record.wavier_wire_order,
            "streak": record.streak,
        }
    return results


def get_all_rosters(league: League) -> dict:
    """Get rosters for all teams. Returns {team_name: [player_dicts]}."""
    rosters = {}
    for team in league.teams:
        roster = team.roster()
        players = []
        for row in roster.rows:
            if row.player:
                players.append({
                    "name": row.player.name,
                    "player_id": row.player.id,
                    "team": row.player.team_name,
                    "team_short": row.player.team_short_name,
                    "position": row.position.short_name if row.position else None,
                    "positions": [p.short_name for p in row.player.all_positions] if row.player.all_positions else [],
                    "total_fpts": row.total_fantasy_points,
                    "fpts_per_game": row.fantasy_points_per_game,
                    "injured": row.player.injured,
                    "day_to_day": row.player.day_to_day,
                    "out": row.player.out,
                })
        rosters[team.name] = {
            "team_id": team.id if hasattr(team, "id") else None,
            "players": players,
            "active": roster.active,
            "active_max": roster.active_max,
            "reserve": roster.reserve,
            "reserve_max": roster.reserve_max,
        }
    return rosters


def get_matchup_history_raw(league: League) -> dict:
    """Get all scoring period matchup data using raw API (works for H2H categories)."""
    raw = api.get_standings(league, views="H2H_MATCHUPS")

    team_info = raw.get("fantasyTeamInfo", {})
    tables = raw.get("tableList", [])

    # Table 0 = Standings, Tables 1+ = Scoring periods (most recent first)
    period_tables = tables[1:] if len(tables) > 1 else []

    CATEGORY_KEYS = ["AdjFG%", "3PTM", "FT%", "PTS", "REB", "AST", "ST", "BLK", "TO"]

    results = {}
    for table in period_tables:
        caption = table.get("caption", "")
        # Extract period number from "Scoring Period:  14"
        period_num = None
        if "Scoring Period" in caption:
            try:
                period_num = int(caption.split(":")[-1].strip())
            except ValueError:
                continue

        header_cells = table.get("header", {}).get("cells", [])
        col_names = [c.get("shortName", c.get("name", "")) for c in header_cells]

        matchup_rows = []
        for row in table.get("rows", []):
            fixed = row.get("fixedCells", [])
            team_name = fixed[0].get("content", "") if fixed else ""
            team_id = fixed[0].get("teamId", "") if fixed else ""

            cells = row.get("cells", [])
            vals = {col_names[i]: cells[i].get("content", "") for i in range(len(cells)) if i < len(col_names)}

            matchup_rows.append({
                "team_name": team_name,
                "team_id": team_id,
                **vals,
            })

        results[period_num] = {
            "caption": caption,
            "columns": col_names,
            "rows": matchup_rows,
        }

    return {"team_info": team_info, "periods": results}


def get_transactions(league: League, count: int = 200) -> list[dict]:
    """Get recent transaction history."""
    txns = league.transactions(count=count)
    results = []
    for t in txns:
        players = []
        for p in t.players:
            players.append({
                "name": p.name,
                "type": p.type,
                "team": p.team_name,
            })
        results.append({
            "team": t.team.name,
            "date": str(t.date),
            "players": players,
        })
    return results


# --- Public API (fxea) endpoints - no auth needed ---

FXEA_BASE = "https://www.fantrax.com/fxea/general"


def get_league_info() -> dict:
    """Get league info from public API including all player statuses (FA/WW/T)."""
    resp = req.get(f"{FXEA_BASE}/getLeagueInfo", params={"leagueId": LEAGUE_ID}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_player_ids(sport: str = "NCAAB") -> dict:
    """Get player ID to name/team/position mapping from public API."""
    resp = req.get(f"{FXEA_BASE}/getPlayerIds", params={"sport": sport}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_free_agents() -> list[dict]:
    """Get all free agents and waiver wire players with names and details.

    Combines the league info (player statuses) with the player ID mapping
    to produce a list of available players.
    """
    league_info = get_league_info()
    player_ids = get_player_ids()
    player_statuses = league_info.get("playerInfo", {})
    team_info = league_info.get("teamInfo", {})

    # Build reverse map: player_id -> fantasy_team_name
    rostered_by = {}
    for team_id, tinfo in team_info.items():
        team_name = tinfo.get("name", team_id)
        for pid in tinfo.get("rosterItems", []):
            rostered_by[pid] = team_name

    free_agents = []
    for pid, status_info in player_statuses.items():
        status = status_info.get("status", "")
        if status not in ("FA", "WW"):
            continue

        player_data = player_ids.get(pid, {})
        if not player_data or not player_data.get("name"):
            continue

        name_raw = player_data.get("name", "")
        # Names are "Last, First" format
        parts = name_raw.split(", ")
        name = f"{parts[1]} {parts[0]}" if len(parts) == 2 else name_raw

        free_agents.append({
            "player_id": pid,
            "name": name,
            "name_raw": name_raw,
            "team": player_data.get("team", ""),
            "position": player_data.get("position", ""),
            "status": status,  # FA or WW
        })

    return free_agents


def get_matchup_period_data(league: League, period_num: int) -> dict:
    """Get category-level matchup data for a specific scoring period."""
    raw = api.request(league, Method(
        "getStandings", view="H2H_MATCHUPS",
        period=period_num, timeStartType="PERIOD_ONLY", timeframeType="BY_PERIOD",
    ))
    tables = raw.get("tableList", [])

    for t in tables:
        if "Scoring Period" in t.get("caption", ""):
            header_cells = t.get("header", {}).get("cells", [])
            col_names = [c.get("shortName", c.get("name", "")) for c in header_cells]
            rows = []
            for row in t.get("rows", []):
                fixed = row.get("fixedCells", [])
                team_name = fixed[0].get("content", "") if fixed else ""
                team_id = fixed[0].get("teamId", "") if fixed else ""
                cells = row.get("cells", [])
                vals = {col_names[i]: cells[i].get("content", "") for i in range(min(len(cells), len(col_names)))}
                rows.append({"team_name": team_name, "team_id": team_id, **vals})
            return {"period": period_num, "columns": col_names, "rows": rows}

    return {"period": period_num, "columns": [], "rows": []}
