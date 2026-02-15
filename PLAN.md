# Fantasy Basketball Championship Plan

## Situation Assessment

- **League**: A10 Fantasy (FanTrax league ID: `l6r9clmimgohg3yp`)
- **Team**: Sick-Os Revenge (team ID: `0hj8uid0mgohg3yt`)
- **Format**: H2H Each Category, 8 teams
- **Scoring Categories (9)**: PTS, REB, AST, STL, BLK, 3PTM, TO, AdjFG%, FT%
  - All weighted equally (1 each). Win a category = 1 win, lose = 1 loss.
  - Each matchup is effectively 9 mini-contests. Win 5+ categories to win the week.
  - **TO is inverse** (lower is better). **AdjFG% and FT% are percentages** (volume matters for leverage).
  - **AdjFG%** = (FGM + 0.5 × 3PM) / FGA — standard eFG% (Effective Field Goal %)
- **Player Pool**: A-10 conference teams only (14 teams: Davidson, Dayton, Duquesne, Fordham, George Mason, George Washington, La Salle, URI, Richmond, St. Bonaventure, St. Joseph's, Saint Louis, VCU, Loyola Chicago)
- **Current Standing**: 8th (last place, 37-85-4 through 14 periods)
- **Playoffs**: Start Period 15 (Mon Feb 16 - Sun Feb 22). Three rounds total, ending Period 17 (Mar 8).
- **Playoff Structure**: Top 2 regular season finishers are NOT in playoffs (auto-promoted). Seeds 3-4 get first-round byes. Seeds 5-8 play Round 1. All rounds are 1 week.
- **Trade Deadline**: Passed (Feb 11). **No trades possible.**
- **Waiver Wire**: Daily bidding at 11am EST, $100 budget (full budget available, nothing spent), $1 minimum bid. This is our ONLY lever.
- **Roster**: 6 active (all Flex), max 8 total players, 15 GP max per scoring period.

## Strategic Framework

### Key Insight: Category Targeting
In H2H categories, you don't need to be the best at everything. You need to **win 5 out of 9 categories** each week. The optimal strategy is to:
1. Identify which categories you can realistically dominate
2. Punt (sacrifice) 1-2 categories entirely
3. Stack your roster to guarantee wins in your target categories

### Key Insight: Volume vs. Efficiency
- **Counting stats** (PTS, REB, AST, STL, BLK, 3PTM): More games played = more stats. **Streaming matters.**
- **Percentage cats** (AdjFG%, FT%): Quality over quantity, but having more attempts gives you a more stable percentage.
- **TO**: Fewer games = fewer turnovers. But you still need to play guys for counting stats. Target low-TO players.

### Key Insight: Schedule Exploitation
A-10 teams don't all play the same number of games each week. Teams with **more games in a scoring period** give you more counting stats. We need to know the A-10 schedule for Periods 15-17.

---

## Phase 1: Infrastructure & Data Collection - COMPLETE

### What was built:

| File | Purpose | Status |
|------|---------|--------|
| `src/ncaa_client.py` | NCAA API client (local Docker) with verified stat endpoint IDs | Done |
| `src/fantrax_client.py` | FanTrax API client - authenticated (Selenium cookies) + public API (fxea) | Done |
| `src/collect_data.py` | Data collection orchestrator | Done |
| `src/schedule_scanner.py` | A-10 game schedule scanner using scoreboard API | Done |
| `src/boxscore_collector.py` | Boxscore data collection from NCAA API | Done |
| `src/fantasy_math.py` | Core analytics engine — z-scores, projections, swap simulations | Done |
| `tests/test_ncaa_client.py` | 14 tests for NCAA client | 14/14 passing |
| `tests/test_fantrax_client.py` | 17 tests for FanTrax client | 17/17 passing |
| `tests/test_schedule_scanner.py` | 6 tests for schedule scanner | 6/6 passing |
| `tests/test_fantasy_math.py` | Tests for fantasy math engine | Done |

### Infrastructure:
- NCAA API running locally via Docker on port 3000 (unlimited requests)
- UV-managed Python project with all dependencies
- Git repo initialized

### Data collected (all cached in `data/`):

| File | Contents |
|------|----------|
| `a10_standings.json` | A-10 conference standings (14 teams) |
| `a10_players.csv/json` | A-10 players with merged stats (PTS, REB, AST, STL, BLK, 3PM, FGM, FGA, FT, FTA, FG%, FT%, eFG%) |
| `a10_team_stats.json` | 14 team stat categories for all A-10 teams |
| `a10_schedule.json` | Game schedules for Periods 14-17 with games-per-team counts |
| `a10_all_games.json` | Full A-10 game listing |
| `a10_boxscores_raw.json` | Raw boxscore data for all A-10 games |
| `fantrax_rosters.json` | All 8 team rosters with player details |
| `fantrax_all_matchups.json` | Category-level matchup results for all 14 periods |

### Key discoveries:
- **Waiver wire solved**: FanTrax public API (`fxea/general/getLeagueInfo` + `getPlayerIds`) gives us full free agent list with player names, teams, positions, and FA/WW status. No auth needed. **156 free agents available.**
- NCAA individual stat endpoints only return nationally-ranked players (top N), so some categories have fewer A-10 players. PPG (136) is the richest endpoint with FGM, 3FG, FT, PTS for 57 players.
- The `fantraxapi` library has bugs with H2H categories format (matchup parsing) and transaction date parsing. Worked around both with raw API calls and public API.

### Season schedule data for playoff periods:

| Period | Dates | Teams with most games |
|--------|-------|----------------------|
| 15 (R1) | Feb 16-22 | **Loyola Chicago: 4 games**; most teams: 2; George Mason/GW: 1 |
| 16 (R2) | Feb 23-Mar 1 | **Loyola Chicago: 3 games**; most teams: 2; Fordham/Richmond/VCU: 1 |
| 17 (R3) | Mar 2-8 | All teams: 2 games |

---

## Phase 2: Analysis Tools - COMPLETE

All analysis tools were built as interactive Marimo notebooks (not standalone scripts). The core math lives in `src/fantasy_math.py`.

| Notebook | Purpose | Status |
|----------|---------|--------|
| `notebooks/roster_analyzer.py` | Team strengths/weaknesses, category z-score profile | Done |
| `notebooks/matchup_analyzer.py` | H2H category projections vs all opponents, win path analysis | Done |
| `notebooks/waiver_optimizer.py` | Swap simulations, category-focused FA search, bid recommendations | Done |
| `notebooks/lineup_optimizer.py` | Daily start/sit decisions, GP tracking, streaming slot detection | Done |
| `notebooks/player_rankings.py` | Schedule-adjusted composite rankings, per-category top 10 | Done |

Covers all originally planned analysis work:
- **2a. Fantasy value model** → `fantasy_math.py` z-score engine + `player_rankings.py` notebook
- **2b. Roster analysis** → `roster_analyzer.py` notebook
- **2c. Opponent analysis** → `matchup_analyzer.py` notebook
- **2d. Waiver wire analysis** → `waiver_optimizer.py` + `player_rankings.py` notebooks
- **2e. Free agent vs. roster comparison** → `waiver_optimizer.py` swap simulator

---

## Phase 3: Strategy & Recommendations - IN PROGRESS

Daily analysis logs live in `analysis/` to track projections vs. actual results.

#### 3a. Category targeting strategy - COMPLETE (for R1)
- **Target cats**: PTS, REB, AST, ST, 3PTM, FT%, BLK (win 7)
- **Punt cats**: AdjFG%, TO
- Will re-evaluate per opponent in R2/R3

#### 3b. Waiver wire action plan - COMPLETE (for R1)
- **Move 1**: Drop Tyrell Ward (-4.03) → Pick up Braeden Speed (+5.02, Loyola 4G) — **Bid $50**
- **Move 2**: Drop Jerome Brewer Jr. (DTD) → Pick up Jordan Stiemke (+2.41, Loyola 4G) — **Bid $25-30**
- Projected result vs Fordham: **7-2 win** (up from 4-5 baseline)
- Budget remaining after R1: ~$20-25 for R2/R3

#### 3c. Lineup optimization - TODO
- Set daily lineups once R1 starts (Feb 16)
- GP management: 20 potential GP with Loyola pickups, only 15 allowed — need sit strategy
- Prioritize full games from Speed, Stiemke, Mitchell, Hinton, Bowen, Henry

#### 3d. Multi-round planning - TODO
- R2/R3 opponent scouting (likely Nishy Baby or Back to Big East if we advance)
- Budget re-allocation based on R1 spend
- Re-run matchup analyzer against next opponent after R1

---

## Phase 4: Recency-Weighted Evaluation - TODO

### Rationale

All current analysis uses full-season averages. But A-10 rosters are full of portal transfers who need time to gel, and non-conference play (Nov-Dec) is weaker competition. Ad-hoc analysis showed meaningful early vs late splits:

- **Speed**: +4.9 PPG, +1.3 RPG, +1.1 3PM recently — our #1 target looks even better
- **Stiemke**: -3.3 PPG, -1.0 3PM, FT% .900→.833 — his case for flipping FT% weakens
- **Hinton** (our guy): -5.8 PPG, FT% .855→.556 — concerning regression
- **Dixon** (FA): +3.1 PPG, +1.6 RPG, BPG 0.9→1.9 — potential BLK category flipper
- **Mitchell** (our best player): -3.6 PPG, -3.7 RPG — still good but regressing

This could change the optimal waiver strategy. Stiemke's declining FT% is the swing — it's the category that flips our R1 matchup from 4-5 to 7-2 by a margin of +.003. If his recent FT% is more predictive, that margin may not hold.

### 4a. Add `aggregate_boxscores()` to `src/fantasy_math.py`

New function that re-aggregates raw boxscore rows (already collected in `data/a10_boxscores_raw.json`) with a configurable `last_n_games` filter. Returns player dicts in the same schema as `load_a10_players()` so all existing z-score, projection, and matchup code works unchanged.

### 4b. New notebook: `notebooks/recency_analysis.py`

Interactive Marimo notebook with:
- **Controls**: Slider for last N games (5-25, default 10), period selector
- **Player split comparison**: Full-season vs last-N side-by-side for our roster + top waiver targets, with deltas highlighted
- **Z-score comparison**: Rankings from both pools, surface players whose recent form diverges most from season average
- **Matchup re-simulation**: R1 vs Fordham using recency stats for both teams — does the 4-5 baseline still hold? Do the swap scenarios change?
- **Waiver target re-ranking**: Free agents ranked by recency-adjusted composite — do Speed and Stiemke still come out on top?

---

## Workflow (README)

```
uv run python src/collect_data.py    # refresh data daily
marimo edit notebooks/<notebook>.py   # run any analysis notebook
```

**Critical path**: Roster analyzer → Matchup analyzer → Waiver optimizer

All data cached locally (CSV/JSON) so we don't have to re-pull constantly.
