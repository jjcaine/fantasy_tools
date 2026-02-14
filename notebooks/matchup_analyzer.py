import marimo

__generated_with = "0.19.11"
app = marimo.App(width="full", app_title="Matchup Analyzer")


@app.cell
def imports():
    import marimo as mo
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent))

    from src.fantasy_math import (
        CATEGORIES,
        INVERSE_CATS,
        load_a10_players,
        load_fantrax_rosters,
        load_matchup_history,
        load_schedule,
        build_player_lookup,
        get_all_team_projections,
        predict_matchup,
        team_historical_cats,
        run_roster_match_quality,
    )

    MY_TEAM = "Sick-Os Revenge"

    players = load_a10_players()
    rosters = load_fantrax_rosters()
    matchups = load_matchup_history()
    schedule = load_schedule()
    lookup = build_player_lookup(players)

    mo.md("# Matchup Analyzer")
    return (
        CATEGORIES, MY_TEAM, get_all_team_projections, lookup,
        matchups, mo, players, predict_matchup, rosters,
        run_roster_match_quality, schedule, team_historical_cats,
    )


@app.cell
def data_quality(mo, players, rosters, lookup, run_roster_match_quality):
    _report = run_roster_match_quality(rosters, players, lookup)
    _failed = [_c for _c in _report.checks if not _c["passed"]]
    if _failed:
        _rows = "\n".join(f"| ❌ | {_c['name']} | {_c['detail']} |" for _c in _failed)
        mo.md(f"### ⚠️ Roster Match Issues\n\n| | Check | Detail |\n|--|-------|--------|\n{_rows}")
    else:
        mo.md(f"✅ All rosters matched successfully ({_report.summary})")


@app.cell
def controls(mo, rosters, schedule, MY_TEAM):
    _opponents = [_t for _t in sorted(rosters.keys()) if _t != MY_TEAM]
    opp_selector = mo.ui.dropdown(
        options=_opponents,
        value=_opponents[0] if _opponents else "",
        label="Opponent",
    )
    _period_options = {f"Period {_p}": str(_p) for _p in sorted(schedule.keys(), key=lambda x: int(x))}
    period_sel = mo.ui.dropdown(options=_period_options, value="Period 15", label="Period")

    mo.hstack([opp_selector, period_sel])
    return opp_selector, period_sel


@app.cell
def build_projections(rosters, players, schedule, period_sel, get_all_team_projections):
    period_key = period_sel.value
    all_projs = get_all_team_projections(rosters, players, schedule, int(period_key))
    return all_projs, period_key


@app.cell
def h2h_projection(mo, CATEGORIES, MY_TEAM, opp_selector, all_projs,
                   period_key, predict_matchup):
    opp = opp_selector.value
    result = None

    if MY_TEAM in all_projs and opp in all_projs:
        _our_proj = all_projs[MY_TEAM]
        _opp_proj = all_projs[opp]
        result = predict_matchup(_our_proj, _opp_proj)

        _h2h_rows = []
        for _c in result.comparisons:
            if _c.winner == "A":
                _winner = f"**{MY_TEAM}**"
            elif _c.winner == "B":
                _winner = f"**{opp}**"
            else:
                _winner = "Tie"

            _fmt = ".3f" if _c.category in ("AdjFG%", "FT%") else ".1f"
            _h2h_rows.append({
                "Category": _c.category,
                MY_TEAM: f"{_c.team_a_val:{_fmt}}",
                opp: f"{_c.team_b_val:{_fmt}}",
                "Winner": _winner,
                "Margin": f"{_c.margin:{_fmt}}",
            })

        if result.wins_a > result.wins_b:
            _outcome = f"**{result.result_str} WIN** 🎉"
        elif result.wins_b > result.wins_a:
            _outcome = f"**{result.result_str} LOSS** 😬"
        else:
            _outcome = f"**{result.result_str} TIE**"

        mo.md(f"### H2H Projection: {MY_TEAM} vs {opp} — Period {period_key}\n\nProjected Result: {_outcome}")
        mo.ui.table(_h2h_rows, selection=None)
    else:
        mo.md("_Select an opponent_")

    return opp, result


@app.cell
def win_path(mo, result, MY_TEAM, opp):
    if result is None:
        mo.md("")
    else:
        _cat_advantages = []
        for _c in result.comparisons:
            _adv = _c.margin if _c.winner == "A" else (-_c.margin if _c.winner == "B" else 0)
            _cat_advantages.append((_c.category, _adv, _c.winner))

        _cat_advantages.sort(key=lambda x: x[1], reverse=True)

        _md = f"### Win Path vs {opp}\n\n"
        _md += "_Categories sorted by our advantage (need 5 to win):_\n\n"
        _md += "| # | Category | Advantage | Status |\n|---|----------|-----------|--------|\n"

        for _i, (_cat, _adv, _winner) in enumerate(_cat_advantages, 1):
            if _winner == "A":
                _status = "✅ Winning"
            elif _winner == "B":
                _status = "❌ Losing"
            else:
                _status = "➖ Tied"
            _md += f"| {_i} | {_cat} | {_adv:+.3f} | {_status} |\n"

        mo.md(_md)


@app.cell
def all_opponents_overview(mo, MY_TEAM, all_projs, predict_matchup):
    _overview_rows = []

    if MY_TEAM in all_projs:
        _our_proj = all_projs[MY_TEAM]

        for _opp_name, _opp_proj in sorted(all_projs.items()):
            if _opp_name == MY_TEAM:
                continue
            _res = predict_matchup(_our_proj, _opp_proj)
            _overview_rows.append({
                "Opponent": _opp_name,
                "Projected": _res.result_str,
                "Our Wins": _res.wins_a,
                "Their Wins": _res.wins_b,
                "Ties": _res.ties,
                "Outcome": "WIN" if _res.wins_a > _res.wins_b else ("LOSS" if _res.wins_b > _res.wins_a else "TIE"),
            })

        _total_w = sum(1 for _r in _overview_rows if _r["Outcome"] == "WIN")
        _total_l = sum(1 for _r in _overview_rows if _r["Outcome"] == "LOSS")
        _total_t = sum(1 for _r in _overview_rows if _r["Outcome"] == "TIE")

        mo.md(f"### All Opponents Overview — Projected: {_total_w}W-{_total_l}L-{_total_t}T across all matchups")
        mo.ui.table(_overview_rows, selection=None)
    else:
        mo.md("_Our team projection not available_")


@app.cell
def opponent_history(mo, matchups, opp_selector, CATEGORIES, team_historical_cats):
    _opp = opp_selector.value
    _opp_hist = team_historical_cats(matchups, _opp)

    if _opp_hist:
        _rows = []
        for _h in _opp_hist:
            _row = {"Period": _h["period"], "Record": f"{_h['W']}-{_h['L']}-{_h['T']}"}
            for _cat in CATEGORIES:
                _row[_cat] = _h["cats"].get(_cat, "")
            _rows.append(_row)

        mo.md(f"### {_opp} — Historical Performance")
        mo.ui.table(_rows, selection=None)
    else:
        mo.md(f"_No historical data for {_opp}_")


if __name__ == "__main__":
    app.run()
