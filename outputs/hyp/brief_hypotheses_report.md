# WNBA Strategy Brief: Hypothesis Test Report

**Date:** 2026-08-26 · **Scope:** 5 hypothesis families from the user-supplied strategy brief, plus a 2-lens adversarial panel on every claim that cleared its noise ceiling.
**Repo:** `C:\Users\Axioo\wnba-line-capture` · All new code under `outputs/hyp/`. Nothing in the live pipeline was touched. No `.csv` modified.

**Bottom line: 0 of 16 testable hypotheses produced a bettable edge. Both claims that survived the primary tests were destroyed by the adversarial panel, on the same shared-baseline artifact.** The most valuable output of this run is a set of durable raw-production facts and five named method traps, not a strategy.

---

## 1. VERDICT TABLE

Breakeven reference: props 53.5% (board margin ~7.5%), game markets 52.6-52.8% (measured overround: ML 5.23%, spread 5.47%, total 5.60%).

| # | Hypothesis (from the brief) | Status | n | Indep. units | ROI | One-line reason |
|---|---|---|---|---|---|---|
| 1 | Cleared her pts prop by halftime in G -> bet her pts in G+1 | **NO EDGE** | 46 | 32 players | -10.1% Over / -3.0% Under | Event fires on only 10.7% of props; both sides lose; CI [-40, +17] is 27pp wide, and the mechanism behind it is separately falsified |
| 2 | H1-clearing carries info beyond "she had a big game" | **NO EDGE (panel-refuted)** | 1,969 | 146 G-games | n/a | The +1.49 pts gap is a shared-baseline artifact. On a confound-preserving null the expected gap is +1.70 to +1.96 and the observed +1.49 sits at the 6th-23rd percentile. Disjoint-baseline rebuild: +0.21, p=0.71 |
| 3 | The book over-adjusts her next line after a halftime clear (gate-3 family) | **NO EDGE** | 386 | 65 players | n/a | Book moves the line +0.0871 per H1 pt and +0.0404 per H2 pt while production repays +0.0821 and +0.0414. Book-minus-truth +0.005 / -0.001, half-swap p=0.27 |
| 4 | First-half scoring share is a stable exploitable trait | **NO EDGE** | 1,706 | 98 players | n/a | ICC 0.097; odd/even split-half r=+0.040; player-mean sd 0.069 vs per-game sd 0.224. It is a coin flip |
| 5 | Same-game: halftime clear -> her PR/PRA over that night | **NOT EXECUTABLE** | 387 / 314 | 40 / 34 events | look-ahead | Raw separation is huge (PR over 85.0% vs 47.6% base; PRA 88.2% vs 48.6%) but **no post-tip player-prop price exists in this repo**: 82,266 of 82,321 board quotes are pre-tip and `live_lines.csv` has 0 player props |
| 6 | Non-star props underpriced (too little action to discipline the line) | **NO EDGE** | 1,129 | 231 games | -2.7% | Mechanism runs backwards: over-rate falls with worse usage rank (50.96 / 49.94 / 47.70%). Non-stars go slightly UNDER. 0 of 50 cells cleared a +20.58% ceiling |
| 7 | Backup elevated by injury stays priced for her old role 2-3 games | **NO EDGE** | 630 | 110 games | -0.5% | Half true: minutes really jump (+3.61 at k=1) but decay in ONE game. The book raises her line +0.476 pts and she then MISSES it (46.19% over). Under hits 53.81% vs a 53.85% breakeven: one vig-width short |
| 8 | Teammate Out/Doubtful lifts the remaining players | **NO EDGE** | 3,439 | 146 games | -6.2% | Reproduces the flat-board control to within 0.2pp on both sides. Two or more absences INVERT it (47.89% over) |
| 9 | Alternate lines inherit the main-line error but pay better | **NOT EXECUTABLE** | 42,345 instants | 159 games | n/a | **The ladder does not exist in this capture.** At one scrape instant 98.27% of player-markets carry exactly ONE line and 0% carry 3+. The 1.36% two-rung states are a 1-scrape transient during a line move |
| 10 | Bet the ALIVE sharp-gap signal at +0.5 / +1.0 / +1.5 rungs | **NOT EXECUTABLE** | 59 signals | 21 games | n/a | 0 of 59 sharp-gap pings had a second rung at the same instant (95% upper bound 5.0%); 2 of 317 had one at all. The signal lives in `pts`, the rungs only in combos |
| 11 | Weeks 1-3 lines are the softest of the year | **NO EDGE** | 269 | 269 games | +4.6% | Inverted: wk1-3 spread slope is 0.9931 (t(slope-1)=-0.06), the BEST-calibrated window of the year. The soft window is wk7-10 (slope 0.8006). Best of 50 cells under a +11.13% ceiling |
| 12 | High-roster-turnover teams mispriced in games 4-15 | **NO EDGE** | 348 | 341 games | +0.1% | Turnover is derivable for 85 team-seasons; abs(spread error) is 9.25 pts for BOTH the high- and low-turnover tercile. Books already know who left |
| 13 | Recency blind spot: books over-weight the season average | **NO EDGE** | 1,057 | 1,057 games | n/a | Divergence coefficient on next-game margin beyond the closing spread is **-0.058 (t=-0.73), the wrong sign**, negative in all 6 specs. The line does not contain divergence either (t=+0.35): no content, not a blind spot |
| 14 | Fade the total after a hot 3P shooting game | **NO EDGE** | 75 | 75 games | -13.2% | Dead on arrival: next-game closing total moves only +0.147 pts per sd of 3P hotness (t=1.50), and -0.045 (t=-0.43) once the previous game's total surprise is controlled. No error to fade; all 12 cells negative |
| 15 | OREB mismatch gives unpriced extra possessions | **NO EDGE (real but too small)** | 75 | 75 games | +4.8% | Signal is REAL and genuinely unpriced in the total (residual slope +25.3, t=2.35) but worth only **+1.39 pts per sd against a ~2.5 pt vig hurdle**. Stated channel falsified: possessions FALL (-8.97, t=-2.21) |
| 16 | Star with 3 first-half fouls -> catastrophic drop-off | **NO EDGE** | 40 | 26 players | -8.8% Over / -8.1% Under | She loses 2.2 min and 0.78 pts, not a benching (fouls out 6.9%, median minutes lost 0.8). Her TEAM scores MORE (+1.21 vs closing implied) because these are whistle-heavy games (+3.11 game FTA per star in trouble) |

