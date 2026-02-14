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
| `tests/test_ncaa_client.py` | 14 tests for NCAA client | 14/14 passing |
| `tests/test_fantrax_client.py` | 17 tests for FanTrax client | 17/17 passing |
| `tests/test_schedule_scanner.py` | 6 tests for schedule scanner | 6/6 passing |

### Infrastructure:
- NCAA API running locally via Docker on port 3000 (unlimited requests)
- UV-managed Python project with all dependencies
- Git repo initialized

### Data collected (all cached in `data/`):

| File | Contents |
|------|----------|
| `a10_standings.json` | A-10 conference standings (14 teams) |
| `a10_players.csv/json` | 68 A-10 players with merged stats (PTS, REB, AST, STL, BLK, 3PM, FGM, FGA, FT, FTA, FG%, FT%, eFG%) |
| `a10_team_stats.json` | 14 team stat categories for all A-10 teams |
| `a10_schedule.json` | Game schedules for Periods 14-17 with games-per-team counts |
| `fantrax_standings.json` | League standings (8 teams with W/L/T) |
| `fantrax_rosters.json` | All 8 team rosters with player details |
| `fantrax_all_matchups.json` | Category-level matchup results for all 14 periods |
| `fantrax_matchups.json` | Recent matchup data (periods 13-14) |

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

## Phase 2: Analysis - TODO

#### 2a. Build fantasy value model
- Map real NCAA stats to the 9 fantasy categories
- Calculate per-game production for every A-10 player across all categories
- Factor in schedule (games per week) to project weekly totals
- Rank all A-10 players by category contributions

#### 2b. Roster analysis - our team
- Profile our roster's category strengths and weaknesses
- Identify which categories we're competitive in and which we're losing
- Calculate our team's projected weekly totals in each category

#### 2c. Opponent analysis
- Profile every other playoff team's roster the same way
- Identify opponent weaknesses we can exploit
- For our Round 1 opponent specifically: which 5 categories can we realistically win?

#### 2d. Waiver wire analysis
- Rank all 156 free agents by fantasy value
- Cross-reference with schedule (prioritize players on teams with more games)
- Identify category-specific pickups (e.g., "best available rebounder on the wire")

#### 2e. Free agent vs. roster comparison
- For each roster spot, compare our current player vs. best available replacement
- Identify clear upgrades on the wire
- Model the impact of each swap on our category projections

### Phase 3: Strategy & Recommendations - TODO

#### 3a. Category targeting strategy
- Based on our roster + available pickups, recommend which 5 categories to target
- Identify 1-2 categories to punt
- This may shift per opponent in each playoff round

#### 3b. Waiver wire action plan
- Prioritized list of claims with recommended bid amounts
- Which of our players to drop for each claim
- Timing considerations (daily processing at 11am EST)

#### 3c. Lineup optimization
- Optimal active lineup for each day of the playoff period
- Factor in GP limits - don't burn all games early in the week
- Streaming plan: which players to rotate in/out day-by-day

#### 3d. Multi-round planning
- Round 1 strategy (must-win)
- Contingency plans for Rounds 2-3 based on likely opponents
- Budget allocation across rounds (don't blow entire $100 in Round 1)

---

## Tools We'll Build

| Script | Purpose | Status |
|--------|---------|--------|
| `src/fantrax_client.py` | Authenticated FanTrax API client + public API free agent search | Done |
| `src/ncaa_client.py` | NCAA API client (hitting local Docker instance) | Done |
| `src/collect_data.py` | Pull and cache all data from both APIs | Done |
| `src/schedule_scanner.py` | A-10 game schedule for playoff periods | Done |
| `src/player_rankings.py` | Fantasy value model - rank all A-10 players | TODO |
| `src/roster_analyzer.py` | Analyze team rosters, strengths, weaknesses | TODO |
| `src/waiver_optimizer.py` | Recommend waiver claims and drops | TODO |
| `src/lineup_optimizer.py` | Optimal daily lineups considering GP limits | TODO |
| `src/matchup_analyzer.py` | Head-to-head category projections vs. opponents | TODO |

All data cached locally (CSV/JSON) so we don't have to re-pull constantly.
