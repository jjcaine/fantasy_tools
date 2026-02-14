import marimo

__generated_with = "0.19.11"
app = marimo.App(width="full", app_title="Roster Analyzer — Sick-Os Revenge")


@app.cell
def imports():
    import marimo as mo
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent))

    from src.fantasy_math import (
        CATEGORIES,
        COUNTING_CATS,
        load_a10_players,
        load_fantrax_rosters,
        load_matchup_history,
        load_schedule,
        build_player_lookup,
        build_team_roster_lines,
        get_player_games_in_period,
        get_all_team_projections,
        project_team_week,
        player_to_cat_line,
        compute_z_scores,
        composite_z_score,
        team_historical_cats,
        team_category_ranks,
        run_player_data_quality,
        run_roster_match_quality,
        run_matchup_data_quality,
        run_schedule_data_quality,
    )

    MY_TEAM = "Sick-Os Revenge"

    players = load_a10_players()
    rosters = load_fantrax_rosters()
    matchups = load_matchup_history()
    schedule = load_schedule()
    lookup = build_player_lookup(players)

    mo.md(f"# Roster Analyzer — {MY_TEAM}")
    return (
        CATEGORIES, MY_TEAM, build_team_roster_lines,
        get_all_team_projections, get_player_games_in_period, lookup,
        matchups, mo, players, project_team_week, rosters,
        run_matchup_data_quality, run_player_data_quality,
        run_roster_match_quality, run_schedule_data_quality,
        schedule, team_historical_cats,
    )


@app.cell
def data_quality(mo, players, rosters, matchups, schedule, lookup,
                 run_player_data_quality, run_roster_match_quality,
                 run_matchup_data_quality, run_schedule_data_quality):
    _reports = {
        "Player Data": run_player_data_quality(players),
        "Roster Matching": run_roster_match_quality(rosters, players, lookup),
        "Matchup History": run_matchup_data_quality(matchups),
        "Schedule": run_schedule_data_quality(schedule),
    }

    _sections = []
    for _title, _report in _reports.items():
        _failed = [_c for _c in _report.checks if not _c["passed"]]
        _icon = "✅" if _report.all_passed else f"⚠️ ({len(_failed)} issues)"
        _detail_rows = []
        for _c in _report.checks:
            _status = "✅" if _c["passed"] else "❌"
            _detail_rows.append(f"| {_status} | {_c['name']} | {_c['detail']} |")
        _table = "| | Check | Detail |\n|--|-------|--------|\n" + "\n".join(_detail_rows)
        _sections.append(f"### {_title} {_icon}\n\n{_table}")

    mo.md("## Data Quality\n\n" + "\n\n".join(_sections))


@app.cell
def roster_match(mo, MY_TEAM, rosters, players, lookup, build_team_roster_lines):
    lines, matched_info, unmatched = build_team_roster_lines(
        MY_TEAM, rosters, players, lookup
    )

    _unmatched_md = ""
    if unmatched:
        _unmatched_names = ", ".join(f"**{_u['name']}** ({_u.get('team', '?')})" for _u in unmatched)
        _unmatched_md = f"\n\n⚠️ **Unmatched players:** {_unmatched_names}"

    mo.md(f"## Our Roster — {len(matched_info)}/{len(matched_info) + len(unmatched)} matched{_unmatched_md}")
    return lines, matched_info, unmatched


@app.cell
def roster_table(mo, matched_info):
    mo.ui.table(
        [
            {
                "FanTrax": _m["fantrax"]["name"],
                "NCAA": _m["ncaa"]["name"],
                "Team": _m["ncaa"]["team"],
                "GP": _m["ncaa"]["games"],
                "PPG": _m["ncaa"]["ppg"],
                "RPG": _m["ncaa"]["rpg"],
                "APG": _m["ncaa"]["apg"],
                "SPG": _m["ncaa"]["spg"],
                "BPG": _m["ncaa"]["bpg"],
                "3PM/G": _m["ncaa"]["tpm_pg"],
                "TOPG": _m["ncaa"]["topg"],
                "MPG": _m["ncaa"]["mpg"],
            }
            for _m in matched_info
        ],
        selection=None,
    )


@app.cell
def period_control(mo, schedule):
    _period_options = {f"Period {_p}": str(_p) for _p in sorted(schedule.keys(), key=lambda x: int(x))}
    period_sel = mo.ui.dropdown(options=_period_options, value="Period 15", label="Period")
    mo.hstack([period_sel])
    return (period_sel,)


