"""Tests for fantasy_math shared computation module."""

import pytest
from src.fantasy_math import (
    CATEGORIES,
    COUNTING_CATS,
    INVERSE_CATS,
    FANTRAX_TO_NCAA_TEAM,
    FANTRAX_SHORT_TO_NCAA,
    aggregate_boxscores,
    calc_adj_fg_pct,
    composite_z_score,
    schedule_adjusted_composite,
    normalize_fantrax_team,
    _normalize_name,
    build_player_lookup,
    match_player,
    player_to_cat_line,
    compute_z_scores,
    project_team_week,
    compare_categories,
    predict_matchup,
    team_historical_cats,
    team_category_ranks,
    get_player_games_in_period,
    run_player_data_quality,
    PlayerCatLine,
    TeamProjection,
)


# ── Fixtures ────────────────────────────────────────────────────────────

def _make_player(
    name="Test Player",
    team="Dayton",
    games=20,
    mpg=30.0,
    fgm=100,
    fga=200,
    ftm=50,
    fta=60,
    tpm=30,
    reb=80,
    ast=60,
    stl=20,
    blk=10,
    to=30,
    pts=None,
):
    """Helper to create a player stats dict."""
    if pts is None:
        pts = 2 * (fgm - tpm) + 3 * tpm + ftm
    return {
        "name": name,
        "team": team,
        "position": "G",
        "games": games,
        "total_minutes": int(mpg * games),
        "fgm": fgm,
        "fga": fga,
        "ftm": ftm,
        "fta": fta,
        "tpm": tpm,
        "tpa": tpm + 20,
        "reb": reb,
        "ast": ast,
        "stl": stl,
        "blk": blk,
        "to": to,
        "pts": pts,
        "pf": 40,
        "ppg": round(pts / games, 1),
        "rpg": round(reb / games, 1),
        "apg": round(ast / games, 1),
        "spg": round(stl / games, 1),
        "bpg": round(blk / games, 1),
        "topg": round(to / games, 1),
        "tpm_pg": round(tpm / games, 1),
        "mpg": mpg,
        "fg_pct": round(fgm / fga, 4) if fga > 0 else None,
        "ft_pct": round(ftm / fta, 4) if fta > 0 else None,
    }


@pytest.fixture
def sample_players():
    """A set of diverse players for testing z-scores."""
    return [
        _make_player("High Scorer", "Dayton", games=20, fgm=140, fga=280, ftm=80, fta=100, tpm=40, reb=60, ast=80, stl=30, blk=15, to=25),
        _make_player("Rebounder", "VCU", games=20, fgm=80, fga=160, ftm=40, fta=60, tpm=5, reb=180, ast=20, stl=10, blk=30, to=20),
        _make_player("Three Point", "Saint Louis", games=20, fgm=100, fga=250, ftm=30, fta=35, tpm=60, reb=40, ast=30, stl=15, blk=5, to=35),
        _make_player("Playmaker", "Duquesne", games=20, fgm=90, fga=200, ftm=50, fta=60, tpm=20, reb=50, ast=120, stl=25, blk=8, to=40),
        _make_player("Defender", "Fordham", games=20, fgm=70, fga=170, ftm=30, fta=40, tpm=10, reb=70, ast=40, stl=40, blk=20, to=15),
        _make_player("Bench Player", "Davidson", games=20, fgm=40, fga=100, ftm=20, fta=30, tpm=10, reb=30, ast=15, stl=8, blk=3, to=18),
    ]


# ── Category math ──────────────────────────────────────────────────────

class TestAdjFgPct:
    def test_basic_calculation(self):
        # (100 + 0.5*30) / 200 = 115/200 = 0.575
        assert calc_adj_fg_pct(100, 30, 200) == 0.575

    def test_no_threes(self):
        # (50 + 0) / 100 = 0.5
        assert calc_adj_fg_pct(50, 0, 100) == 0.5

    def test_zero_attempts(self):
        assert calc_adj_fg_pct(0, 0, 0) is None

    def test_all_threes(self):
        # All field goals are threes: (10 + 0.5*10) / 20 = 15/20 = 0.75
        assert calc_adj_fg_pct(10, 10, 20) == 0.75


