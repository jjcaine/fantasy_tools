import marimo

__generated_with = "0.19.11"
app = marimo.App(width="full", app_title="A-10 Player Rankings")


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
        load_schedule,
        compute_z_scores,
        composite_z_score,
        schedule_adjusted_composite,
        run_player_data_quality,
    )

    players = load_a10_players()
    schedule = load_schedule()

    mo.md("# A-10 Player Fantasy Rankings")
    return (
        CATEGORIES, COUNTING_CATS, composite_z_score, compute_z_scores,
        mo, players, run_player_data_quality, schedule,
        schedule_adjusted_composite,
    )


@app.cell
def data_quality(mo, players, run_player_data_quality):
    _report = run_player_data_quality(players)

    _rows = []
    for _check in _report.checks:
        _icon = "✅" if _check["passed"] else "❌"
        _rows.append(f"| {_icon} | {_check['name']} | {_check['detail']} |")

    _table_md = "| Status | Check | Detail |\n|--------|-------|--------|\n" + "\n".join(_rows)

    mo.md(f"""
## Data Quality Report

**{_report.summary}** — {len(players)} players loaded

{_table_md}
""")


@app.cell
def controls(mo, schedule):
    _period_options = {f"Period {_p}": str(_p) for _p in sorted(schedule.keys(), key=lambda x: int(x))}
    period_selector = mo.ui.dropdown(
        options=_period_options,
        value="Period 15",
        label="Schedule Period",
    )
    min_games_slider = mo.ui.slider(
        start=1, stop=25, value=5, step=1,
        label="Min Games Played",
    )
    min_mpg_slider = mo.ui.slider(
        start=0, stop=30, value=10, step=1,
        label="Min MPG",
    )
    _sort_options = {"Composite Z": "composite", "Schedule-Adjusted Composite": "sched_adj"}
    for _cat in ["AdjFG%", "3PTM", "FT%", "PTS", "REB", "AST", "ST", "BLK", "TO"]:
        _sort_options[f"Z: {_cat}"] = _cat
    sort_by = mo.ui.dropdown(
        options=_sort_options,
        value="Schedule-Adjusted Composite",
        label="Sort By",
    )

    mo.hstack([period_selector, min_games_slider, min_mpg_slider, sort_by])
    return min_games_slider, min_mpg_slider, period_selector, sort_by


@app.cell
def compute_rankings(
    CATEGORIES,
    composite_z_score,
    compute_z_scores,
    min_games_slider,
    min_mpg_slider,
    mo,
    period_selector,
    players,
    schedule,
    schedule_adjusted_composite,
    sort_by,
):
    z_results = compute_z_scores(
        players,
        min_games=min_games_slider.value,
        min_mpg=min_mpg_slider.value,
    )

    _period_key = period_selector.value
    _games_per_team = schedule.get(_period_key, {}).get("games_per_team", {})

    table_rows = []
    for _r in z_results:
        _comp = composite_z_score(_r["z_scores"])
        _team_games = _games_per_team.get(_r["team"], 0)
        _sched_adj = schedule_adjusted_composite(_r["z_scores"], _team_games)

        _row = {
            "Player": _r["name"],
            "Team": _r["team"],
            "GP": _r["games"],
            "MPG": _r["mpg"],
            "Composite Z": _comp,
            f"Sched-Adj (P{_period_key})": _sched_adj,
            f"Games P{_period_key}": _team_games,
        }
        for _cat in CATEGORIES:
            _z = _r["z_scores"].get(_cat)
            _row[f"z_{_cat}"] = _z if _z is not None else ""
        _cl = _r["cat_line"]
        _row["PPG"] = _cl.pts_pg
        _row["RPG"] = _cl.reb_pg
        _row["APG"] = _cl.ast_pg
        _row["SPG"] = _cl.stl_pg
        _row["BPG"] = _cl.blk_pg
        _row["TOPG"] = _cl.to_pg
        _row["3PM/G"] = _cl.tpm_pg
        _row["AdjFG%"] = f"{_cl.adj_fg_pct:.3f}" if _cl.adj_fg_pct else ""
        _row["FT%"] = f"{_cl.ft_pct:.3f}" if _cl.ft_pct else ""

        table_rows.append(_row)

    _sort_key = sort_by.value
    if _sort_key == "composite":
        table_rows.sort(key=lambda _x: _x.get("Composite Z", 0) or 0, reverse=True)
    elif _sort_key == "sched_adj":
        table_rows.sort(key=lambda _x: _x.get(f"Sched-Adj (P{_period_key})", 0) or 0, reverse=True)
    elif _sort_key in CATEGORIES:
        table_rows.sort(
            key=lambda _x: _x.get(f"z_{_sort_key}", -999) if _x.get(f"z_{_sort_key}", "") != "" else -999,
            reverse=True,
        )

    mo.md(f"### Rankings — {len(table_rows)} qualified players (min {min_games_slider.value} GP, {min_mpg_slider.value} MPG)")
    return table_rows, z_results


@app.cell
def display_table(mo, table_rows):
    mo.ui.table(
        table_rows,
        selection=None,
        pagination=True,
        page_size=30,
    )


@app.cell
def top_per_category(CATEGORIES, mo, z_results, composite_z_score):
    _sections = []
    for _cat in CATEGORIES:
        _ranked = [
            _r for _r in z_results
            if _r["z_scores"].get(_cat) is not None
        ]
        _ranked.sort(key=lambda _x: _x["z_scores"][_cat], reverse=True)
        _top10 = _ranked[:10]

        _lines = []
        for _i, _r in enumerate(_top10, 1):
            _z = _r["z_scores"][_cat]
            _cl = _r["cat_line"]
            _raw_map = {
                "AdjFG%": f"{_cl.adj_fg_pct:.3f}" if _cl.adj_fg_pct else "",
                "3PTM": f"{_cl.tpm_pg:.1f}",
                "FT%": f"{_cl.ft_pct:.3f}" if _cl.ft_pct else "",
                "PTS": f"{_cl.pts_pg:.1f}",
                "REB": f"{_cl.reb_pg:.1f}",
                "AST": f"{_cl.ast_pg:.1f}",
                "ST": f"{_cl.stl_pg:.1f}",
                "BLK": f"{_cl.blk_pg:.1f}",
                "TO": f"{_cl.to_pg:.1f}",
            }
            _lines.append(f"| {_i} | {_r['name']} | {_r['team']} | {_raw_map.get(_cat, '')} | {_z:+.2f} |")

        _table = f"| # | Player | Team | Per Game | Z-Score |\n|---|--------|------|----------|--------|\n" + "\n".join(_lines)
        _sections.append(f"#### Top 10: {_cat}\n\n{_table}")

    mo.md("\n\n".join(_sections))


if __name__ == "__main__":
    app.run()