@app.cell
def player_breakdown(mo, CATEGORIES, lines, schedule, period_sel,
                     get_player_games_in_period, project_team_week, MY_TEAM):
    _period_key = period_sel.value
    games = get_player_games_in_period(lines, schedule, int(_period_key))

    _rows = []
    for _cl in lines:
        _g = games.get(_cl.name, 0)
        _rows.append({
            "Player": _cl.name,
            "Team": _cl.team,
            f"Games (P{_period_key})": _g,
            "PPG": _cl.pts_pg,
            f"Proj PTS": round(_cl.pts_pg * _g, 1),
            "RPG": _cl.reb_pg,
            f"Proj REB": round(_cl.reb_pg * _g, 1),
            "APG": _cl.ast_pg,
            f"Proj AST": round(_cl.ast_pg * _g, 1),
            "3PM/G": _cl.tpm_pg,
            f"Proj 3PM": round(_cl.tpm_pg * _g, 1),
            "SPG": _cl.stl_pg,
            "BPG": _cl.blk_pg,
            "TOPG": _cl.to_pg,
        })

    our_proj = project_team_week(lines, games, period=_period_key, team_name=MY_TEAM)

    mo.md(f"### Per-Player Breakdown — Period {_period_key}")
    mo.ui.table(_rows, selection=None)
    return games, our_proj


@app.cell
def team_vs_league(
    mo, CATEGORIES, MY_TEAM, rosters, players, schedule, period_sel,
    get_all_team_projections, our_proj
):
    _period_key = period_sel.value
    all_projs = get_all_team_projections(rosters, players, schedule, int(_period_key))

    rank_rows = []
    for _cat in CATEGORIES:
        _vals = [(_t, _p.cats.get(_cat, 0)) for _t, _p in all_projs.items()]
        if _cat == "TO":
            _vals.sort(key=lambda x: x[1])
        else:
            _vals.sort(key=lambda x: x[1], reverse=True)

        _our_rank = next((_i + 1 for _i, (_t, _) in enumerate(_vals) if _t == MY_TEAM), "?")
        _our_val = our_proj.cats.get(_cat, 0)
        _league_avg = sum(_v for _, _v in _vals) / len(_vals) if _vals else 0

        _label = ""
        if isinstance(_our_rank, int):
            if _our_rank <= 3:
                _label = "💪 Strength"
            elif _our_rank >= 6:
                _label = "📉 Weakness"

        rank_rows.append({
            "Category": _cat,
            "Our Proj": round(_our_val, 3) if _cat in ("AdjFG%", "FT%") else round(_our_val, 1),
            "League Avg": round(_league_avg, 3) if _cat in ("AdjFG%", "FT%") else round(_league_avg, 1),
            "Rank (of 8)": _our_rank,
            "Assessment": _label,
        })

    mo.md(f"### Team Projected Totals vs League — Period {_period_key}")
    mo.ui.table(rank_rows, selection=None)
    return all_projs, rank_rows


@app.cell
def historical(mo, matchups, MY_TEAM, CATEGORIES, team_historical_cats):
    _hist = team_historical_cats(matchups, MY_TEAM)

    _trend_rows = []
    if _hist:
        for _h in _hist:
            _row = {"Period": _h["period"], "Record": f"{_h['W']}-{_h['L']}-{_h['T']}"}
            for _cat in CATEGORIES:
                _row[_cat] = _h["cats"].get(_cat, "")
            _trend_rows.append(_row)
        mo.md(f"### Historical Performance — Periods 1-{_hist[-1]['period']}")
        mo.ui.table(_trend_rows, selection=None)
    else:
        mo.md("_No historical data found._")


@app.cell
def cat_targeting(mo, CATEGORIES, rank_rows):
    _strengths = [_r for _r in rank_rows if "Strength" in _r.get("Assessment", "")]
    _weaknesses = [_r for _r in rank_rows if "Weakness" in _r.get("Assessment", "")]
    _middle = [_r for _r in rank_rows if _r.get("Assessment", "") == ""]

    _target_cats = [_r["Category"] for _r in _strengths]
    _middle_sorted = sorted(_middle, key=lambda _x: _x["Rank (of 8)"])
    _target_cats += [_r["Category"] for _r in _middle_sorted[:max(0, 5 - len(_target_cats))]]

    _punt_cats = [_r["Category"] for _r in _weaknesses]

    _md = "### Category Strategy Recommendation\n\n"
    _md += f"**Target ({len(_target_cats)} cats):** {', '.join(_target_cats)}\n\n"
    _md += f"**Consider punting ({len(_punt_cats)} cats):** {', '.join(_punt_cats) if _punt_cats else 'None'}\n\n"
    _md += "_Strategy: Win 5 of 9 categories each week. Focus roster moves on target cats._"

    mo.md(_md)


if __name__ == "__main__":
    app.run()
