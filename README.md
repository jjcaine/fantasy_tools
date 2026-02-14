# Fantasy Tools — A-10 Basketball

## What This Is

An experiment in using AI-assisted data analysis (Claude Code) to compete in fantasy sports — specifically, to see if walking into the playoffs with a last-place team and a systematic analytical approach can produce real results.

The league is an A-10 conference college basketball league on FanTrax, part of a two-league system with promotion/relegation. The regular season wasn't a priority this year (work got in the way), so we're heading into the playoffs as the 8th seed with a 37-85-4 record. The only lever left is the daily waiver wire.

The goal: build tools and workflows that surface edges a busy manager would miss — schedule exploitation, category targeting, swap impact modeling — and see if they translate into actual playoff wins. Everything here was built during the playoff push, not before it.

Daily analysis logs live in `analysis/` to track what the models projected vs. what actually happened.

## League Format

8-team H2H categories league on FanTrax. 9 cats: AdjFG%, 3PTM, FT%, PTS, REB, AST, ST, BLK, TO. Win 5 of 9 each week.

Team: **Sick-Os Revenge** (8th seed). Playoffs: Periods 15-17 (Feb 16 - Mar 8). Top 2 seeds auto-promoted, seeds 3-4 get R1 byes, seeds 5-8 play in. Daily waiver wire, $100 budget across 3 rounds.

## Setup

```
uv sync
```

## Refresh Data

Run before every analysis session. Pulls latest player stats, rosters, schedule, and matchup history.

```
uv run python src/collect_data.py
```

## Playoff Analysis Workflow

### 1. Roster Analyzer — "What do we have?"

```
marimo edit notebooks/roster_analyzer.py
```

- Confirm all players matched (check data quality section)
- Note any injuries (injured players = drop candidates)
- **Team vs League rankings** — identify your top 5 cats and punt cats
- Category strategy recommendation frames every decision that follows

### 2. Matchup Analyzer — "What do we need to win?"

```
marimo edit notebooks/matchup_analyzer.py
```

- **All opponents overview** — projected record against every team
- **H2H vs current opponent** — which 5 cats are you winning?
- **Win path** — cats sorted by margin, shows the easiest path to 5 wins
- Swing cats (close margins) are where waiver moves matter most

### 3. Waiver Optimizer — "Who do we pick up?"

```
marimo edit notebooks/waiver_optimizer.py
```

- Set **category focus** to swing cats from the matchup win path
- **Roster upgrade analysis** — find your weakest link
- **Swap simulator** — test drop/add combos, see projected impact per cat
- **Bid recommendations** — budget heuristic: ~$50 R1, ~$30 R2, ~$20 R3
- Injured players are first drop candidates

### 4. Lineup Optimizer — "Who do we start?"

```
marimo edit notebooks/lineup_optimizer.py
```

- **Game calendar** — who plays when this period
- **GP tracker** — 15 GP max, check if benching is needed
- **Optimal daily lineup** — greedy by z-score value
- **Streaming slots** — days with <6 active players = pickup opportunities

### 5. Player Rankings — Reference

```
marimo edit notebooks/player_rankings.py
```

- Schedule-adjusted composite rankings for the current period
- Sort by specific category z-scores when targeting swing cats
- Top 10 per category for quick reference

## During Each Playoff Round

1. Refresh data daily (`uv run python src/collect_data.py`)
2. Check lineup optimizer for start/sit decisions
3. If a streaming slot opens, check waiver optimizer for best available
4. Before R2/R3 waivers, re-run matchup analyzer against the next opponent

## Critical Path

**Roster analyzer → Matchup analyzer → Waiver optimizer**

What you're good at → What you need to win → Who to pick up.