class TestPlayerToCatLine:
    def test_basic(self):
        p = _make_player()
        cl = player_to_cat_line(p)
        assert cl.name == "Test Player"
        assert cl.team == "Dayton"
        assert cl.games == 20
        assert cl.adj_fg_pct == calc_adj_fg_pct(100, 30, 200)
        assert cl.ft_pct == pytest.approx(50 / 60)
        assert cl.pts_pg == pytest.approx(p["ppg"])
        assert cl.reb_pg == pytest.approx(p["rpg"])

    def test_zero_fta(self):
        p = _make_player(ftm=0, fta=0)
        cl = player_to_cat_line(p)
        assert cl.ft_pct is None

    def test_per_game_volumes(self):
        p = _make_player(games=10, fgm=50, fga=100, ftm=20, fta=30, tpm=15)
        cl = player_to_cat_line(p)
        assert cl.fgm_pg == pytest.approx(5.0)
        assert cl.fga_pg == pytest.approx(10.0)
        assert cl.ftm_pg == pytest.approx(2.0)
        assert cl.fta_pg == pytest.approx(3.0)


# ── Name matching ──────────────────────────────────────────────────────

class TestNormalizeName:
    def test_basic(self):
        assert _normalize_name("John Smith") == "john smith"

    def test_strip_jr(self):
        assert _normalize_name("Deuce Jones Jr.") == "deuce jones"
        assert _normalize_name("Deuce Jones Jr") == "deuce jones"

    def test_strip_suffixes(self):
        assert _normalize_name("Deuce Jones II") == "deuce jones"
        assert _normalize_name("Player III") == "player"
        assert _normalize_name("Player IV") == "player"

    def test_strip_apostrophe(self):
        assert _normalize_name("O'Brien") == "obrien"

    def test_strip_comma_suffix(self):
        assert _normalize_name("Jerome Brewer, Jr.") == "jerome brewer"

    def test_strip_period(self):
        assert _normalize_name("J.R. Smith") == "jr smith"


class TestNormalizeFantraxTeam:
    def test_full_name(self):
        assert normalize_fantrax_team("Duquesne Dukes") == "Duquesne"
        assert normalize_fantrax_team("VCU Rams") == "VCU"
        assert normalize_fantrax_team("Loyola (IL) Ramblers") == "Loyola Chicago"

    def test_short_code(self):
        assert normalize_fantrax_team("Duques") == "Duquesne"
        assert normalize_fantrax_team("LoyIL") == "Loyola Chicago"
        assert normalize_fantrax_team("URI") == "Rhode Island"

    def test_unknown_passthrough(self):
        assert normalize_fantrax_team("Unknown Team") == "Unknown Team"


class TestMatchPlayer:
    def test_exact_match(self):
        players = [_make_player("Jimmie Williams", "Duquesne")]
        lookup = build_player_lookup(players)
        result = match_player("Jimmie Williams", "Duquesne Dukes", lookup, players)
        assert result is not None
        assert result["name"] == "Jimmie Williams"

    def test_team_disambiguation(self):
        players = [
            _make_player("Alex Williams", "Duquesne"),
            _make_player("Alex Williams", "VCU"),
        ]
        lookup = build_player_lookup(players)
        result = match_player("Alex Williams", "Duquesne Dukes", lookup, players)
        assert result["team"] == "Duquesne"

    def test_last_name_fallback(self):
        players = [_make_player("Tarence Guinyard", "Duquesne")]
        lookup = build_player_lookup(players)
        # Different first name but same last name + team
        result = match_player("T. Guinyard", "Duquesne Dukes", lookup, players)
        assert result is not None
        assert result["name"] == "Tarence Guinyard"

    def test_no_match(self):
        players = [_make_player("Real Player", "Dayton")]
        lookup = build_player_lookup(players)
        result = match_player("Totally Unknown", "Dayton Flyers", lookup, players)
        assert result is None

    def test_suffix_matching(self):
        players = [_make_player("Deuce Jones II", "Saint Joseph's")]
        lookup = build_player_lookup(players)
        # FanTrax might list without suffix
        result = match_player("Deuce Jones", "Saint Joseph's Hawks", lookup, players)
        # The lookup key for "Deuce Jones II" is "deuce jones", same as "Deuce Jones"
        assert result is not None


# ── Z-scores ───────────────────────────────────────────────────────────

