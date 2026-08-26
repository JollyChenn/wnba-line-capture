# WNBA Betting-Market Edge Audit — Final Report
*Assembled 2026-08-26. Data horizon 2026-06-24 → 2026-08-25 (64 days).*

```
VERDICT:
PROMISING BUT UNCONFIRMED — one candidate at Tier 2. Every other standing claim is
retracted or downgraded.

CONFIDENCE:
LOW

BEST MARKET:
PLAYER PROPS (pre-game, 1xbet board). NOT the game markets, and NOT in-play.

BEST CANDIDATE EDGE:
Sharp divergence. Bet the OVER on a 1xbet player prop when Pinnacle's line for the same
player-market is >= 1.0 point HIGHER, with the sharp line read no earlier than ~6h before tip.

CONDITIONS:
Over side only — the mirror (sharp >=1 LOWER -> under) returns -4.0% and does not work.
Sharp reference must be near-tip: Pinnacle's early prop lines are low-limit and uninformative.
93% of qualifying signals are the pts market, purely because that is where sharp coverage exists.

INDEPENDENT GAME COUNT:
32 games (of 159 in the prop book). The independent unit is the game, never the quote.

NUMBER OF SIGNALS:
45 bets, 30 distinct players.

OUT-OF-SAMPLE ROI:
Chronological thirds: +43.3% (n=13), +29.4% (n=12), -6.2% (n=23).
The most recent third — the only genuinely out-of-sample fold — is NEGATIVE.

OUT-OF-SAMPLE CLV:
Not established. The stored CLV columns do not measure closing line value (their "close" sits a
median 15.1h before tip and agrees with an honest recompute on 25% of rows). Model S itself has
no independent CLV: its "+12.7pp beat the close" is its ROI restated, because the 1xbet prop
line is unchanged 88% of the time.

AVERAGE ODDS/LINE:
1.808 decimal (breakeven 55.3%). Realised hit rate 64.4% (29-16).

MAXIMUM DRAWDOWN:
-4.26u on flat 1u staking; final +7.30u.

STATISTICAL CONFIDENCE:
Clears a pre-declared 14-cell noise ceiling (+13.3% at p95, game-block) — the only cell of 14
that does. But its own game-block 95% CI is [-11.2, +43.3] and INCLUDES ZERO. The point estimate
is significant against the grid; the effect itself is not significantly non-zero.

MULTIPLE-TESTING RESULT:
FAILS. This project has run 100+ declared hypotheses across ~15 sweeps. A single uncorrected cell
at this n does not survive family-wise correction over that history. The adversarial
falsification panel commissioned for this claim never ran (session limit) — it is UNVERIFIED.

EXECUTION-STRESS RESULT:
Robust to price friction: +16.2% / +15.6% / +14.9% / +14.3% at 0/1/2/3 cents of decimal slippage.
Robust to leave-one-player-out (worst +15.9%, dropping Chelsea Gray).
NOT stress-tested for executability — we cannot prove a quoted price was takeable, so every
figure here is an OPTIMISTIC UPPER BOUND.

BIGGEST FALSE-DISCOVERY RISK:
n=45 across 32 games, selected after a long search, with the most recent chronological fold
negative. That is precisely the profile of the five findings this project has already retracted.

BIGGEST DATA LIMITATION:
64 days. And the in-play dataset the brief was written for effectively does not exist here:
27 games, a ~15-minute poll cadence (not 1 minute), and 89.6% byte-identical repeated rows.
```

---

## 1. What the data actually is

The brief assumes minute-resolution live odds with synchronised game state. That is not what this
repository holds, and **no live model was built**. Precisely:

| brief assumption | reality |
|---|---|
| live odds ~1/min | Rows arrive ~1.3 min apart, but **89.6% are byte-identical repeats**. Only **130 distinct quote refreshes** exist across all 27 games, on a mechanical **~15.1-minute** poll clock. |
| in-play markets | moneyline, spread, total, team_total (+ alternate ladder) — genuine |
| independent in-play games | **27** |
| score / clock at each odds row | Present after all — `live_snapshots.csv` carries period, clock, scores, fouls, timeouts for all 27 games; 98.3% of odds rows match a state row within 90s. **An earlier claim in this project that state was unavailable was wrong.** |
| complete game traces | **None.** Median 52 snapshots/game; only 11 of 27 reach Q4; the poller starts and stops mid-game. |
| second in-play book | **No.** 1xbet game lines are pre-game only, so no cross-book work is possible in-play. |
| player props | **The real asset:** 7,634 gradable two-sided quotes across 159 games. |

