import marimo

__generated_with = "0.19.11"
app = marimo.App(width="full", app_title="Waiver Wire Optimizer")


@app.cell
def imports():
    import marimo as mo
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent))

    from src.fantasy_math import (
        CATEGORIES,
        load_a10_players,
        load_fantrax_rosters,
        load_schedule,
        build_player_lookup,
        build_team_roster_lines,
        get_player_games_in_period,
        project_team_week,
        compute_z_scores,
        composite_z_score,
        schedule_adjusted_composite,
        player_to_cat_line,
        match_player,
    )

    MY_TEAM = "Sick-Os Revenge"

    players = load_a10_players()
    rosters = load_fantrax_rosters()
    schedule = load_schedule()
    lookup = build_player_lookup(players)

    mo.md("# Waiver Wire Optimizer")
    return (
        CATEGORIES, MY_TEAM, build_team_roster_lines,
        composite_z_score, compute_z_scores, get_player_games_in_period,
        lookup, match_player, mo, player_to_cat_line, players,
        project_team_week, rosters, schedule, schedule_adjusted_composite,
    )


@app.cell
def identify_free_agents(mo, players, rosters, lookup, match_player):
    _rostered_names = set()
    for _team_name, _team_data in rosters.items():
        for _fp in _team_data.get("players", []):
            _ncaa = match_player(_fp["name"], _fp.get("team", ""), lookup, players)
            if _ncaa:
                _rostered_names.add(_ncaa["name"])

    free_agents = [_p for _p in players if _p["name"] not in _rostered_names]

    mo.md(f"### Free Agent Pool: {len(free_agents)} players ({len(_rostered_names)} rostered)")
    return (free_agents,)


@app.cell
def data_quality_check(mo, free_agents):
    _fa_teams = set(_p["team"] for _p in free_agents)
    _high_value = [_p for _p in free_agents if (_p.get("games", 0) or 0) >= 10 and (_p.get("mpg", 0) or 0) >= 15]

    _md = "#### FA Pool Quality\n\n"
    _md += f"- Teams represented: {len(_fa_teams)} ({', '.join(sorted(_fa_teams))})\n"
    _md += f"- Qualified FAs (10+ GP, 15+ MPG): {len(_high_value)}\n"

    for _p in _high_value:
        if (_p.get("ppg", 0) or 0) > 20:
            _md += f"- ⚠️ **{_p['name']}** ({_p['team']}) has {_p['ppg']} PPG — verify not rostered\n"

    mo.md(_md)


@app.cell
def controls(mo, schedule):
    _period_options = {f"Period {_p}": str(_p) for _p in sorted(schedule.keys(), key=lambda x: int(x))}
    period_sel = mo.ui.dropdown(options=_period_options, value="Period 15", label="Period")
    _cat_options = {"All Categories": "all"}
    for _c in ["AdjFG%", "3PTM", "FT%", "PTS", "REB", "AST", "ST", "BLK", "TO"]:
        _cat_options[_c] = _c
    cat_focus = mo.ui.dropdown(
        options=_cat_options,
        value="All Categories",
        label="Category Focus",
    )
    min_gp = mo.ui.slider(start=1, stop=20, value=5, step=1, label="Min Games")

    mo.hstack([period_sel, cat_focus, min_gp])
    return cat_focus, min_gp, period_sel


