# Fantasy Tools — A-10 Basketball

## What This Is

An experiment in using AI-assisted data analysis (Claude Code) to compete in fantasy sports — specifically, to see if walking into the playoffs with a last-place team and a systematic analytical approach can produce real results.

The league is an A-10 conference college basketball league on FanTrax, part of a two-league system with promotion/relegation. The regular season wasn't a priority this year (work got in the way), so we're heading into the playoffs as the 8th seed with a 37-85-4 record. The only lever left is the daily waiver wire.

The goal: build tools and workflows that surface edges a busy manager would miss — schedule exploitation, category targeting, swap impact modeling — and see if they translate into actual playoff wins. Everything here was built during the playoff push, not before it.

Daily analysis logs live in `analysis/` to track what the models projected vs. what actually happened.

## League Format

8-team H2H categories league on FanTrax. 9 cats: AdjFG%, 3PTM, FT%, PTS, REB, AST, ST, BLK, TO. Win 5 of 9 each week.

Team: **Sick-Os Revenge** (8th seed). Playoffs: Periods 15-17 (Feb 16 - Mar 8). Top 2 seeds auto-promoted, seeds 3-4 get R1 byes, seeds 5-8 play in. Daily waiver wire, $100 budget across 3 rounds.

## Quick Start

Prerequisites: Python 3.13+, [uv](https://docs.astral.sh/uv/)

```bash
# Install dependencies
uv sync

# Launch the TUI
uv run fantasy
```

The TUI provides a keyboard-driven interface for daily workflows. Press `?` at any time for help. See [Keybindings](#keybindings) below.

### Configuration

Edit `config.toml` at the project root to set your team name, scoring categories, period dates, and GP limits. The TUI reads this file on startup.

## Refresh Data

Run before every analysis session. Pulls latest player stats, rosters, schedule, and matchup history.

```bash
# From the TUI: press d to open the Data Refresh screen, then click Start Collection
# Or from the command line:
uv run python src/collect_data.py
```

## TUI Workflows

### Check your matchup

1. Press `d` to refresh data (if needed)
2. Press `m` to open the Matchup Dashboard
3. Select a scoring period and opponent from the dropdowns
4. Review the 9-category H2H comparison — green = winning, red = losing
5. Check the all-opponents overview to see your projected record vs the field
6. Identify swing categories (small margins) to target with waiver moves

### Evaluate waivers

1. Press `w` to open the Waiver Optimizer
2. Select a scoring period
3. Browse the FA rankings table (sorted by schedule-adjusted z-score)
4. Check "Best Available Per Category" for targeted pickups
5. Use the Swap Simulator: select a drop candidate and a FA to add
6. Compare before/after projected category totals to evaluate the swap

### Optimize your lineup

1. Press `l` to open the Lineup Optimizer
2. Select the period and adjust GP Max if needed
3. Review the game calendar to see who plays when
4. Check the GP budget tracker — if over budget, benching is needed
5. Follow the optimal daily lineup plan (highest-z players started first)
6. Check streaming recommendations for days with open roster spots

### Scout player rankings

1. Press `r` to open Player Rankings
2. Adjust Min GP, Min MPG filters to focus on qualified players
3. Sort by Composite Z, Schedule-Adjusted Z, or any individual category
4. Use per-category z-scores to find specialists for swing categories

### Analyze your roster

1. Press `t` to open Roster Analysis
2. Select a scoring period
3. Review per-game stats and projected games for each player
4. Check category ranks (1-8) — green = strength, red = weakness
5. Use weaknesses to identify categories to target on waivers

## Notebook Analysis Workflow

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

## Keybindings

| Key | Screen |
|-----|--------|
| `d` | Data Refresh |
| `m` | Matchup Dashboard |
| `r` | Player Rankings |
| `t` | Roster Analysis |
| `w` | Waiver Optimizer |
| `l` | Lineup Optimizer |
| `?` | Help overlay |
| `q` | Quit |