**Not executable on this data:** brief sections 8–20, 22–23, 45 (live spread/total/moneyline
models, possessions, live efficiency, shooting-variance regression, event-reaction studies).
**Executable and executed:** 21, 26-G/H/I, 32 (price microstructure), plus the full pre-game
prop programme.

**Effective sample size.** The in-play feed's 24,615 rows deflate **45–60×** under a game-block
bootstrap to n_eff ≈ 20–38 — approximately the 27 games. The prop book deflates **2.7–2.9×**
(ICC 0.0354) to n_eff ≈ 2,500. A tick count is never evidence.

## 2. Data quality

```
PROP BOOK      raw ticks 81,755 -> collapsed to one two-sided closing quote per
               player-market-game = 7,634 gradable, across 159 games
IN-PLAY FEED   raw rows 24,645  -> 130 distinct refreshes across 27 games
EXCLUDED       All-Star exhibition (COOP/SPO: 22 box rows + 1 game) — removed, filter fixed
               DNP bets (59 rows) — now explicitly VOIDED rather than left pending forever
               one-sided quotes, pushes, period lines served under full-game codes
MARGIN         median two-sided overround 7.50% -> breakeven 53.48%
BASE RATES     blind Over -6.5%, blind Under -7.4% (independently reproduces the margin)
```

**Two data-layer defects were found and fixed today; both biased every prior study.**

1. **The board-to-box join deleted 3,201 rows (3.9%).** An exact lowercase string match failed on
   8 real players, led by **A'ja Wilson at 1,530 rows**. Every "no edge on stars" or usage-rank
   conclusion in this repo was computed on a sample with the league's highest-usage player
   removed. Fixed via `namefix.py`: 3,201/3,201 recovered, 0 unresolved, and unknown names are
   now reported rather than silently dropped.
2. **The Pinnacle game-line extractor took an arbitrary alternate.** Each snapshot posts a
   **7-rung ladder** sharing one capture timestamp, so a max-timestamp tie-break kept whatever
   landed last in the file — a median **1.5 points** off the main line, wrong on 71% of
   snapshots. Fixed by selecting the rung priced closest to even (validated against 1xbet's own
   posted total to mean +0.04, sd 0.66).

## 3. What survived — re-measured on repaired data

Fourteen cells declared, ceiling computed **first** at **+13.3%** (p95, game-block):

| cell | n | games | hit% | ROI | 95% CI |
|---|---|---|---|---|---|
| **C2 sharp gap ≥1 → OVER** | **45** | **32** | **64.4%** | **+16.2%** | **[-11.2, +43.3]** ← only cell above ceiling |
| C1 Model S | 103 | 73 | 60.2% | +11.4% | [-7.1, +30.5] |
| cushion ≥3 overs | 649 | 136 | 57.5% | +6.6% | [-4.6, +17.8] |
| C3 total HIGH overs | 1177 | 24 | 53.2% | -0.3% | [-8.4, +8.2] |
| C4 volatility LOW overs | 2521 | 159 | 51.6% | -3.5% | [-9.4, +1.9] |
| C1b **gate 3 alone** | 4926 | 152 | 50.9% | **-5.7%** | [-9.8, -1.8] |
| C4 volatility HIGH overs | 2442 | 159 | 47.7% | -11.6% | [-16.6, -7.0] |
| blind Over / Under | 7634 | 159 | 50.0% | -6.5% / -7.4% | — |

### Tier assignment

- **C2 sharp divergence — Tier 2 (Promising).** Confirmed mechanism: Pinnacle's line is
  genuinely more accurate than 1xbet's (MAE 5.003 vs 5.439). Clears its ceiling; robust to
  slippage and to leave-one-player-out. Held back from Tier 3 by a CI including zero, a negative
  most-recent fold, no multiple-testing survival, no verified CLV, and an unrun falsification panel.
- **C1 gate 3 / Model S — Tier 1 (Interesting Anomaly).** The staleness *mechanism* is real
  (p=0.0007 on production), but **gate 3 as a standalone bet loses 5.7%** — it closes only part
  of a 7.5% margin. The flip/hotover/overshoot signal layered on top is **falsified on raw
  production**: signal nights beat the line by +0.191 sd against +0.213 sd on the same players'
  other gate-passing nights (p=0.87). The signal contributes nothing measurable.
- **C3 game-total gradient — Tier 0. RETRACTED.** It existed only inside the alternate-line bug.
  On the clean main line: rho -0.0061, game-block p=0.807. The total still forecasts the *score*
  (r ≈ 0.5–0.8); it does not forecast whether her prop goes over. Two different hypotheses, and
  this project conflated them.
