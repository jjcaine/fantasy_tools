import marimo

__generated_with = "0.19.11"
app = marimo.App(width="full", app_title="Lineup Optimizer")


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
        player_to_cat_line,
        match_player,
    )

    MY_TEAM = "Sick-Os Revenge"
    GP_MAX = 15

    players = load_a10_players()
    rosters = load_fantrax_rosters()
    schedule = load_schedule()
    lookup = build_player_lookup(players)

    lines, matched_info, unmatched = build_team_roster_lines(
        MY_TEAM, rosters, players, lookup
    )

    mo.md("# Lineup Optimizer")
    return (
        CATEGORIES, GP_MAX, MY_TEAM, composite_z_score, compute_z_scores,
        get_player_games_in_period, lines, lookup, match_player,
        matched_info, mo, players, project_team_week, rosters,
        schedule, unmatched,
    )


@app.cell
def data_quality(mo, matched_info, unmatched):
    _md = f"**Roster:** {len(matched_info)} matched"
    if unmatched:
        _names = ", ".join(_u["name"] for _u in unmatched)
        _md += f" | ⚠️ {len(unmatched)} unmatched: {_names}"
    _md += "\n\n_Verify all players are correctly matched to NCAA stats before trusting projections._"
    mo.md(_md)


@app.cell
def controls(mo, schedule):
    _period_options = {f"Period {_p}": str(_p) for _p in sorted(schedule.keys(), key=lambda x: int(x))}
    period_sel = mo.ui.dropdown(options=_period_options, value="Period 15", label="Period")
    active_slots = mo.ui.slider(start=4, stop=8, value=6, step=1, label="Active Roster Slots")

    mo.hstack([period_sel, active_slots])
    return active_slots, period_sel


@app.cell
def game_calendar(mo, lines, schedule, period_sel, matched_info, compute_z_scores, composite_z_score):
    _period_key = period_sel.value
    _period_data = schedule.get(_period_key, {})
    game_dates = _period_data.get("game_dates_per_team", {})

    _all_dates_set = set()
    for _dates in game_dates.values():
        _all_dates_set.update(_dates)
    all_dates = sorted(_all_dates_set)

    _our_z = compute_z_scores([_m["ncaa"] for _m in matched_info], min_games=1, min_mpg=0)
    z_by_name = {_r["name"]: composite_z_score(_r["z_scores"]) for _r in _our_z}

    _calendar_rows = []
    for _cl in lines:
        _team_dates = game_dates.get(_cl.team, [])
        _row = {
            "Player": _cl.name,
            "Team": _cl.team,
            "Value (Z)": round(z_by_name.get(_cl.name, 0), 1),
            "Total Games": len([_d for _d in _team_dates if _d in all_dates]),
        }
        for _d in all_dates:
            _day_label = _d[5:]
            _row[_day_label] = "🏀" if _d in _team_dates else ""
        _calendar_rows.append(_row)

    _calendar_rows.sort(key=lambda _x: _x.get("Value (Z)", 0), reverse=True)

    mo.md(f"### Game Calendar — Period {_period_key} ({_period_data.get('start', '')} to {_period_data.get('end', '')})")
    mo.ui.table(_calendar_rows, selection=None)
    return all_dates, game_dates, z_by_name


@app.cell
def gp_tracker(mo, lines, game_dates, GP_MAX, all_dates):
    _total_available = sum(
        len([_d for _d in game_dates.get(_cl.team, []) if _d in all_dates])
        for _cl in lines
    )

    _pct = min(_total_available / GP_MAX * 100, 100) if GP_MAX > 0 else 0
    _bar_fill = int(_pct / 5)
    _bar = "█" * _bar_fill + "░" * (20 - _bar_fill)

    _md = f"### GP Budget Tracker\n\n"
    _md += f"**Available Starts:** {_total_available} | **GP Max:** {GP_MAX}\n\n"
    _md += f"**Usage:** [{_bar}] {_total_available}/{GP_MAX}\n\n"

    if _total_available <= GP_MAX:
        _md += "✅ Can start everyone in every game — no benching needed!"
    else:
        _md += f"⚠️ {_total_available - GP_MAX} starts must be benched. Use the optimizer below."

    mo.md(_md)