@app.cell
def ranked_free_agents(
    mo, CATEGORIES, free_agents, schedule, period_sel, cat_focus, min_gp,
    compute_z_scores, composite_z_score, schedule_adjusted_composite,
):
    _period_key = period_sel.value
    _games_per_team = schedule.get(_period_key, {}).get("games_per_team", {})

    z_results = compute_z_scores(free_agents, min_games=min_gp.value, min_mpg=10)

    _table_rows = []
    for _r in z_results:
        _team_games = _games_per_team.get(_r["team"], 0)
        _comp = composite_z_score(_r["z_scores"])
        _sched_adj = schedule_adjusted_composite(_r["z_scores"], _team_games)

        _row = {
            "Player": _r["name"],
            "Team": _r["team"],
            "GP": _r["games"],
            "MPG": _r["mpg"],
            "Composite Z": _comp,
            f"Sched-Adj P{_period_key}": _sched_adj,
            f"Games P{_period_key}": _team_games,
        }
        for _cat in CATEGORIES:
            _z = _r["z_scores"].get(_cat)
            _row[f"z_{_cat}"] = _z if _z is not None else ""
        _cl = _r["cat_line"]
        _row["PPG"] = _cl.pts_pg
        _row["RPG"] = _cl.reb_pg
        _row["APG"] = _cl.ast_pg
        _row["3PM/G"] = _cl.tpm_pg
        _row["SPG"] = _cl.stl_pg
        _row["BPG"] = _cl.blk_pg
        _row["TOPG"] = _cl.to_pg
        _table_rows.append(_row)

    _focus = cat_focus.value
    if _focus == "all":
        _table_rows.sort(key=lambda _x: _x.get(f"Sched-Adj P{_period_key}", 0), reverse=True)
    else:
        _table_rows.sort(
            key=lambda _x: _x.get(f"z_{_focus}", -999) if _x.get(f"z_{_focus}", "") != "" else -999,
            reverse=True,
        )

    mo.md(f"### Ranked Free Agents — {len(_table_rows)} qualified")
    mo.ui.table(_table_rows, selection=None, pagination=True, page_size=25)
    return (z_results,)


@app.cell
def category_best_available(mo, CATEGORIES, z_results, composite_z_score):
    _sections = []
    for _cat in CATEGORIES:
        _ranked = [_r for _r in z_results if _r["z_scores"].get(_cat) is not None]
        _ranked.sort(key=lambda _x: _x["z_scores"][_cat], reverse=True)
        _top5 = _ranked[:5]

        _lines = []
        for _i, _r in enumerate(_top5, 1):
            _z = _r["z_scores"][_cat]
            _lines.append(f"| {_i} | {_r['name']} | {_r['team']} | {_z:+.2f} | {_r['games']} GP |")

        _table = "| # | Player | Team | Z | GP |\n|---|--------|------|---|----|\n" + "\n".join(_lines)
        _sections.append(f"**{_cat}**\n\n{_table}")

    mo.md("### Best Available by Category\n\n" + "\n\n".join(_sections))


@app.cell
def roster_upgrade(
    mo, MY_TEAM, rosters, players, lookup, free_agents,
    build_team_roster_lines, compute_z_scores, composite_z_score,
):
    roster_lines, roster_matched, _ = build_team_roster_lines(MY_TEAM, rosters, players, lookup)
    _our_z = compute_z_scores([_m["ncaa"] for _m in roster_matched], min_games=1, min_mpg=0)
    fa_z = compute_z_scores(free_agents, min_games=5, min_mpg=10)

    upgrade_rows = []
    for _our_r in _our_z:
        _our_comp = composite_z_score(_our_r["z_scores"])
        _best_fa = max(fa_z, key=lambda _x: composite_z_score(_x["z_scores"])) if fa_z else None
        if _best_fa:
            _fa_comp = composite_z_score(_best_fa["z_scores"])
            _diff = _fa_comp - _our_comp
            upgrade_rows.append({
                "Current Player": _our_r["name"],
                "Current Z": _our_comp,
                "Best FA": _best_fa["name"],
                "FA Z": _fa_comp,
                "Upgrade": f"{_diff:+.2f}",
                "Clear Upgrade?": "✅ Yes" if _diff > 1.0 else ("⬆️ Maybe" if _diff > 0 else ""),
            })

    upgrade_rows.sort(key=lambda _x: float(_x["Upgrade"]), reverse=True)

    mo.md("### Roster Upgrade Analysis\n\n_Comparing each of our players to the single best available FA:_")
    mo.ui.table(upgrade_rows, selection=None)
    return fa_z, roster_lines, roster_matched, upgrade_rows


@app.cell
def swap_simulator_controls(mo, roster_matched, fa_z, composite_z_score):
    _drop_options = [_m["ncaa"]["name"] for _m in roster_matched]
    drop_sel = mo.ui.dropdown(options=_drop_options, label="Drop Player")

    _fa_sorted = sorted(fa_z, key=lambda _x: composite_z_score(_x["z_scores"]), reverse=True)[:20]
    _add_options = {f"{_r['name']} ({_r['team']})": _r["name"] for _r in _fa_sorted}
    add_sel = mo.ui.dropdown(options=_add_options, label="Add Player")

    mo.hstack([drop_sel, add_sel])
    return add_sel, drop_sel