- **C4 volatility gradient — Tier 0/1.** The gradient is real and large (low-vol overs -3.5% vs
  high-vol -11.6%) but **both sides lose**. It is a skip-signal, not a bet.

## 4. False edges / failed hypotheses

Every one tested and killed, with cause of death. This list is the most valuable artifact here.

| hypothesis | cause of death |
|---|---|
| Game-total gradient | Alternate-line extraction bug; vanishes on the main line |
| Opponent "shade" | Unfiltered median poisoned by an All-Star game; p 0.019 → 0.398 when fixed |
| Garbage-time fade | **Mechanism falsified** — padded players score *more* next game (+1.28 vs +0.05) |
| Props → game totals | 72.7% hit rate decomposed into a 60% always-over base rate plus an arbitrary scaling constant |
| Odds lean (follow or fade) | All four directions ≈ -7%: the book's *prices* are calibrated |
| Opponent / teammate spillover | No spillover clears the 7.5% margin |
| Second market, same player | -1.7%; the edge is on the *number*, not the player |
| Fading gate rejects | -19.9% over → only +5.1% under: vig eats the anti-edge |
| ftunder / newunder fade | A real -13.3% loser, but its mirror is **-1.6%**, not +13.3% |
| Milestone lines (9.5 / 19.5) | Inverted — the book *shades* round-number overs upward |
| Within-game timing (H1 / Q4 share) | Quarter concentration is 1/volume (rho -0.73); residualise and every cell goes negative |
| Persistence / convergence of the sharp gap | Persistence runs backwards (p=0.945); only 3 convergence cases exist |
| Injury-news latency | Teammate overs at unmoved lines equal the control exactly (-7.2%) |
| Star-return fade, forgotten lines, slate size, book-vs-itself arithmetic | All inverted or flat |
| Engine tier/ev confidence layer | **Zero rank power**: spearman -0.0001, CI [-0.063, +0.061]; overstates hit rate by 11.2pp |
| In-play momentum / mean reversion / anchor (G/H/I) | The feed carries no information at 1–5 min; only 130 real refreshes exist |

## 5. The model-versus-market question (brief 42, 55)

> Does the model contain information not already reflected in the price?

**For Model S: no**, on the only test that can answer it. Against Pinnacle's vig-free fair price
it prices at **-7.7% EV**. Its apparent CLV is an artifact of the 1xbet line being static 88% of
the time. Its realised +6.8% live ROI sits inside noise, and its signal layer is falsified.

**For C2: yes by construction — and that is also its ceiling.** The information is *Pinnacle's*,
not ours. We are arbitraging a soft book against a sharp one. That is a real, well-documented
mechanism, and it caps the edge at how slowly 1xbet follows.

The market is broadly efficient here. The one exploitable seam is **staleness relative to a
sharper book**, not superior forecasting.

## 6. What would change the answer

| open question | what is needed |
|---|---|
| Is C2 real? | ~120–150 signals (≈100 independent games). At 45/32 the CI spans 54 points. **Widening Pinnacle prop capture to rebounds and assists is the single highest-value action** — the 93%-pts concentration is a capture limitation, not a property of the edge. |
| Do live models work? | Capture score+clock *joined* to odds (the poller already writes both files — they simply were never joined), a real refresh cadence rather than a 15-minute cache, and ≥150 games. |
| Cross-book in-play | A second in-play book. Currently impossible. |
| Is the seasonal decay real? | The book spans 64 days and the model decayed +42% → +9% → flat. Separating decay from noise needs a full season. |

## 7. Practical implication

**Model S is live at 12-9 (+6.8%) on 21 settled bets, with a stop-line at n=40.**

The honest position has worsened. Its signal layer is falsified, its standalone gate loses money,
it has no CLV against a sharp reference, and its ROI sits below the median of its own noise
ceiling. **Recommendation: do not increase stakes; treat n=40 as a genuine stop, not a formality.**

**Do not switch to C2 yet either.** It is better evidenced, but it is 45 bets with a negative
most-recent fold and an unrun falsification panel. It belongs in the shadow log — where `S_gap`
already runs — until it reaches ~120 signals.

The correct posture for the next month is not a bigger bet. It is **better capture**: fix the
Pinnacle prop coverage so the one live candidate can actually be tested.

---
*Numbers come from `clean_remeasure.py`, `c2_detail.py`, `verify_fixes.py`, and the four audit
tracks under `outputs/tables/`. The adversarial falsification panel for C2 did not run (session
limit) — every C2 figure should be read as unverified.*
