# Period 15 Streaming Pickup Analysis - February 16, 2026

**Team:** Sick-Os Revenge
**Matchup:** vs Boardwalk Hall is on Fire (Playoff Round 1, P15: Feb 16-22)
**Constraint:** Must win. 5-4 is the only acceptable outcome — no path through a loss.

---

## Situation

Roster has 8 players but a severe schedule imbalance:

| Day | Date | Roster Players Playing | Empty Active Slots (of 6) |
|-----|------|----------------------|--------------------------|
| Tue | 2/17 | 1 (Hinton) | 5 |
| Wed | 2/18 | 7 (must bench 1) | 0 |
| Fri | 2/20 | 0 | 6 |
| Sat | 2/21 | 8 (must bench 2) | 0 |

Tuesday and Friday are almost completely wasted. Two streaming spots are open, and Jerome Brewer (day-to-day) can move to IR to free a roster slot.

---

## Schedule Targets

Only two teams play on **both** Tue 2/17 and Fri 2/20 — the two gap days:

| Team | Game 1 | Game 2 |
|------|--------|--------|
| **Saint Louis** | Tue 2/17 (vs Rhode Island) | Fri 2/20 (vs VCU) |
| **VCU** | Tue 2/17 (vs George Washington) | Fri 2/20 (@ Saint Louis) |

Pickups from these teams yield 2 games each on otherwise-empty days.

---

## Free Agent Rankings (VCU + Saint Louis)

| Player | Team | GP | MPG | Comp Z | BLK | REB | TO | FT% | AdjFG% | Target Z |
|--------|------|----|-----|--------|-----|-----|----|-----|--------|----------|
| **Dion Brown** | Saint Louis | 25 | 23.3 | **+6.86** | -0.1 | +2.1 | -1.5 | +0.5 | +1.8 | +2.8 |
| **Jadrian Tracey** | VCU | 26 | 22.9 | **+5.78** | +0.2 | +0.2 | -2.0 | +0.2 | +0.5 | -0.9 |
| Brady Dunlap | Saint Louis | 24 | 17.5 | +4.09 | -0.8 | -0.1 | +0.1 | +1.1 | +1.4 | +1.7 |
| Michael Belle | VCU | 26 | 21.5 | +4.01 | +1.5 | +1.5 | +0.1 | -1.2 | +1.4 | +3.3 |

Brown and Tracey are the top two by composite z-score and are high-minute starters (23+ MPG, 25+ GP). Both contribute steals (+0.9 each) and assists (+1.0/+1.1).

Brown is especially strong in target cats: +2.1 REB, +1.8 AdjFG%, +0.5 FT%.

Tracey's TO z-score is -2.0 (high turnovers) — this is a real concern analyzed in depth below.

---

## Current Matchup: Full 9-Category Breakdown

### Status Quo (No Moves) — Projected 5-4 WIN

| Category | Us | Them | Margin | Result |
|----------|---:|-----:|-------:|--------|
| AdjFG% | .537 | .536 | **+.000** | WIN |
| 3PTM | 15.4 | 21.2 | -5.8 | LOSE |
| FT% | .769 | .760 | **+.009** | WIN |
| PTS | 161.0 | 178.2 | -17.2 | LOSE |
| REB | 65.6 | 62.2 | +3.4 | WIN |
| AST | 29.2 | 41.8 | -12.6 | LOSE |
| ST | 10.4 | 16.8 | -6.4 | LOSE |
| BLK | 6.6 | 1.8 | +4.8 | WIN |
| TO | 22.2 | 22.8 | **+0.6** | WIN |

**Winning (5):** AdjFG%, FT%, REB, BLK, TO
**Losing (4):** 3PTM, PTS, AST, ST

**Risk assessment:** 3 of 5 wins are on a knife's edge:
- AdjFG%: +.000 — essentially a coin flip
- FT%: +.009 — one bad free throw shooting night could flip it
- TO: +0.6 — less than one turnover of margin

All three must hold for a full week to win 5-4. If *any one* slips, we lose the matchup.

---

## Drop Analysis

Brewer moves to IR. Need to drop 1 player to open a second roster slot.

Simulated each drop (adding both Brown + Tracey) and projected result vs Boardwalk:

| Drop | Result vs Boardwalk | BLK | REB | TO | FT% | AdjFG% |
|------|-------------------|-----|-----|-----|-----|--------|
| **John Hugley IV** | **5-4 WIN** | +1.0 | +8.2 | +3.8 | -0.002 | +0.011 |
| Hunter Adam | 5-4 WIN | +0.8 | +13.0 | +6.6 | -0.008 | +0.004 |
| Alex Williams | 4-5 LOSS | +1.2 | +11.0 | +6.0 | -0.016 | +0.012 |
| Dasonte Bowen | 4-5 LOSS | +1.4 | +11.0 | +3.8 | -0.024 | +0.021 |
| Joseph Grahovac | 4-5 LOSS | -2.0 | +10.8 | +5.6 | -0.010 | +0.007 |
| Frank Mitchell | 4-5 LOSS | +0.2 | -2.6 | +2.4 | +0.016 | +0.012 |
| Jonah Hinton | 3-6 LOSS | +1.0 | +10.8 | +3.2 | -0.015 | +0.019 |