class TestZScores:
    def test_returns_all_qualified(self, sample_players):
        results = compute_z_scores(sample_players, min_games=5, min_mpg=10)
        assert len(results) == len(sample_players)

    def test_filters_by_games(self, sample_players):
        # Add a player with only 3 games
        players = sample_players + [_make_player("Newbie", games=3)]
        results = compute_z_scores(players, min_games=5, min_mpg=10)
        names = {r["name"] for r in results}
        assert "Newbie" not in names

    def test_filters_by_mpg(self, sample_players):
        players = sample_players + [_make_player("Benchwarmer", mpg=5.0)]
        results = compute_z_scores(players, min_games=5, min_mpg=10)
        names = {r["name"] for r in results}
        assert "Benchwarmer" not in names

    def test_z_scores_have_all_cats(self, sample_players):
        results = compute_z_scores(sample_players)
        for r in results:
            for cat in CATEGORIES:
                assert cat in r["z_scores"]

    def test_z_scores_mean_near_zero(self, sample_players):
        results = compute_z_scores(sample_players)
        for cat in CATEGORIES:
            values = [r["z_scores"][cat] for r in results if r["z_scores"][cat] is not None]
            if values:
                mean = sum(values) / len(values)
                assert abs(mean) < 0.1, f"{cat} mean z-score {mean} not near zero"

    def test_to_inverted(self, sample_players):
        results = compute_z_scores(sample_players)
        # Defender has lowest TO (15) so should have highest TO z-score
        defender = next(r for r in results if r["name"] == "Defender")
        playmaker = next(r for r in results if r["name"] == "Playmaker")
        assert defender["z_scores"]["TO"] > playmaker["z_scores"]["TO"]

    def test_pct_cats_volume_filter(self):
        # Player with < 2 FGA/g should have None for AdjFG%
        players = [
            _make_player("Low Volume", games=20, fgm=10, fga=30, tpm=5),  # 1.5 FGA/g
            _make_player("Normal", games=20, fgm=100, fga=200, tpm=30),
            _make_player("Normal2", games=20, fgm=90, fga=180, tpm=25),
            _make_player("Normal3", games=20, fgm=80, fga=160, tpm=20),
            _make_player("Normal4", games=20, fgm=70, fga=140, tpm=15),
            _make_player("Normal5", games=20, fgm=60, fga=120, tpm=10),
        ]
        results = compute_z_scores(players)
        low_vol = next(r for r in results if r["name"] == "Low Volume")
        assert low_vol["z_scores"]["AdjFG%"] is None


class TestCompositeZScore:
    def test_basic_sum(self):
        z = {cat: 1.0 for cat in CATEGORIES}
        assert composite_z_score(z) == 9.0

    def test_with_none(self):
        z = {cat: 1.0 for cat in CATEGORIES}
        z["AdjFG%"] = None
        assert composite_z_score(z) == 8.0

    def test_weighted(self):
        z = {cat: 1.0 for cat in CATEGORIES}
        weights = {cat: 0.0 for cat in CATEGORIES}
        weights["PTS"] = 2.0
        assert composite_z_score(z, weights) == 2.0


class TestScheduleAdjustedComposite:
    def test_baseline_no_adjustment(self):
        z = {"PTS": 1.0, "REB": 1.0, "AdjFG%": 1.0, "FT%": 1.0, "TO": 1.0,
             "3PTM": 1.0, "AST": 1.0, "ST": 1.0, "BLK": 1.0}
        # At baseline (2 games), counting cats should be unchanged
        result = schedule_adjusted_composite(z, team_games=2, baseline_games=2)
        assert result == 9.0

    def test_double_games_doubles_counting(self):
        z = {"PTS": 1.0, "REB": 0.0, "AdjFG%": 0.0, "FT%": 0.0, "TO": 0.0,
             "3PTM": 0.0, "AST": 0.0, "ST": 0.0, "BLK": 0.0}
        # PTS is a counting cat, 4 games vs 2 baseline = 2x
        result = schedule_adjusted_composite(z, team_games=4, baseline_games=2)
        assert result == 2.0  # 1.0 * 2.0

    def test_pct_cats_unscaled(self):
        z = {"PTS": 0.0, "REB": 0.0, "AdjFG%": 1.0, "FT%": 1.0, "TO": 1.0,
             "3PTM": 0.0, "AST": 0.0, "ST": 0.0, "BLK": 0.0}
        # Pct + TO cats should NOT scale
        result = schedule_adjusted_composite(z, team_games=4, baseline_games=2)
        assert result == 3.0  # 1.0 + 1.0 + 1.0


# ── Weekly projections ─────────────────────────────────────────────────