@app.cell
def optimal_lineup(mo, lines, game_dates, all_dates, z_by_name, GP_MAX, active_slots):
    _max_active = active_slots.value
    _lineup_plan = []
    _cumulative_gp = 0

    for _d in all_dates:
        _day_label = _d if isinstance(_d, str) else str(_d)
        _playing = []
        for _cl in lines:
            _team_dates = game_dates.get(_cl.team, [])
            if _day_label in _team_dates:
                _playing.append({
                    "name": _cl.name,
                    "team": _cl.team,
                    "value": z_by_name.get(_cl.name, 0),
                })

        _playing.sort(key=lambda _x: _x["value"], reverse=True)

        _starters = []
        _benched = []

        if len(_playing) <= _max_active:
            if _cumulative_gp + len(_playing) <= GP_MAX:
                _starters = _playing
            else:
                _remaining = GP_MAX - _cumulative_gp
                _starters = _playing[:_remaining]
                _benched = _playing[_remaining:]
        else:
            _can_start = min(_max_active, GP_MAX - _cumulative_gp)
            _starters = _playing[:_can_start]
            _benched = _playing[_can_start:]

        _cumulative_gp += len(_starters)

        _lineup_plan.append({
            "Date": _day_label[5:] if len(_day_label) > 5 else _day_label,
            "Playing": len(_playing),
            "Starting": len(_starters),
            "Benched": len(_benched),
            "Starters": ", ".join(_p["name"] for _p in _starters) if _starters else "—",
            "Benched Players": ", ".join(f"{_p['name']} (z={_p['value']:.1f})" for _p in _benched) if _benched else "—",
            "Cumulative GP": _cumulative_gp,
        })

    mo.md(f"### Optimal Daily Lineup — {_cumulative_gp}/{GP_MAX} GP used")
    mo.ui.table(_lineup_plan, selection=None)


@app.cell
def projection_with_lineup(
    mo, CATEGORIES, lines, game_dates, all_dates, z_by_name,
    GP_MAX, active_slots, project_team_week, MY_TEAM,
):
    _max_active = active_slots.value

    _effective_games = {_cl.name: 0 for _cl in lines}

    for _d in all_dates:
        _day_label = _d if isinstance(_d, str) else str(_d)
        _playing = []
        for _cl in lines:
            _team_dates = game_dates.get(_cl.team, [])
            if _day_label in _team_dates:
                _playing.append(_cl)

        _playing.sort(key=lambda _x: z_by_name.get(_x.name, 0), reverse=True)
        _gp_used = sum(_effective_games.values())
        _can_start = min(len(_playing), _max_active, GP_MAX - _gp_used)

        for _cl in _playing[:_can_start]:
            _effective_games[_cl.name] += 1

    _proj = project_team_week(lines, _effective_games, period=0, team_name=MY_TEAM)

    _rows = []
    for _cat in CATEGORIES:
        _val = _proj.cats.get(_cat, 0)
        _fmt = ".3f" if _cat in ("AdjFG%", "FT%") else ".1f"
        _rows.append({"Category": _cat, "Projected Total": f"{_val:{_fmt}}"})

    mo.md("### Category Projections (with lineup plan)")
    mo.ui.table(_rows, selection=None)


@app.cell
def streaming_slots(
    mo, lines, game_dates, all_dates, active_slots, players,
    compute_z_scores, composite_z_score, rosters, lookup, match_player,
):
    _max_active = active_slots.value

    _open_days = []
    for _d in all_dates:
        _day_label = _d if isinstance(_d, str) else str(_d)
        _playing_count = sum(
            1 for _cl in lines
            if _day_label in game_dates.get(_cl.team, [])
        )
        if _playing_count < _max_active:
            _open_days.append((_day_label, _max_active - _playing_count))

    if not _open_days:
        mo.md("### Streaming Slots\n\n_No open slots — all days have full lineups._")
    else:
        _rostered_names = set()
        for _team_name, _team_data in rosters.items():
            for _fp in _team_data.get("players", []):
                _ncaa = match_player(_fp["name"], _fp.get("team", ""), lookup, players)
                if _ncaa:
                    _rostered_names.add(_ncaa["name"])

        _free_agents = [_p for _p in players if _p["name"] not in _rostered_names]
        _fa_z = compute_z_scores(_free_agents, min_games=5, min_mpg=10)

        _md = "### Streaming Slots\n\n_Days with open roster spots + best available FAs:_\n\n"
        for _day, _slots in _open_days:
            _teams_playing = [_t for _t, _dates in game_dates.items() if _day in _dates]
            _fas_playing = [_r for _r in _fa_z if _r["team"] in _teams_playing]
            _fas_playing.sort(key=lambda _x: composite_z_score(_x["z_scores"]), reverse=True)

            _day_short = _day[5:] if len(_day) > 5 else _day
            _top_fas = _fas_playing[:5]
            if _top_fas:
                _names = ", ".join(f"{_r['name']} ({_r['team']}, z={composite_z_score(_r['z_scores']):+.1f})" for _r in _top_fas)
                _md += f"**{_day_short}** ({_slots} open): {_names}\n\n"
            else:
                _md += f"**{_day_short}** ({_slots} open): _No qualified FAs playing_\n\n"

        mo.md(_md)


if __name__ == "__main__":
    app.run()