Only Hugley or Adam preserve the 5-4. **Hugley is the best drop** — his negative FT% and AdjFG% z-scores hurt two target cats, while Adam's +2.04 AdjFG% z-score is too valuable in a matchup where AdjFG% is a swing category.

---

## Turnover Concern: Deep Dive

Tracey's -2.0 TO z-score is the biggest risk in the streaming plan. With a current TO margin of only +0.6, can we afford to add a high-turnover player?

### Alternative VCU/Saint Louis Pickups (with Brown)

| Second Pickup | Overall | TO Margin | FT% Margin | AdjFG% Margin | PTS Margin |
|---------------|---------|-----------|------------|---------------|------------|
| **Jadrian Tracey** | **5-4 WIN** | **-3.2 LOSE** | +.008 WIN | +.011 WIN | +4.6 WIN |
| Michael Belle | 3-6 LOSS | -0.8 LOSE | -.009 LOSE | +.017 WIN | — |
| Brady Dunlap | 4-5 LOSS | -0.8 LOSE | +.021 WIN | +.017 WIN | — |
| Ahmad Nowell | 4-5 LOSS | -0.2 LOSE | +.014 WIN | +.014 WIN | — |

**Key finding:** Every alternative also loses TO — adding any extra games generates more turnovers. But the TO-friendly options (Belle, Dunlap, Nowell) lose the overall matchup because they don't produce enough counting stats to compensate. Belle tanks FT% below Boardwalk's, flipping that category.

Tracey is the only second pickup that projects 5-4.

---

## The Core Decision: Stand Pat vs Stream

Both paths project 5-4 WIN, but they win **different sets of 5 categories** with different risk:

### Path A: Stand Pat (no moves)

| Category | Margin | Risk |
|----------|--------|------|
| AdjFG% | +.000 | EXTREME — literal coin flip |
| FT% | +.009 | HIGH — one bad game flips it |
| REB | +3.4 | Moderate |
| BLK | +4.8 | Safe |
| TO | +0.6 | HIGH — less than 1 turnover |

**You need 3 coin flips to all go your way for a full week.** If any one of AdjFG%, FT%, or TO slips, you lose the playoff.

### Path B: Stream (drop Hugley, add Brown + Tracey)

| Category | Margin | Risk |
|----------|--------|------|
| AdjFG% | +.011 | Moderate — 10x safer than standing pat |
| FT% | +.008 | HIGH — still tight, slightly worse |
| PTS | +4.6 | Moderate — new win, wasn't possible before |
| REB | +11.6 | Safe — padded significantly |
| BLK | +5.8 | Safe |

**You concede TO (inevitable with extra games) and pick up PTS instead.** Only 1 tight margin to defend (FT%) instead of 3. AdjFG% moves from coin flip to real lead. REB becomes a blowout.

### Risk Summary

| | Stand Pat | Stream |
|---|-----------|--------|
| Tight margins to defend | **3** (AdjFG%, FT%, TO) | **1** (FT%) |
| Safe wins | 2 (REB, BLK) | 4 (AdjFG%, PTS, REB, BLK) |
| Path to 5-4 | All 3 coin flips hold | 1 coin flip holds |

---

## Recommendation: Stream

**Make the moves.** The math strongly favors streaming.

Standing pat requires 3 razor-thin margins to hold for an entire week. Streaming reduces that to 1. You're trading a guaranteed loss in one tight category (TO) for significantly better odds in the others. In a must-win playoff round, reducing your exposure to variance is the right call.

### Moves

| Action | Player | Team |
|--------|--------|------|
| Move to IR | Jerome Brewer | La Salle |
| Drop | John Hugley IV | Duquesne |
| **Add** | **Dion Brown** | **Saint Louis** |
| **Add** | **Jadrian Tracey** | **VCU** |

### Projected Result After Moves: 5-4 WIN

| Category | Us | Them | Margin | Result |
|----------|---:|-----:|-------:|--------|
| AdjFG% | .547 | .536 | +.011 | **WIN** |
| 3PTM | 19.4 | 21.2 | -1.8 | LOSE |
| FT% | .768 | .760 | +.008 | **WIN** |
| PTS | 182.8 | 178.2 | +4.6 | **WIN** |
| REB | 73.8 | 62.2 | +11.6 | **WIN** |
| AST | 33.8 | 41.8 | -8.0 | LOSE |
| ST | 13.2 | 16.8 | -3.6 | LOSE |
| BLK | 7.6 | 1.8 | +5.8 | **WIN** |
| TO | 26.0 | 22.8 | -3.2 | LOSE |