class TestProjectTeamWeek:
    def test_counting_cats_scale_by_games(self):
        p = _make_player("Star", "Dayton", games=20)
        cl = player_to_cat_line(p)
        games = {"Star": 3}
        proj = project_team_week([cl], games)
        # PTS should be ppg * 3
        assert proj.cats["PTS"] == pytest.approx(p["ppg"] * 3, abs=0.2)

    def test_zero_games_zero_projection(self):
        p = _make_player("Star", "Dayton")
        cl = player_to_cat_line(p)
        games = {"Star": 0}
        proj = project_team_week([cl], games)
        assert proj.cats["PTS"] == 0.0
        assert proj.cats["REB"] == 0.0

    def test_volume_weighted_pct(self):
        # Two players with different FG% and volume
        p1 = _make_player("Efficient", "Dayton", games=10, fgm=60, fga=100, tpm=10)
        p2 = _make_player("Volume", "VCU", games=10, fgm=40, fga=100, tpm=5)
        cl1 = player_to_cat_line(p1)
        cl2 = player_to_cat_line(p2)
        games = {"Efficient": 2, "Volume": 2}
        proj = project_team_week([cl1, cl2], games)

        # Volume-weighted AdjFG%: sum(adj_fgm*g) / sum(fga*g)
        adj_fgm1 = (60 / 10 + 0.5 * 10 / 10) * 2  # (6 + 0.5) * 2 = 13
        adj_fgm2 = (40 / 10 + 0.5 * 5 / 10) * 2    # (4 + 0.25) * 2 = 8.5
        fga_total = (100 / 10) * 2 + (100 / 10) * 2  # 20 + 20 = 40
        expected = (adj_fgm1 + adj_fgm2) / fga_total
        assert proj.cats["AdjFG%"] == pytest.approx(expected, abs=0.001)

    def test_multiple_players_sum(self):
        p1 = _make_player("Player1", "Dayton", games=10, reb=50)  # 5 rpg
        p2 = _make_player("Player2", "VCU", games=10, reb=30)     # 3 rpg
        cl1 = player_to_cat_line(p1)
        cl2 = player_to_cat_line(p2)
        games = {"Player1": 2, "Player2": 3}
        proj = project_team_week([cl1, cl2], games)
        # 5*2 + 3*3 = 19
        assert proj.cats["REB"] == pytest.approx(19.0, abs=0.2)


# ── Matchup analysis ──────────────────────────────────────────────────

class TestCompareCategories:
    def test_basic_comparison(self):
        proj_a = TeamProjection(team_name="Team A", period=15)
        proj_a.cats = {
            "AdjFG%": 0.55, "3PTM": 15, "FT%": 0.80, "PTS": 160,
            "REB": 60, "AST": 35, "ST": 12, "BLK": 8, "TO": 14,
        }
        proj_b = TeamProjection(team_name="Team B", period=15)
        proj_b.cats = {
            "AdjFG%": 0.50, "3PTM": 18, "FT%": 0.75, "PTS": 150,
            "REB": 65, "AST": 30, "ST": 10, "BLK": 10, "TO": 18,
        }
        result = compare_categories(proj_a, proj_b)
        assert result.wins_a + result.wins_b + result.ties == 9

    def test_to_lower_wins(self):
        proj_a = TeamProjection(team_name="A", period=1)
        proj_a.cats = {c: 0 for c in CATEGORIES}
        proj_a.cats["TO"] = 10  # lower = better

        proj_b = TeamProjection(team_name="B", period=1)
        proj_b.cats = {c: 0 for c in CATEGORIES}
        proj_b.cats["TO"] = 15

        result = compare_categories(proj_a, proj_b)
        to_comp = next(c for c in result.comparisons if c.category == "TO")
        assert to_comp.winner == "A"

    def test_tie(self):
        proj_a = TeamProjection(team_name="A", period=1)
        proj_a.cats = {c: 50.0 for c in CATEGORIES}
        proj_b = TeamProjection(team_name="B", period=1)
        proj_b.cats = {c: 50.0 for c in CATEGORIES}
        result = compare_categories(proj_a, proj_b)
        assert result.ties == 9