### Hypotheses the data cannot support at all

| Hypothesis | Status | Exactly why the data cannot support it |
|---|---|---|
| **Q1-outlier fade** (fade a team after an outlier first quarter, in-play) | **NOT EXECUTABLE** | Requires in-play prices timestamped against period state. `live_lines.csv` covers **41 team-pairs over 18 days** (2026-07-16 to 08-11); `live_snapshots.csv` covers **27 games / 1,269 rows (~47 snapshots per game)**. The two overlap on at most 27 games. Pre-game game markets are already dead over 1,842 games; there is no reason to expect the in-play version to be beatable at n=27 |
| **Momentum lag** (line lags an in-game run) | **NOT EXECUTABLE** | Same instrument gap. Needs sub-minute in-play quotes joined to a running-score feed. Median inter-scrape gap on the props board is 1,955s (33 min) and the live feed is ~47 snapshots per game. A run lasts 2-4 minutes; the capture cadence cannot see it |
| **1H / period markets** | **NOT EXECUTABLE** | **Zero half or quarter markets exist anywhere in the capture.** `xbet_gamelines.csv` carries only spread (4,833) / total (4,821) / moneyline (3,724); `live_lines.csv` only spread (21,580) / total (21,580) / team_total (10,658) / moneyline (3,025). The 1xbet type-codes for half markets are never pulled |
| **Referee crews** | **PARTIALLY EXECUTABLE, UNDERPOWERED** | The data DOES exist: `elo_model/gameinfo.csv` has an `officials` field populated on **1,055 of 1,059 games**, 1,008 of which join `outputs/gm/gm_dataset.csv`, 43 distinct officials. But (a) the **exact 3-person crew is useless**: 949 distinct crews, maximum 3 repeats; (b) per-referee power is thin: median 81 games each, total-residual sd 16.36, so **MDE at t=2 is 3.64 pts of total at n=81**, and a 43-cell grid ceiling swallows that; (c) the field is scraped POST-game, so every historical row is look-ahead as captured |
| **Overseas fatigue** (winter workload abroad) | **NOT EXECUTABLE** | Nothing in the repo contains international schedules, minutes played abroad, or offseason workload. It would also be a season-level variable: one observation per player-season, so roughly 160 independent units across the whole capture, against an effect that would have to be enormous to clear a 7.5% prop margin |

---

## 2. THE USER'S SPECIFIC QUESTION

> **"If a player clears her prop line by halftime, what happens to her next game - over, under, or nothing?"**

### Short answer: **NOTHING. Do not bet it in either direction.**

There is no next-game effect at all. It is not a small effect that the vig eats. The effect itself is zero once the test is done correctly.

**The three numbers that matter.**

1. **The literal bet.** 46 next-game pts props after a halftime clear, priced at real two-sided quotes: **Over -10.14% (47.8% hit), Under -2.97% (52.2% hit)**, block-bootstrap CIs [-40.0, +17.3] and [-29.8, +27.3]. Both far inside a +57.4% noise ceiling. n=46 over 19 game-days, minimum detectable effect +/-27% ROI. This alone is only "underpowered", not "dead".

2. **The raw-production signal that looked alive.** On a 4x larger panel (n=1,969 player-games), games where she cleared by halftime were followed by **+2.04 pts above her trailing median vs +0.54 for non-events, a +1.49 pts gap, player-block p=0.0045**. This is the number that would justify an over. It is an artifact.

3. **The corrected number: +0.21 pts, p=0.71.** Zero.

### The confound, in plain language

This is regression to the mean wearing a disguise, and the disguise is that **the same trailing median sits on both sides of the test**.

- The event label is `H1 points > reference line`, and on 1,512 of 1,969 rows (77%) that reference IS her 10-game trailing median `med_G`.
- The outcome is `next-game points - med_G`.
- So when `med_G` happens to sit low relative to her true level, the label fires more easily AND the outcome is mechanically inflated. No carryover is needed to produce a positive gap.