@app.cell
def swap_impact(
    mo, CATEGORIES, MY_TEAM, drop_sel, add_sel, roster_lines, schedule, period_sel,
    players, player_to_cat_line, get_player_games_in_period,
    project_team_week,
):
    if drop_sel.value and add_sel.value:
        _drop_name = drop_sel.value
        _add_name = add_sel.value

        _new_lines = [_cl for _cl in roster_lines if _cl.name != _drop_name]
        _add_player = next((_p for _p in players if _p["name"] == _add_name), None)
        if _add_player:
            _new_lines.append(player_to_cat_line(_add_player))

        _period_key = period_sel.value
        _old_games = get_player_games_in_period(roster_lines, schedule, int(_period_key))
        _new_games = get_player_games_in_period(_new_lines, schedule, int(_period_key))

        _old_proj = project_team_week(roster_lines, _old_games, period=_period_key, team_name=MY_TEAM)
        _new_proj = project_team_week(_new_lines, _new_games, period=_period_key, team_name=MY_TEAM)

        _swap_rows = []
        for _cat in CATEGORIES:
            _old_val = _old_proj.cats.get(_cat, 0)
            _new_val = _new_proj.cats.get(_cat, 0)
            _diff = _new_val - _old_val
            _is_better = (_diff < 0) if _cat == "TO" else (_diff > 0)
            _icon = "⬆️" if _is_better else ("⬇️" if _diff != 0 and not _is_better else "➖")

            _fmt = ".3f" if _cat in ("AdjFG%", "FT%") else ".1f"
            _swap_rows.append({
                "Category": _cat,
                "Before": f"{_old_val:{_fmt}}",
                "After": f"{_new_val:{_fmt}}",
                "Change": f"{_diff:+{_fmt}}",
                "Impact": _icon,
            })

        mo.md(f"### Swap Impact: Drop **{_drop_name}** → Add **{_add_name}** (P{_period_key})")
        mo.ui.table(_swap_rows, selection=None)
    else:
        mo.md("_Select a player to drop and add above_")


@app.cell
def bid_recommendations(mo, upgrade_rows):
    _md = "### Bid Recommendations\n\n"
    _md += "_Budget: $100 across 3 playoff rounds. Rough heuristic: ~$50 R1, ~$30 R2, ~$20 R3._\n\n"
    _md += "| FA Target | Drop | Upgrade Z | Suggested Bid |\n|-----------|------|-----------|---------------|\n"

    for _r in upgrade_rows:
        _diff = float(_r["Upgrade"])
        if _diff <= 0:
            continue
        if _diff > 3.0:
            _bid = "$40-50"
        elif _diff > 2.0:
            _bid = "$25-35"
        elif _diff > 1.0:
            _bid = "$15-25"
        else:
            _bid = "$5-15"
        _md += f"| {_r['Best FA']} | {_r['Current Player']} | {_r['Upgrade']} | {_bid} |\n"

    mo.md(_md)


@app.cell
def streaming_preview(mo, free_agents, schedule, period_sel, compute_z_scores, composite_z_score):
    _period_key = period_sel.value
    _period_data = schedule.get(_period_key, {})
    _game_dates = _period_data.get("game_dates_per_team", {})

    _fa_z = compute_z_scores(free_agents, min_games=5, min_mpg=10)

    _all_dates = set()
    for _dates in _game_dates.values():
        _all_dates.update(_dates)

    _md = f"### Streaming Preview — Period {_period_key}\n\n"
    _md += "_Top 5 available FAs by game date:_\n\n"
    for _d in sorted(_all_dates):
        _teams_playing = [_t for _t, _dates in _game_dates.items() if _d in _dates]
        _fas_playing = [_r for _r in _fa_z if _r["team"] in _teams_playing]
        _fas_playing.sort(key=lambda _x: composite_z_score(_x["z_scores"]), reverse=True)
        _top5 = _fas_playing[:5]
        if _top5:
            _names = ", ".join(f"{_r['name']} ({_r['team']}, z={composite_z_score(_r['z_scores']):+.1f})" for _r in _top5)
            _md += f"**{_d}**: {_names}\n\n"
        else:
            _md += f"**{_d}**: _No qualified FAs playing_\n\n"

    mo.md(_md)


if __name__ == "__main__":
    app.run()