class TestPredictMatchup:
    def test_result_string(self):
        proj_a = TeamProjection(team_name="A", period=1)
        proj_a.cats = {
            "AdjFG%": 0.55, "3PTM": 15, "FT%": 0.80, "PTS": 160,
            "REB": 60, "AST": 35, "ST": 12, "BLK": 8, "TO": 14,
        }
        proj_b = TeamProjection(team_name="B", period=1)
        proj_b.cats = {
            "AdjFG%": 0.50, "3PTM": 10, "FT%": 0.75, "PTS": 150,
            "REB": 50, "AST": 30, "ST": 10, "BLK": 5, "TO": 18,
        }
        result = predict_matchup(proj_a, proj_b)
        assert result.wins_a == 9
        assert result.result_str == "9-0-0"

    def test_sorted_by_margin(self):
        proj_a = TeamProjection(team_name="A", period=1)
        proj_a.cats = {c: 100.0 for c in CATEGORIES}
        proj_a.cats["PTS"] = 200  # big advantage
        proj_a.cats["REB"] = 101  # small advantage
        proj_a.cats["TO"] = 100

        proj_b = TeamProjection(team_name="B", period=1)
        proj_b.cats = {c: 100.0 for c in CATEGORIES}
        proj_b.cats["TO"] = 100

        result = predict_matchup(proj_a, proj_b)
        # PTS should come before REB (bigger margin)
        margins = [(c.category, c.margin) for c in result.comparisons if c.margin > 0]
        if len(margins) >= 2:
            assert margins[0][1] >= margins[1][1]


# ── Historical analysis ────────────────────────────────────────────────

class TestHistorical:
    @pytest.fixture
    def sample_matchup_history(self):
        return {
            "1": {
                "rows": [
                    {"team_name": "Sick-Os Revenge", "W": "5", "L": "4", "T": "0",
                     "AdjFG%": "0.520", "3PTM": "12", "FT%": ".800", "PTS": "150",
                     "REB": "60", "AST": "35", "ST": "10", "BLK": "5", "TO": "15"},
                    {"team_name": "Brian", "W": "4", "L": "5", "T": "0",
                     "AdjFG%": "0.490", "3PTM": "10", "FT%": ".750", "PTS": "140",
                     "REB": "55", "AST": "30", "ST": "8", "BLK": "7", "TO": "18"},
                ]
            },
            "2": {
                "rows": [
                    {"team_name": "Sick-Os Revenge", "W": "3", "L": "6", "T": "0",
                     "AdjFG%": "0.500", "3PTM": "14", "FT%": ".780", "PTS": "145",
                     "REB": "58", "AST": "32", "ST": "12", "BLK": "4", "TO": "17"},
                ]
            },
        }

    def test_team_historical_cats(self, sample_matchup_history):
        result = team_historical_cats(sample_matchup_history, "Sick-Os Revenge")
        assert len(result) == 2
        assert result[0]["period"] == 1
        assert result[1]["period"] == 2
        assert result[0]["cats"]["PTS"] == 150.0
        assert result[0]["W"] == 5

    def test_team_category_ranks(self, sample_matchup_history):
        ranks = team_category_ranks(sample_matchup_history, period=1)
        assert "Sick-Os Revenge" in ranks
        assert "Brian" in ranks
        # Sick-Os has higher PTS (150 vs 140) → rank 1
        assert ranks["Sick-Os Revenge"]["PTS"] == 1
        assert ranks["Brian"]["PTS"] == 2

    def test_to_rank_lower_is_better(self, sample_matchup_history):
        ranks = team_category_ranks(sample_matchup_history, period=1)
        # Sick-Os has 15 TO (lower = better), Brian has 18
        assert ranks["Sick-Os Revenge"]["TO"] == 1
        assert ranks["Brian"]["TO"] == 2


# ── Schedule helpers ───────────────────────────────────────────────────

class TestGetPlayerGamesInPeriod:
    def test_basic(self):
        cl1 = PlayerCatLine(
            name="Player1", team="Dayton", games=20, mpg=30,
            tpm_pg=1, pts_pg=15, reb_pg=5, ast_pg=3, stl_pg=1, blk_pg=0.5, to_pg=2,
            adj_fg_pct=0.5, ft_pct=0.8,
        )
        cl2 = PlayerCatLine(
            name="Player2", team="Loyola Chicago", games=20, mpg=25,
            tpm_pg=2, pts_pg=12, reb_pg=4, ast_pg=2, stl_pg=0.5, blk_pg=0.3, to_pg=1.5,
            adj_fg_pct=0.45, ft_pct=0.75,
        )
        schedule = {
            "15": {
                "games_per_team": {"Dayton": 2, "Loyola Chicago": 4},
            }
        }
        result = get_player_games_in_period([cl1, cl2], schedule, 15)
        assert result["Player1"] == 2
        assert result["Player2"] == 4