The engine is visible in the raw data: for `med_G` between 0 and 6.5, the event rate is 32.8% and the mean residual is +1.94; for `med_G` >= 14.5, the event rate is 4.8% and the mean residual is -0.56. Mean `med_G` is 6.07 on event rows versus 10.68 on non-event rows. Decomposing the identity, `gap = delta_next_pts - delta_med` gives `+1.49 = -3.11 - (-4.60)`: **the entire gap is the baseline term, and within player her actual next-game production is 0.20 pts LOWER on event rows.**

Four independent kills, each on the same rows:

| Test | Result |
|---|---|
| Placebo null (resample H1 within player, keep each row's own reference, so the label keeps its `med_G` dependence but carries no game-G information) | Null mean gap **+1.96** [p5 +1.47, p95 +2.43]. Observed +1.49 is at the **6th percentile**, p=0.94. The signal is SMALLER than the pure artifact |
| Null B (keep the label and `med_G`, shuffle observed next-game values within player) | Null mean **+1.695**, p95 +2.148. Observed at the **23rd percentile**, one-sided p=0.771 |
| Disjoint-baseline rebuild (split the same trailing-10 window in half; label off window A, outcome baseline off window B) | Same baseline **+2.861 (p=0.0002)** -> disjoint **+0.207 (p=0.71)** -> disjoint flipped **+0.024 (p=0.97)** |
| Direct fix (outcome measured against a leave-two-out player mean containing no `med_G`) | **gap -0.117**, n=1,963, player-block CI [-0.730, +0.475], **p=0.76** |

And even the surviving fragment is not first-half-specific. A control label containing **zero half information** ("her full-game points in G exceeded the reference") produces a **larger** gap (+2.005, p=0.0002) than the H1 label. Inside the subset that already cleared the full-game line, the H1 label adds +0.424 (p=0.357). Fully matched on player, points +/-1 and minutes +/-6 with a disjoint baseline, the H1 effect is +0.909 pts, se 0.576, **t=+1.58**.

Base-rate trap worth noting: every row in this panel averages +0.79 above its own trailing median, because the median of a right-skewed points distribution sits below the mean. Both arms being positive is arithmetic, not evidence.

### And the momentum story is wrong too

The original run reported "big WNBA games persist, they do not regress" at r=+0.191. **The panel refuted that as well, on the identical shared-baseline mechanism.** A null simulation that redraws each player's scores i.i.d. from her own distribution (true persistence = 0 by construction) and runs the same estimator returns **r = +0.11 to +0.12**. Corrected estimates:

- Points residual, baseline re-estimated at G+1: **r = +0.079**, CI [+0.026, +0.134].
- Points with a player fixed effect only, no trailing median anywhere: **r = +0.043** (only **+0.022, p=0.417** on the original restricted panel).
- **Points per minute: r = -0.020, p=0.294. Zero.**
- **Minutes: r = +0.191, p=0.002.** All of the persistence is minutes.
- Lag profile: points +0.044, -0.018, -0.001, -0.019, -0.027 at lags 1-5. Minutes +0.198, +0.124, +0.073, +0.024, +0.005.

**Correct statement:** per-minute scoring has no game-to-game memory. What persists is ROLE. A player who got big minutes gets big minutes again. And a slope below 1 IS regression to the mean: top-decile games run +12.49 pts above the player's trailing median and the next game runs +1.32, so **89% of the spike is given back**.

### The one live thread, and why you cannot trade it

Given she has **already** cleared her posted pts line by halftime, her **PR over lands 85.0%** of the time (vs a 47.6% base rate, n=387 quotes / 40 events) and her **PRA over lands 88.2%** (vs 48.6%, n=314 / 34). That is a 37-40pp separation, far larger than anything the pre-game board offers. It is same-game information and there is **no post-tip player-prop price anywhere in this repo**, so pricing it against the pre-game line is look-ahead and must not be recorded as ROI. This is the single most valuable unexecuted finding in the run (section 6.1).

---

## 3. MECHANISM TRUTHS (durable, mostly unbettable)

These are worth more than any marginal ROI cell because they constrain every future study.

**Player production**

1. **H1/H2 split is noise.** League-wide H1 share = 0.4920 (n=3,065 player-games). Per player-game (pts>=8): mean 0.496, sd 0.224, p25 0.353, p75 0.647. **ICC 0.097**; odd/even split-half r=+0.040 across 98 players; player-level mean sd only 0.069. There is no "first-half scorer" archetype in the WNBA.
2. **Scoring does not carry over; minutes do.** Per-minute scoring lag-1 autocorrelation is -0.020 (p=0.294). Minutes lag-1 is +0.191 (p=0.002) and decays smoothly over ~5 games. Points lag-1 is +0.03 to +0.08 and is ~87% explained by minutes. Any hot-hand or fade-the-padded-game model is modelling role, not form.
3. **A minutes spike is a ONE-game phenomenon, not 2-3.** Minutes above trailing median: **+3.61 (k=1), +0.83 (k=2), +0.15 (k=3), +0.33 (k=4), -0.59 (no jump)**. The brief's persistence claim is wrong by a factor of about 3.
4. **Usage rank predicts line-beating in the direction opposite to folklore.** Over-rate and mean(actual - line) both fall monotonically as usage rank worsens: rank 1-2 **50.96% / +0.492**, rank 3-4 **49.94% / +0.290**, rank 5-7 **47.70% / -0.104**. Slope -0.0179 sd per rank step (p=0.056). Bench lines are, if anything, marginally generous.
5. **Teammate absence does not lift the remainder, and two absences depress it.** One heavy (>=25 median min) mate out: over-rate 52.03%, remaining players' minutes essentially unchanged (mean min - own median = -0.01). Two or more out: **47.89%, z -0.081**. Backups with a heavy mate out play +3.66 minutes yet post mean(actual - line) **-0.355** and a 45.45% over-rate.
6. **Foul trouble is a trim, not a benching.** A 24+-minute player takes her 3rd foul before halftime in 6.1% of games (408 events, 2023-2026). Cost: **-2.23 minutes (t=-8.46) and -0.78 points (t=-2.41)**; fouls out 6.9%; median minutes lost 0.8. Only the 3rd-foul-in-Q1 subset (n=30) shows a real dent (-3.78 min, -3.62 pts).
7. **Foul-trouble games are HIGH-scoring, which inverts any naive test.** Each rotation star in trouble adds **+3.11 game FTA (t=6.17)**. Teams with a star in trouble beat their closing implied team total by +1.21 pts; game totals run 167.8 (one star) and 170.4 (two-plus) against 163.3 (none). A "star in foul trouble -> fade her team" rule is measuring the whistle.
8. **The post-foul-trouble bounce is UP.** Next game: +0.72 minutes (t=2.50), +0.47 points (t=1.42).

**Team and market**

9. **Team 3P% has no memory.** Raw AR(1) +0.046 (t=1.79); conditional on a hot game, next-game deviation from own baseline is +0.001 per sd (t=0.44). A z>=2 game (.530 vs a .328 baseline) is followed by .332 against a .342 baseline. Any model using recent 3P% as a team-strength input is adding noise.
10. **How the market actually updates a total.** Next-game closing total moves **+0.0355 pts per point of previous-game total surprise (t=5.16)** and +0.063 per point of team-scoring surprise (t=5.97): correct, aggressive shrinkage of about 3-6%. It does **not** decompose by shot type (3P-specific coefficient -0.045, t=-0.43 after controlling the total surprise).
11. **Offensive rebounds do not add possessions.** Realised possessions vs OREB mismatch: **-8.97 (t=-2.21)**; realised OREB +15.0 (t=6.7); FGA flat (t=-0.5). The benefit is second-chance efficiency, not pace. Any WNBA pace model that adds possessions for a rebounding mismatch is mis-specified.
12. **The OREB mismatch is unpriced in the total and fully priced in the spread.** Closing total ~ mismatch: t=-0.43. Closing home spread ~ mismatch differential: **-17.17, t=-3.96**. Realised total residual ~ mismatch: **+25.3, t=2.35**, worth **+1.39 pts per sd** = ~+2.8pp of win probability = ~52.4% against a 52.6% breakeven. Real, documented, and about 1 point of total short of the toll.
13. **League OREB rate is drifting hard and will fake a signal:** 2023 .2309 -> 2024 .2387 -> 2025 .2462 -> 2026 .2549. Any cross-season OREB feature centred on a pooled mean turns its top tail into a season dummy (in this run, 2023 supplied 1 of 150 top-tail games).
14. **Closing-line calibration is not uniform across the season.** Spread slope by league week: **0.993 (wk1-3), 0.910 (wk4-6), 0.801 (wk7-10, t(slope-1)=-2.49), 0.929 (wk11-14), 1.033 (wk15+)**. The soft window is mid-season, the exact opposite of the brief, and it is a slope not a side, so it is unbettable without a competing margin forecast.
15. **Early-season lines are wider, not wronger.** abs(spread error) wk1-3 is 10.353 vs 9.615 (t=+1.48) with signed error -0.64 (t=-0.56), and abs(total error) actually SMALLER (12.19 vs 13.00). That is what "books widen for uncertainty" looks like from the outside.
16. **Roster turnover has no relationship to closing-line error** in magnitude or sign (abs(spread error) 9.25 high-turnover vs 9.25 low-turnover; signed cover margin -0.68 / +0.63 / -0.08 by tercile). Reusable negative, now computable across all 8 seasons from `elo_model/box_full.csv`.
17. **Recency divergence is invisible to the market and correctly so.** Closing line ~ divergence: +0.017 (t=+0.35). Next-game margin beyond the line ~ divergence: -0.058 (t=-0.73). The only signed recency effect runs OPPOSITE the brief: good-early / cold-lately teams beat the spread by **+1.90 pts (t=+1.70, n=134)**, worth only +2.9% ROI after a 5.47% overround.
18. **1xbet expresses its opinion in the NUMBER, not the PRICE.** Full-board vig-free P(over) spans only **0.443 to 0.557** (p05-p95), a band of 0.114. At the realised +0.069 probability per point of line, the entire price grid can encode about **1.65 points of line opinion**. 16.0% of two-sided quotes sit at exactly 0.500 vig-free. This is the structural reason the only live edge in this project is a stale-LINE edge.
19. **The book under-adjusts a line move by about half.** Two independent measurements: within transient 2-rung pairs, priced dP(over) = +0.0368/pt vs realised **+0.0690/pt** (ratio 0.534, difference +0.0322 [+0.0116, +0.0543], p=0.003); across 8,883 consecutive single-line moves board-wide, median price step **+0.0321/pt**. Half the compression per side = **1.61pp against 3.90pp of vig**: real, 2.4x too small.
20. **The price step scales with market granularity but barely with the player.** Median step per point: reb +0.1007, ast +0.1122, ra +0.0724, pa +0.0280, pr +0.0260, pts +0.0250, pra +0.0214. But Spearman(book step, her 15-game SD) = **-0.253** where truth demands -0.969, R^2 = 0.110. The book gets the market right and the player mostly wrong.
21. **Measured vig on this data:** ML overround 1.0523 (breakeven 52.61%), spread 1.0547 (52.74%), total 1.0560 (52.80%), props ~1.0780 (53.5-54.0%).

**Method traps caught this run (each generated a false positive before being caught)**

- **Shared baseline.** Never let the label and the outcome subtract the same trailing statistic. It manufactured a +1.49 pts "carryover" (true value +0.21) and a +0.191 "persistence" (true value +0.04 to +0.08, and it is minutes). Within-player demeaning does NOT fix it: it removes the baseline's player mean and leaves its within-player variance. `Var(med_G)` alone was 53.2% of the reported covariance. **Re-estimate the baseline at G+1, or use a disjoint window.**
- **A player-block permutation cannot see a confound it carries into every draw.** Shuffling the label while `med_G` stays welded to the row reproduces the artifact in the null and in the data, returning p=0.0005 on a biased statistic. The correct null resamples the thing that generates the artifact.
- **The hidden level.** Regressing `line_move` on `(h1 - line_G)` gave +0.2478 at p=0.0003 that read as book over-reaction. It is `line_G` in disguise: enter `line_G` on its own and it takes -0.1917 while the h1 term collapses. Never regress on a difference when the level of the subtrahend independently predicts the outcome.
- **Pin the scrape instant.** 1xbet combo lines (pra/pr/pa/ra) flicker by a full point and return within one scrape 40.3% of the time. Pooling quotes across a player-market-game silently treats the flicker as two coexisting offers. That is exactly how the "24.8% of markets carry multiple lines, so a ladder exists" premise was formed.
- **Correlated quotes are not independent bets.** A 61.67% under-rate on 227 quotes collapsed to 55.1% and +0.16% ROI on the 89 player-games those quotes covered.
- **Parser trap:** 1,036 of 16,914 made threes (6.1%) carry no "three point" phrase. Adding "distance >= 22 feet is a three" takes team-point reconciliation from 64.51% to **94.28% exact** (mean abs error 0.065 pts).

---

## 4. WHAT SURVIVED, RANKED

Nothing survived as a bet. Ranked by residual value:

| Rank | Survivor | Status after falsification | Why it matters |
|---|---|---|---|
| 1 | **Halftime clear -> same-game PR/PRA over: 85.0% / 88.2% vs a 47.6% / 48.6% base** | **NOT REFUTED, NOT EXECUTABLE.** No adversarial attack applies because no ROI is claimed. Blocked purely by the absence of a post-tip prop price | A 37-40pp raw separation is an order of magnitude bigger than anything on the pre-game board. It is the only finding worth building capture for |
| 2 | **OREB mismatch is real, unpriced in the total, and ~1 pt short of the vig** (realised total residual +25.3, t=2.35, = +1.39 pts/sd; closing total t=-0.43) | **SURVIVES as a mechanism.** Its ROI cell does NOT: two look-ahead defects were found and each killed the edge (season drift -> season indicator; whole-season percentile -> future peeking). Walk-forward ROI collapsed from +21.96% to +4.80% and the best cell flipped sign | The only documented gap in the book's own model. Worth revisiting only if a lower-margin totals market appears, or if it can be stacked with a second unpriced total input |
| 3 | **The book under-adjusts a line move by ~half** (compression ratio 0.534, +0.0322/pt, p=0.003; corroborated by the median +0.0321/pt step across 8,883 board-wide moves) | **SURVIVES as a mechanism, fails as a bet.** 1.61pp per side vs 3.90pp of vig, 2.4x too small. Best of 12 cells +2.42% vs a +8.30% ceiling, and that cell is the always-over base-rate cell | Explains why the project's only live edge is a stale-LINE edge, and puts a hard number on how much price error the board can physically express (~1.65 pts) |
| 4 | **Minutes-jump elevation and the book's over-adjustment** (+3.61 min at k=1; line raised +0.476 pts, 45.4% of lines raised vs 28.2%; she then hits 46.19% over) | **SURVIVES as a mechanism.** The under side reaches **53.81% against a 53.85% breakeven** | The cleanest evidence that 1xbet reads minutes news promptly. It narrows where staleness can live: not in role news. Exactly one vig-width from being a bet, so it is the natural cell to re-check at 3-4x the sample |
| 5 | **Foul-trouble whistle confound** (+3.11 game FTA per star in trouble; team beats implied total by +1.21) | **SURVIVES.** Falsifies the folklore rather than supporting a bet | Pre-kills a whole family of "star in trouble -> fade" ideas |
| 6 | **H1 share is a coin flip** (ICC 0.097, split-half r=+0.040) | **SURVIVES** | Structural reason the entire first-half family had to fail. Cite it before anyone proposes a half-based player model again |
| 7 | ~~H1-clearing predicts next-game production (+1.49 pts, p=0.0045)~~ | **REFUTED by both panel lenses.** Corrected value +0.21 (p=0.71) / -0.12 (p=0.76) | Recorded only so it is not rediscovered |
| 8 | ~~Big scoring games persist (r=+0.191, p=0.0005)~~ | **REFUTED by both panel lenses.** Corrected value +0.03 to +0.08, and per-minute scoring is -0.020 (p=0.294). The persistence is MINUTES (+0.191) | Recorded only so it is not rediscovered. This also weakens, rather than corroborates, the earlier garbage-time-fade reading |

**Two for two on the panel: every claim that cleared its primary noise ceiling was destroyed by a correctly-specified null, and both failures were the same trap.** That is the strongest signal in this report about how to run the next study.

---

## 5. WHAT DIED AND WHY

**Died because the mechanism runs backwards (the strongest kind of negative)**
- Non-star props underpriced -> non-stars actually go slightly UNDER (over-rate 50.96 / 49.94 / 47.70% by usage rank).
- Backup elevated by injury stays cheap -> the book raises her line +0.476 and she MISSES it (46.19% over).
- Teammate out lifts the remainder -> two or more absences INVERT it (47.89% over); backups with a mate out post -0.355 vs line.
- Weeks 1-3 are softest -> wk1-3 is the best-calibrated window of the season (slope 0.9931); the loose window is wk7-10.
- Recency blind spot -> divergence coefficient is -0.058, the wrong sign, in all 6 specs; the mirror direction is the one with a signed effect.
- Deeper alternate rung is the better instrument -> the SHALLOWER rung's over beats it by +6.52% [+2.18, +11.05].
- Star in foul trouble -> her team scores MORE, and her next game is +0.72 min / +0.47 pts.
- OREB mismatch buys possessions -> possessions FALL (-8.97, t=-2.21).

**Died because the instrument does not exist**
- The alternate-line ladder: 98.27% of player-market scrape instants carry exactly one line, 3+ rungs never occur in 42,345 instants, and the 1.36% two-rung states last a median of 1 scrape (83.3% are move-through or blip-return).
- Sharp-gap at alternate rungs: 0 of 59 eligible pings had a second rung; 2 of 317 had one at all.
- Same-game PR/PRA: no post-tip player-prop price exists (82,266 of 82,321 board quotes map to a forward game).
- 1H markets, referee crews as currently captured, overseas workload, Q1-outlier fade, momentum lag: see the second verdict table.

**Died because the effect is real but smaller than the vig**
- OREB mismatch on the total: +1.39 pts/sd against a ~2.5 pt hurdle.
- Line-move compression: 1.61pp per side against 3.90pp of vig.
- Minutes-jump under: 53.81% against a 53.85% breakeven.
- Good-early / cold-lately spread: +1.90 pts of cover margin -> +2.9% ROI against a +19.46% family ceiling, profitable in 3 of 8 seasons.

**Died on the noise ceiling**
- Role/usage grid: 0 of 50 cells cleared +20.58%; best +6.19%.
- Minutes-jump grid: 0 of 36 cells cleared +28.60%; best +15.84%, and its dose-response RISES with k (-3.52 / +13.16 / +15.84), the opposite of the recalibration story.
- Season-timing grid: 0 of 50 cells cleared +11.13%; turnover 0 of 6 cleared +5.88%; divergence 0 of 30 cleared +11.60% and the best cell ran the OPPOSITE direction to the claim.
- Alternate-line grid: best +2.42% vs +8.30%.
- Hot-3P fade: all 12 cells negative, best -6.67% vs +23.17%.
- H1 grid: all 6 filters inside a +49.71% ceiling.

**Died on the panel (survived the primary test, killed by a correct null)**
- H1-clearing predicts next-game production: shared-baseline artifact, corrected value zero.
- Big games persist: shared-baseline artifact plus a minutes confound; corrected value ~+0.04, and it is role, not scoring.

**Died on look-ahead found during the run (self-caught)**
- OREB top-decile +21.96% [+2.6, +40.6] -> +4.80% once the within-season percentile stopped peeking at future games.
- "Book captures 201% of what she repeats" -> selection on extreme residuals against a stale median; artifact-free the book is within 0.005 of truth.
- "Book over-reacts to first-half explosions" (+0.2478, p=0.0003) -> `line_G` in disguise.

**Died on correlated-quote inflation**
- The post-hoc "minutes jump + line raised -> under" rescue: 61.67% under-rate on 227 quotes became 55.1% and **+0.16% ROI** on the 89 underlying player-games, and all of it lived in the second half of the season (-0.38% then +22.09%).

---

## 6. WHAT WOULD MAKE THE DEAD ONES TESTABLE (specific and costed)

Ordered by value per unit of engineering.

### 6.1 Post-tip player-prop capture (unlocks the only big raw signal)
**Unlocks:** same-game halftime-clear -> PR/PRA over (85.0% / 88.2% vs a 47.6% / 48.6% base rate), plus every in-play prop idea in the brief.
**What is missing:** the 1xbet in-play section is never pulled for player markets. `xbet_board.csv` is pre-tip on 82,266 of 82,321 quotes; `live_lines.csv` has 56,844 rows and **zero** player props.
**Change:** a NEW puller (never edit `cloud_xbet.py`) that hits the in-play player-prop type-codes; the ops file already documents the pre-game code family (ast 1491/1492, reb 1489/1490). Poll every 2-3 minutes during live windows and stamp game clock and score from the same request, so gate and price share an instant (law 5).
**Cost:** ~1 request per live game per poll. At ~3 games/night, 2.5h each, 2-minute cadence, that is ~225 requests/night, well inside the current scrape budget. Storage 1-2 MB/night.
**Yield:** the halftime-clear event fires on ~10.7% of posted props, so expect **20-40 events per month** and ~120 gradable quotes. A 37pp separation needs only n~60 events to resolve: **2-3 months to a verdict.** Highest-yield capture change available.
**Caveat before betting a cent:** an 85% over rate against a pre-game line is not an edge; the live line will already have moved. The test is whether the LIVE price still under-prices it, which cannot be known until the prices are captured.

### 6.2 Half and quarter markets
**Unlocks:** 1H totals/spreads, Q1-outlier fade, a directly bettable version of the first-half family.
**What is missing:** no half or quarter market exists in any file (`xbet_gamelines.csv`: spread 4,833 / total 4,821 / moneyline 3,724; `live_lines.csv`: spread 21,580 / total 21,580 / team_total 10,658 / moneyline 3,025).
**Change:** add the 1xbet half/quarter type-codes to the game-lines pull, roughly 3 extra market types per game, pre-game and in-play.
**Cost:** ~1 extra request per game per scrape; about a day to find and validate the codes.
**Priority: LOW.** Full-game markets are dead across 1,842 games and 515 cells, half markets carry a wider margin, and H1 share is a coin flip (ICC 0.097). This buys optionality, not a hypothesis.

### 6.3 Referee crews (data exists; timing and power are the blockers)
**What already exists:** `elo_model/gameinfo.csv` has `officials` populated on **1,055 of 1,059 games**, 1,008 joinable to `outputs/gm/gm_dataset.csv`, 43 distinct officials, median 81 games each, 36 officials with >=30 games.
**Blocker 1, timing.** The field comes from the post-game summary, so every historical row is look-ahead. The unlock is a **pre-tip** crew capture (assignments are published on game day). Cost: 1 request per game, ~4 per day, folded into the existing morning loop. Trivial.
**Blocker 2, power.** Exact 3-person crews are hopeless: **949 distinct crews across 1,055 games, max 3 repeats.** Per-referee is the only viable unit: total-residual sd is **16.36 pts**, so **MDE at t=2 is 3.64 pts of total at n=81** and 2.99 at n=120, and a 43-cell grid ceiling exceeds that. You need roughly **200 games per referee**, i.e. 2-3 more seasons of forward capture.
**Verdict:** start the pre-tip capture now (nearly free, and the clock only runs forward), run no test for at least two seasons. A cheaper interim test is referee-level FOUL rate rather than total, since foul counts carry far less variance than points.

### 6.4 Live period data (in-play state)
**What exists:** `live_snapshots.csv` = **27 games, 1,269 rows (~47 snapshots per game)** with score, fouls, timeouts, rebounds; `live_lines.csv` = **41 team-pairs over 18 days** (2026-07-16 to 08-11), not joined to state at a shared instant.
**Change:** merge the snapshot poll and the live-price poll into one request loop so every price row carries period + clock + score, and run it for the full slate rather than a sample. Cost: ~1 day, no new endpoint.
**Yield:** ~40 games/month of joined state+price; two full seasons (~300 games) before an in-play game-market test has power, and the pre-game game markets are already dead. **Priority: LOW, and only as a by-product of 6.1.**

### 6.5 Overseas workload
**What is missing:** everything. No international schedule, no minutes abroad, no offseason table.
**Change:** an external scrape of EuroLeague Women / Turkish / Chinese league game logs for ~200 players, plus a cross-league name-resolution layer. Note the in-repo name join silently dropped 8 players and 3,201 rows (3.9% of the book) until it was fixed today; a cross-league join will be substantially worse.
**Cost:** multi-day build with permanent maintenance, and the name join is the expensive part.
**Power:** season-level variable, one observation per player-season, roughly **160 independent units in total** against a 7.5% prop margin.
**Verdict: ABANDON.** Underpowered by design before any data is collected.

### 6.6 Cheap extensions to work already done
- **Extend PBP capture past 2026-07-15.** `outputs/hyp/h1_all.csv` covers 05-08 to 07-15 (17,278 player-games, 1,058 games). `data/halves_2026.csv` stops at 06-22, before the prop board starts on 06-24, so it is useless on its own. Extending the pull roughly **quadruples the bettable H1 pair count** (46 -> ~180). Cost near zero, the parser exists and reconciles at 94.28%. This is housekeeping, not a priority, since the underlying effect is now zero.
- **Player minutes for 2023-2025.** The PBP substitution parse (51,538 "X enters the game for Y" rows) reconstructs per-player on-court seconds validated to mean abs error 0.254 min against `data/box_2026.csv`, 99.9% within 2 minutes. This unlocks three extra seasons of minutes that the box files do not carry, and minutes is where all the player-level persistence lives (r=+0.191). **The most useful cheap asset produced this run.**

---

## 7. PRIORITY RECOMMENDATION

Standing position: game markets dead across 1,842 games and 515 cells; props carry exactly one Tier-2 candidate (soft-vs-sharp staleness, n=45 / 32 games, +16.2%, CI includes zero); this run added 16 more negatives and 2 panel-refuted positives. The search space for a new pre-game signal on this board is close to exhausted.

### Do these three, in this order

**1. Stop hunting new signals. Grow the ONE live candidate to a verdict, on CLV.**
Soft-vs-sharp staleness is at n=45 over 32 games. Nothing else in this project has ever cleared a ceiling. The month should go to feeding it.
- Flat 1u, no filter tuning. The filter hunt stays closed until ~150 bets, as already ruled.
- **Grade on CLV, not ROI.** At n=45 the ROI CI is roughly +/-30pp and cannot separate +16% from zero; CLV converges an order of magnitude faster and is the only proof this project accepts.
- Enforce law 5 mechanically: log the Pinnacle read timestamp and the 1xbet quote timestamp on every bet row, and reject any bet where they differ by more than the gate window. Two of this run's false positives came from gate/price instant drift in analysis; the live path deserves the same guard.
- Expected: 40-60 bets/month, so **n~150 by late October** and a real verdict rather than a sixth downward revision.

**2. Build the post-tip player-prop capture (6.1). Collect only. Bet nothing.**
It is the only place in this entire investigation where a raw separation of 37-40pp exists (PR over 85.0% vs 47.6%). Every pre-game family is now dead or vig-bound, so the next edge, if there is one, lives in an instrument that is not yet captured. Cost is one new puller and ~225 requests/night. Set the rule now: **no bet from this feed for 90 days.**

**3. Re-audit the existing live model with the shared-baseline test.**
The panel destroyed two claims that had cleared their ceilings, both on the same trap: a trailing median on both sides of a test. The live Model S signals (cold = t3 <= median - 4, shrink = t5 - t10 <= -3) are **defined in terms of trailing medians and trailing windows**, exactly the structure that produced +1.49 out of nothing and +0.191 out of +0.04. Run the diagnostic: re-estimate each signal's baseline at G+1, or on a disjoint half of the trailing window, and re-check the historical separation. Cost: one day, no new data. If the signals survive, confidence rises cheaply. If they do not, that is worth more than any new hypothesis, and it would explain the "verdict revised 5 times downward in one day" history.

### Abandon
- **All game markets, pre-game and in-play.** 1,842 games, 8 seasons, 515 cells, plus 88 more this run. Zero.
- **Role, usage, and injury-elevation prop families.** Mechanism falsified in direction on raw production, not merely under a ceiling.
- **Alternate-line work of any kind.** The instrument does not exist on this book: 0% of 42,345 scrape instants carry 3+ rungs.
- **Season timing, roster turnover, recency divergence.** All three inverted at the mechanism stage.
- **Hot-3P fades and foul-trouble fades.** The book makes neither error.
- **The first-half family as a pre-game bet.** H1 share ICC is 0.097; there is nothing there to model.
- **Overseas fatigue.** Underpowered by design (~160 independent units).
- **Referee crews at the crew level.** 949 distinct crews, max 3 repeats. Per-referee is a 2028 question; start the pre-tip capture, run no test.
- **Any new filter hunt on fewer than 150 forward bets.** This run produced 6 post-hoc cells that looked alive; all 6 died on a ceiling, a dedup, a walk-forward split, or a correct null.

### The meta-lesson worth keeping
Two claims cleared their declared noise ceilings this run and **both were artifacts of the same construction error**: the label and the outcome shared a trailing statistic, and a player-block permutation carried the artifact into every null draw so it could not see it. The correct nulls (placebo resample preserving the coupling; disjoint-baseline rebuild; i.i.d. redraw through the same estimator) each returned a null mean LARGER than the observed effect. **A permutation test is no longer sufficient evidence in this project unless it can be shown to break the specific confound at issue.** Name what generates the artifact, then simulate that.

---

*Scripts (all new, all under `outputs/hyp/`): `hlib.py`, `h1_build.py`, `h1_qc.py`, `h1_census.py`, `h1_main.py`, `h1_mech.py`, `h1_confound.py`, `h1_q45.py`, `h1_q4b2.py`, `h1_final.py`, `h1_cf3.py`, `h1_cf4.py`, `h1_cf5.py`, `fx_h1carry.py`, `fx_h1carry2-4.py`, `fx_persist.py`, `hcf_persist.py`, `hcf_null.py`, `hcf_min.py`, `rolelib.py`, `build_role.py`, `hypA.py`, `hypA2.py`, `build_B.py`, `hypB.py`, `hypB2.py`, `hypB3.py`, `alt_*.py`, `tk_lib.py`, `tkA_mech.py`, `tkA_roi.py`, `tkA_turnover.py`, `tkB_recency.py`, `tkB_mirror.py`, `tk_follow.py`, `pbp_parse.py`, `pbp_players.py`, `pbpx_lib.py`, `pbpx_a_mech.py`, `pbpx_a_roi.py`, `pbpx_b.py`-`pbpx_b5.py`, `pbpx_c.py`, `pbpx_c2.py`. Caches: `h1_all.csv`, `role_rows.json`, `B_rows.json`, `pbp_derived.csv`, `pbp_players.csv`, `pbp_fouls.csv`, `pbp_p3.csv`.*