# ── Data quality ───────────────────────────────────────────────────────

class TestDataQuality:
    def test_pts_formula_check(self):
        # Correct: PTS = 2*(FGM-3PM) + 3*3PM + FTM = 2*70 + 3*30 + 50 = 280
        good = [_make_player("Good", pts=280)]
        report = run_player_data_quality(good)
        pts_check = next(c for c in report.checks if "PTS =" in c["name"])
        assert pts_check["passed"]

    def test_pts_formula_catches_mismatch(self):
        bad = [_make_player("Bad", pts=999)]  # wrong
        report = run_player_data_quality(bad)
        pts_check = next(c for c in report.checks if "PTS =" in c["name"])
        assert not pts_check["passed"]

    def test_fgm_lte_fga(self):
        bad = [_make_player("Bad", fgm=200, fga=100)]
        report = run_player_data_quality(bad)
        check = next(c for c in report.checks if "FGM <= FGA" in c["name"])
        assert not check["passed"]


# ── Aggregate boxscores ───────────────────────────────────────────────

def _make_boxscore_row(
    first_name="Test", last_name="Player", team="Dayton", date="2025-01-15",
    position="G", minutes=30, fgm=5, fga=10, ftm=2, fta=3, tpm=1, tpa=3,
    oreb=1, reb=5, ast=3, stl=1, blk=0, to=2, pf=2, pts=13, game_id="1",
):
    return {
        "game_id": game_id, "date": date, "team": team,
        "first_name": first_name, "last_name": last_name,
        "position": position, "minutes": minutes,
        "fgm": fgm, "fga": fga, "ftm": ftm, "fta": fta,
        "tpm": tpm, "tpa": tpa, "oreb": oreb, "reb": reb,
        "ast": ast, "to": to, "stl": stl, "blk": blk, "pf": pf, "pts": pts,
    }


@pytest.fixture
def sample_boxscore_rows():
    """Synthetic boxscore rows for 2 players across 4 games each."""
    return [
        # Player A - 4 games
        _make_boxscore_row("Alice", "Alpha", "Dayton", "2025-01-10", fgm=6, fga=12, ftm=3, fta=4, tpm=2, tpa=5, reb=8, ast=4, stl=2, blk=1, to=3, pts=17, game_id="g1"),
        _make_boxscore_row("Alice", "Alpha", "Dayton", "2025-01-12", fgm=4, fga=10, ftm=2, fta=2, tpm=1, tpa=3, reb=6, ast=3, stl=1, blk=0, to=2, pts=11, game_id="g2"),
        _make_boxscore_row("Alice", "Alpha", "Dayton", "2025-01-14", fgm=8, fga=15, ftm=4, fta=5, tpm=3, tpa=6, reb=10, ast=5, stl=3, blk=2, to=1, pts=23, game_id="g3"),
        _make_boxscore_row("Alice", "Alpha", "Dayton", "2025-01-16", fgm=5, fga=11, ftm=1, fta=2, tpm=2, tpa=4, reb=7, ast=2, stl=0, blk=1, to=4, pts=13, game_id="g4"),
        # Player B - 4 games
        _make_boxscore_row("Bob", "Beta", "VCU", "2025-01-10", fgm=3, fga=8, ftm=1, fta=2, tpm=0, tpa=1, reb=12, ast=1, stl=0, blk=3, to=1, pts=7, game_id="g1"),
        _make_boxscore_row("Bob", "Beta", "VCU", "2025-01-12", fgm=4, fga=9, ftm=2, fta=3, tpm=1, tpa=2, reb=10, ast=2, stl=1, blk=2, to=2, pts=11, game_id="g2"),
        _make_boxscore_row("Bob", "Beta", "VCU", "2025-01-14", fgm=2, fga=7, ftm=0, fta=0, tpm=0, tpa=1, reb=14, ast=0, stl=0, blk=4, to=0, pts=4, game_id="g3"),
        _make_boxscore_row("Bob", "Beta", "VCU", "2025-01-16", fgm=5, fga=10, ftm=3, fta=4, tpm=2, tpa=3, reb=8, ast=3, stl=2, blk=1, to=3, pts=15, game_id="g4"),
    ]


class TestAggregateBoxscores:
    def test_all_games(self, sample_boxscore_rows):
        result = aggregate_boxscores(sample_boxscore_rows)
        assert len(result) == 2
        alice = next(p for p in result if p["name"] == "Alice Alpha")
        assert alice["games"] == 4
        assert alice["team"] == "Dayton"
        assert alice["fgm"] == 6 + 4 + 8 + 5  # 23
        assert alice["pts"] == 17 + 11 + 23 + 13  # 64
        assert alice["ppg"] == round(64 / 4, 1)

    def test_last_n(self, sample_boxscore_rows):
        result = aggregate_boxscores(sample_boxscore_rows, last_n_games=2)
        assert len(result) == 2
        alice = next(p for p in result if p["name"] == "Alice Alpha")
        # Last 2 games by date desc: Jan 16 and Jan 14
        assert alice["games"] == 2
        assert alice["fgm"] == 8 + 5  # g3 + g4
        assert alice["pts"] == 23 + 13  # g3 + g4

    def test_schema(self, sample_boxscore_rows):
        result = aggregate_boxscores(sample_boxscore_rows)
        required_keys = {
            "name", "team", "position", "games", "total_minutes",
            "fgm", "fga", "ftm", "fta", "tpm", "tpa",
            "reb", "ast", "stl", "blk", "to", "pts", "pf",
            "ppg", "rpg", "apg", "spg", "bpg", "topg", "tpm_pg", "mpg",
            "fg_pct", "ft_pct", "tp_pct", "efg_pct",
        }
        for p in result:
            missing = required_keys - set(p.keys())
            assert not missing, f"Missing keys for {p['name']}: {missing}"

    def test_plugs_into_cat_line(self, sample_boxscore_rows):
        """Verify output works with player_to_cat_line and compute_z_scores."""
        result = aggregate_boxscores(sample_boxscore_rows)
        for p in result:
            cl = player_to_cat_line(p)
            assert cl.name == p["name"]
            assert cl.games == p["games"]

    def test_empty_input(self):
        result = aggregate_boxscores([])
        assert result == []

    def test_last_n_greater_than_games(self, sample_boxscore_rows):
        """last_n_games > actual games should return all games."""
        result = aggregate_boxscores(sample_boxscore_rows, last_n_games=100)
        alice = next(p for p in result if p["name"] == "Alice Alpha")
        assert alice["games"] == 4


# ── Integration: load real data if available ───────────────────────────

class TestWithRealData:
    """Tests that load actual data files. Skipped if files don't exist."""

    @pytest.fixture
    def real_players(self):
        from pathlib import Path
        path = Path(__file__).parent.parent / "data" / "a10_players.json"
        if not path.exists():
            pytest.skip("a10_players.json not found")
        import json
        with open(path) as f:
            return json.load(f)

    @pytest.fixture
    def real_rosters(self):
        from pathlib import Path
        path = Path(__file__).parent.parent / "data" / "fantrax_rosters.json"
        if not path.exists():
            pytest.skip("fantrax_rosters.json not found")
        import json
        with open(path) as f:
            return json.load(f)

    def test_real_data_quality(self, real_players):
        report = run_player_data_quality(real_players)
        for check in report.checks:
            if not check["passed"]:
                print(f"  WARN: {check['name']}: {check['detail']}")
        # At minimum, basic checks should pass
        assert len(real_players) >= 200

    def test_real_z_scores(self, real_players):
        results = compute_z_scores(real_players)
        assert len(results) > 50  # Should have plenty of qualified players
        # Top composite should be reasonable
        composites = [(r["name"], composite_z_score(r["z_scores"])) for r in results]
        composites.sort(key=lambda x: x[1], reverse=True)
        top_name, top_z = composites[0]
        assert top_z > 0, f"Top player {top_name} has negative composite z"
        assert top_z < 20, f"Top player {top_name} has suspiciously high z: {top_z}"

    def test_real_roster_matching(self, real_players, real_rosters):
        lookup = build_player_lookup(real_players)
        total = 0
        matched = 0
        for team_name, team_data in real_rosters.items():
            for fp in team_data.get("players", []):
                total += 1
                ncaa = match_player(fp["name"], fp.get("team", ""), lookup, real_players)
                if ncaa:
                    matched += 1
                else:
                    print(f"  Unmatched: {fp['name']} ({fp.get('team', 'N/A')})")
        match_rate = matched / total if total > 0 else 0
        assert match_rate >= 0.85, f"Match rate too low: {match_rate:.1%} ({matched}/{total})"
