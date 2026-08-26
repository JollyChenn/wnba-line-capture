# assemble outputs/tables/prop_edge_audit.md and outputs/candidate_strategies.json
import os, sys, json, datetime
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
O = os.path.join(D, "outputs")
def rd(n):
    p = os.path.join(O, n)
    return open(p, encoding="utf-8").read() if os.path.exists(p) else "(missing)"
ceil = json.load(open(os.path.join(O, "t4_ceilings.json")))
ceilU = json.load(open(os.path.join(O, "t4_ceilU_byn.json")))
c2c = json.load(open(os.path.join(O, "t4_c2ceil.json")))

HDR = """# Track 4 - The player-prop edge, held to the brief's standard

Audit date 2026-08-26. Read-only reconstruction; nothing in the live pipeline was touched.
Every number below is recomputed from `xbet_board.csv`, `pinn_board.csv`, `bets_log.csv`,
`gamelines.csv` and `data/box_2026.csv` by `t4_build.py`, not copied from the repo's write-ups.

## What was reconstructed, and how it was priced

`outputs/t4_base.json` holds **7,227 two-sided 1xbet player-prop quotes across 132 games and
117 players**, 2026-06-24 to 2026-08-25. A row survives only if the book posted BOTH sides at
the SAME line, the player has >= 6 prior games and played >= 8 minutes.

Three entry instants are carried for every row, and each is **gated and graded at its own
instant** (Law 5): the first posted quote (`open`), the last quote at or before tip-6h, and the
last quote at or before tip-1h. **tip-1h is the primary**, because it is the only one an
operator can actually reach with a settled line.

Board economics, measured not assumed: mean over 1.880 / mean under 1.862, **implied margin
7.56%**, so break-even is **53.2%-54.1%** depending on the cell, never 50%. The unfiltered board
returns **-5.5% on overs and -8.5% on unders**. Push rate 0.00% (all lines are half-points).

The reconstruction reproduces the project's own numbers, which is the licence to audit them:
Model S n=119, 74-45, **+14.9%** at tip-1h and **+15.8%** at the open; the reject group
**-6.5%**; no-previous-line **-8.8%**.

## Sections of the brief that are not executable here

Sections 8-20, 22-23 and 45 need live game state. `live_lines.csv` has no score, clock, period
or possession column, and the 1,058 play-by-play games in `elo_model/plays_full.csv` have zero
overlap with the 27 games that carry in-play odds. Not attempted, not faked.

---

## 1. NOISE CEILINGS, DECLARED BEFORE ANY RESULT WAS READ

Three grids, each permuted at the level its label actually lives at (Law 2).

| grid | universe | cells | null | median best cell | **p95** |
|---|---|---|---|---|---|
| **U** signal-candidate filters | @UN@ quotes | @UC@ (7 src subsets x 8 market subsets x 6 line gates) | shuffle outcome inside PLAYER block | @UM@ | **@UP@** |
| **G** game-level labels | @GN@ quotes, 50 games | @GC@ | permute the game TOTAL across games | @GM@ | **@GP@** |
| **P** player-level labels | @PN@ quotes, 639 blocks | @PC@ | permute the player-market volatility label within market | @PM@ | **@PP@** |

Grid U's ceiling is dominated by small cells, so it was recomputed at matched cell size. This is
the single most important table in the audit:

| min cell n | cells | null median | null p95 | null max | best REAL cell |
|---|---|---|---|---|---|
"""

rows = ""
for mn in ("25", "50", "80", "100", "119", "140"):
    if mn not in ceilU: continue
    c = ceilU[mn]
    rows += "| %s | %d | %+.1f%% | %+.1f%% | %+.1f%% | %+.1f%% (n=%d) `%s` |\n" % (
        mn, c["cells"], 100*c["med"], 100*c["p95"], 100*c["mx"], 100*c["best_real"], c["best_n"], c["best_name"].replace("|", "/"))

BODY = """
**At every cell size, the best cell the project's own filter space can produce is at or below
the median of what pure noise produces on the same grid.** The Model S cell itself
(`src=flip+hotover+overshoot | mk=pts+pra+pr | mv<0.5`, n=137 before one-position dedup,
+14.8%) sits at the **88th percentile from the top of the null best-of-grid** - 88 of every 100
shuffled replications produce a better winner than the real data does. Its own single-cell
permutation p is 0.0822, before any correction.

A structural note found while building the grid: **1xbet moves player lines in whole points
only.** The observed moves are exactly {-4,-3,-2,-1,0,+1,+2,+3,+4}. So "raised by >= 0.5" and
"raised by >= 1.0" are the *same rule*, and the 0.5 in the live config is a free parameter that
does nothing. The gate has three real settings, not a continuum.

---

## 2. C1 - GATE 3 / MODEL S STALENESS

### The claim splits into two very different things

**(i) The gate as a gradient. This is real.** On the whole board - 6,606 quotes, 127 games,
106 players - the direction holds on RAW PRODUCTION, where the book's price cannot manufacture
it (Law 6):

| line move | n | over-rate | mean (actual - line)/player sd |
|---|---|---|---|
| -1 | 1233 | 54.3% | +0.164 |
| 0 | 3036 | 50.4% | +0.113 |
| +1 | 1343 | 48.7% | +0.007 |
| +2 | 338 | 48.5% | -0.046 |

rho(line move, standardised beat) = **-0.0390**, player-block permutation **p = 0.0007**,
game-block permutation **p = 0.0013**. This survives BH *and* Bonferroni over the whole
reconstructed family. It is the strongest single result in Track 4.

**(ii) The gate does not pay.** Over-side ROI on the board:

| group | n | ROI | 95% CI (game-clustered) |
|---|---|---|---|
| cut (mv <= -1) | 1706 | -2.6% | [-8.4%, +3.1%] |
| flat (mv == 0) | 3036 | -5.3% | [-10.1%, -0.8%] |
| raised (mv >= +1) | 1864 | -7.1% | [-13.9%, -0.6%] |
| **gate PASS (mv <= 0)** | **4742** | **-4.4%** | **[-8.6%, -0.3%]** |

The gate is worth about **+4.4 pp against a 7.6 pp margin**. It closes roughly 60% of the vig
and stops there. As a standalone bet it loses money at large n with a CI that excludes zero.

### So where does +14.9% come from? A 2x2 on the same board at the same instant

| | n | over-rate | ROI |
|---|---|---|---|
| no signal, gate FAIL | 1017 | 49.4% | -7.0% |
| no signal, gate PASS | 1954 | 52.8% | -2.6% |
| signal, gate FAIL | 81 | 50.6% | -5.1% |
| **signal, gate PASS (= Model S)** | **137** | **62.0%** | **+14.8%** |

All of the profit is in the interaction cell. The gate main effect is +4.4 pp; the rest is the
`flip / hotover / overshoot` signal. **That signal does not survive.**

### The decisive test: does the signal fire on the right NIGHTS?

Restrict to player-markets the signal *does* fire on, and compare her signal nights with her own
other gate-pass nights. Between-player quality then cancels by construction. Null = shuffle the
signal flag inside each player-market block.

| set | blocks | signal nights | her quiet nights | within-block diff | null mean | **p** |
|---|---|---|---|---|---|---|
| gate PASS | 80 | n=137, +14.8% | n=720, +4.9% | +9.9 pp | +8.3 pp | **0.4263** |
| gate FAIL | 59 | n=81, -7.3% | n=301, +11.4% | -18.7 pp | -0.9 pp | 0.9385 |
| all rows | 99 | n=218, +6.6% | n=1391, +4.8% | +1.8 pp | +6.4 pp | 0.7670 |

The null mean is already +8.3 pp because signal-carrying blocks are the high-line, high-usage
ones. The real +9.9 pp is inside that. And the sign **inverts** on gate-FAIL rows, which is the
shape of noise, not of an interaction.

**Law 6, applied to the signal, falsifies it outright.** On raw production:

- signal nights, mean (actual - line)/sd = **+0.191**
- the same players' other gate-pass nights = **+0.213**
- difference **-0.023, p = 0.8705**

Signal nights are, if anything, marginally *worse* than her ordinary nights at beating the line.
The entire +9.9 pp of ROI difference is price and luck. A falsified mechanism means the ROI cell
is noise - that is the project's own rule.

An intermediate result worth recording because it nearly fooled this audit: using
"player-markets the signal *ever* fires on" (which peeks at the future) makes the effect look
like pure player selection, +6.5% vs -6.9%. Rebuilt chronologically - "has fired on her in an
EARLIER game" - that split collapses to **+1.0% vs -2.3%, +3.2 pp, p = 0.2483**. The
player-selection story was itself a look-ahead artifact.

### (a) Walk-forward, split by GAME

| fold | dates | n | games | ROI | win rate |
|---|---|---|---|---|---|
| 1 | 06-26 .. 07-19 | 40 | 25 | +20.2% | 65.0% |
| 2 | 07-19 .. 08-07 | 38 | 25 | +36.4% | 73.7% |
| 3 | 08-07 .. 08-25 | 41 | 25 | **-10.1%** | 48.8% |

By half-month: Jul-A +19.0%, Jul-B +20.9%, Aug-A +12.6%, **Aug-B -2.9%**. Every one of those CIs
straddles zero.

**The seasonal decay is real and it is the dominant fact about C1.** The board capture starts
2026-06-24, so this reconstruction only sees the tail of the "+42% late June" period (n=2-3
bets). Within what is observable: July +20.1%, August +6.9%, second half of August -2.9%. The
claim is not *purely* an artifact of the early period - fold 2 is the best fold and runs to
August 7 - but the trend is monotone downward and the most recent third of the sample is
negative. And the timing effect that the whole claim rests on runs **+37.3 pp, +19.0 pp,
-17.5 pp** across the three folds.

The genuinely prospective record agrees with the pessimistic reading. `shadow_forward.csv`
separates live-logged rows from replayed ones:

| MODEL_S rows | n | win rate | ROI |
|---|---|---|---|
| **logged live** | 17 | 52.9% | **-1.5%** |
| backfilled replay | 85 | 64.7% | +19.2% |

`model_forward.csv`: 26 settled, 15-11, +6.5%. The replays prove the rule would have *selected*
those bets; only the 17 live rows prove anything was reachable, and they are flat.

### (b) Multiple testing

See section 6. `C1 Model S ROI > 0` has p = 0.0468 and **fails** BH at q=0.10 (crit 0.0425).
The `starred-minus-raised` contrast (p = 0.0375) passes. The two staleness-gradient tests on
raw production (p = 0.0007 / 0.0013) pass BH and Bonferroni.

### (c) Robustness

Threshold perturbation, with the whole-point granularity in mind:

| gate | n | ROI |
|---|---|---|
| mv <= -1 (cut only) | 65 | +24.3% |
| **mv <= 0 (live rule)** | **119** | **+14.9%** |
| mv <= +1 | 161 | +9.6% |
| no gate | 183 | +6.4% |

Monotone, which is in the claim's favour. But note the live setting is not the best one and the
gradient is exactly what the board-wide gate gradient already predicts.

- **Leave-one-team-out**: ROI stays in [+11.2%, +19.0%], spread 7.8 pp. Stable.
- **Leave-one-player-out**: 49/49 deletions leave it positive; worst case +12.6%. Stable. No
  single player carries it; the top 5 players are 25% of bets.
- **Chronological stability**: fails, as above.

Robustness to *cross-sectional* deletion is good. Robustness to *time* is what fails, and time
is the axis that matters for a forward bet.

### (d) Execution stress

| | ROI |
|---|---|
| no slippage | +14.9% |
| 1c decimal | +14.3% |
| 2c | +13.7% |
| 3c | +13.0% |

**Slippage that takes C1 to zero: 24.0 cents of decimal odds.** That is a large margin of
safety - if the ROI were real. Missed entries barely matter (10% -> +15.0%, 25% -> +14.9%,
random omission), because the rule has no timing sensitivity within the night.

Priced at three different instants, each gated and graded at that instant: open +15.8%
(n=132), tip-6h +13.0% (n=125), tip-1h +14.9% (n=119). **In this reconstruction the
open-vs-late gap is small**, which is worth flagging against the project's own note that
"every historical ROI in the repo is an opening-line number (OPEN +12.8% vs PING +4.0%)". The
difference is that the repo's PING number is a *live* record and this is a reconstruction; a
reconstruction cannot capture the bets that were unreachable by the time the ping arrived. The
live 17-row -1.5% is the number that carries that information, and it is the number to believe.

### (e) Bankroll

Flat 1u: final +17.74u over 119 bets, **max drawdown 9.0u, longest losing streak 6**.
OOS (folds 2-3) win rate 60.8% at mean odds 1.849 -> full Kelly f = 0.145.

| staking | stake | final from 100u | max DD |
|---|---|---|---|
| flat 1u | 1.0u | 117.7 | 9.0u |
| 1/4 Kelly | 3.6% | 178.5 | 29.0% |
| 1/8 Kelly | 1.8% | 135.8 | 15.4% |

Risk of a 50u drawdown on a 100u bank, flat 1u, game-clustered resample: **0.0%**. Risk of ruin
**0.0%**. Those zeros are not comfort - they are a statement that 119 bets is too short a series
to reach ruin, not that the strategy is safe. The Kelly fraction is computed from a win rate
with a standard error of about 4.5 pp; a 3.6%-of-bank stake sized off that is sized off noise.

### Tier

**TIER 1 (anomaly).** Model S's headline ROI does not clear its own declared noise ceiling at
any cell size, its p fails BH, the night-level mechanism it depends on is falsified on raw
production, the most recent third of the sample is negative, and the live-logged forward record
is flat. What *is* real - and it is a genuine finding - is the staleness gradient itself, which
is a **Tier 2 feature and a negative-EV standalone bet**.

---

## 3. C2 - SHARP GAP (bet toward Pinnacle when 1xbet differs by >= 1 pt, read <= 6h to tip)

### Coverage comes first, because it decides everything else

A Pinnacle prop line within 10h of a tip-6h read exists for **588 of 7,227 quotes (8.1%)**,
across 104 games. And the source changes mid-sample: **`pinn_board.csv`, a real board sweep,
only exists from 2026-08-21.** Everything before that is the `pinn` column of `bets_log.csv` -
i.e. only players the engine had already flagged. The pre-2026-08-21 half of C2's sample is
conditioned on the engine's own attention.

That split is the most alarming number in this section:

| sample | n | games | ROI | 95% CI |
|---|---|---|---|---|
| <= 2026-08-20 (engine-selected players) | 103 | 61 | **+20.1%** | [+3%, +35%] |
| >= 2026-08-21 (real Pinnacle board sweep) | 45 | 10 | **-20.4%** | [-51%, +12%] |

**The only unselected sample of C2 is negative.** It is 10 games, so it settles nothing on its
own - but it is the sample that most resembles how the rule would run.

### Headline and mechanism

|gap| >= 1.0, betting toward Pinnacle: **n=148, 71 games, 89-59 (60.1%), ROI +7.8%,
95% CI [-7.9%, +24.3%]**. The CI includes zero.

The mechanism is the strongest part of the claim and it **passes** (Law 6):

- rho(gap, actual - 1xbet line) = **+0.1229**, player-block permutation **p = 0.0085**, n=588.
- On the rows the rule actually bets, mean |actual - 1xbet line| = **5.439** vs
  mean |actual - Pinnacle line| = **5.003**. Pinnacle is measurably the better forecast on
  exactly those rows.

ROI permutation (gap reshuffled inside player blocks, direction following the shuffled gap):
**p = 0.0173**. Pre-specified live cell against its own single-cell null: **p = 0.0158**, null
median -6.9%.

### Noise ceiling for C2

Declared grid: 4 gap thresholds x 2 sharp horizons x 3 direction rules x 4 market groups = 96
cells, 23 reaching n >= 40.

- best REAL cell **+22.5%** (|gap|>=1, 6h, over-only, all markets)
- null best-of-grid: median **+10.8%**, **p95 +25.4%**, max +37.0%
- **The best real cell does NOT clear the ceiling.** Only the pre-specified live cell has a
  defensible p, and it has one *because* it was declared in advance.

### (a) Walk-forward and timing

| fold | dates | n | ROI | win rate |
|---|---|---|---|---|
| 1 | 06-24 .. 07-22 | 33 | +30.7% | 72.7% |
| 2 | 07-22 .. 08-11 | 46 | +13.8% | 63.0% |
| 3 | 08-11 .. 08-25 | 69 | **-7.3%** | 52.2% |

By month: Jun +66.2% (n=8), Jul +9.5% (n=39), Aug +2.5% (n=101). **Same decay shape as C1.**

Timing is load-bearing and fragile: the identical rule with the sharp line read 12h out instead
of 6h returns **-5.4%** (n=86). The claim only exists inside a narrow window, which is
consistent with a genuine staleness story and equally consistent with a fitted one.

### (c) Robustness

| threshold | n | games | ROI | win rate |
|---|---|---|---|---|
| |gap| >= 0.5 | 243 | 76 | +8.0% | 59.7% |
| |gap| >= 1.0 | 148 | 71 | +7.8% | 60.1% |
| |gap| >= 1.5 | 23 | 20 | +18.8% | 65.2% |
| |gap| >= 2.0 | 18 | 15 | +23.0% | 66.7% |

Stable at the usable end, unusably thin at the tight end.

Failures of robustness that matter:

- **Direction asymmetry.** over side n=41 **+22.5%**, under side n=107 **+2.1%**. The project's
  own claim was "+13.6% over / +12.4% under, both directions pay about the same". In this
  reconstruction they do not; the bulk of the volume is the flat side.
- **Scale.** A 1-point gap means different things at line 4.5 and line 24.5. Normalising
  (|gap|/line >= 5%) drops it to **+5.0%** on n=121.
- Market split: pts n=118 +12.6%; combos n=25 +6.7%; reb/ast n=5 -100% (thin).
- **Not the Model S signal wearing a hat**: removing the 23 bets that overlap a signal-firing
  player-market leaves n=125 at **+10.3%**. Genuinely independent of C1.

### (d) Execution stress

| | ROI |
|---|---|
| no slippage | +7.8% |
| 1c | +7.2% |
| 2c | +6.6% |
| 3c | +6.0% |

**Slippage to zero: 12.9 cents.** 10% missed entries -> +7.7%; 25% -> +7.7%.

The real execution constraint is not slippage, it is **availability**: the rule needs a
Pinnacle prop line <= 10h stale AND a two-sided 1xbet quote at the same line, inside a 6h
window. That combination existed on **8.1% of quotes** - roughly 2 bets per game night.

### (e) Bankroll

Flat 1u: final +11.48u over 148 bets, max drawdown **11.6u**, longest losing streak 5.
OOS win rate 56.5% at mean odds 1.799 -> full Kelly f = **0.021**. 1/4 Kelly = 0.5% of bank,
1/8 Kelly = 0.3%. P(50u drawdown on 100u) 0.0%, P(ruin) 0.0%.

The Kelly fraction is tiny because the OOS win rate is barely above break-even, and its standard
error is 4.6 pp - wider than the edge it is sizing. **Fractional Kelly here is indistinguishable
from flat staking**, and flat staking is the honest choice.

### Tier

**TIER 2 (promising).** In its favour: a confirmed, well-powered mechanism that survives BH
(p=0.0085), a pre-specified cell at p=0.0158, a 12.9-cent slippage margin, threshold stability,
and demonstrated independence from C1. Against it: the CI includes zero, fold 3 is negative,
the only unselected sample is -20.4%, the two directions no longer pay alike, the best cell
does not clear its grid ceiling, and it lives on 8.1% of the board. Not Tier 3 - Tier 3 needs
OOS survival, and C2's out-of-sample third has the wrong sign.

---

## 4. C3 - GAME-TOTAL GRADIENT

Data first: `gamelines.csv` starts 2026-07-11, so **only 50 games** carry a Pinnacle total.
Fifty is the independent n (Law 3), regardless of the 2,926 quotes sitting on top of them.

### The gradient depends entirely on which statistic you correlate

| statistic | rho | GAME-block label permutation p |
|---|---|---|
| actual (raw production) | +0.0819 | **0.0003** |
| actual - line | +0.0628 | 0.0450 |
| (actual - line) / player sd | +0.0627 | 0.0370 |
| over PnL at board price | +0.0474 | 0.2143 |
| **over_won (0/1)** | **+0.0201** | **0.4585** |

This is the whole story. **A higher total does predict more raw production - and the book has
already priced it.** The moment you measure against the line, the effect halves; the moment you
measure the thing you can actually bet, it is gone.

For the record, a quote-level shuffle on this game-level label gives p = 0.2602 on `over_won`
instead of 0.4585 - treating 2,926 quotes as 2,926 independent units. That is exactly the Law 2
mistake, and here it would have made the claim look about twice as strong as it is.

Pinnacle's total does forecast the score: rho(total, realised total) = **+0.4795** over 50
games. The forecasting skill is real; the betting edge is not downstream of it.

### ROI by total tercile (over side)

| tercile | n | games | over-rate | ROI | 95% CI |
|---|---|---|---|---|---|
| low (<173.2) | 918 | 19 | 50.7% | -5.3% | [-14.4%, +4.0%] |
| mid | 923 | 19 | 50.9% | -4.5% | [-14.3%, +4.8%] |
| high (>=181.0) | 1085 | 19 | 50.0% | **-6.8%** | [-14.7%, +0.6%] |

**Non-monotone, and the high tercile is the worst of the three.** The best cell in the whole
grid is -4.5% against a declared Grid-G ceiling of **p95 = +10.9%**.

Boundary perturbation makes it worse, not better - the tighter the cut, the more it loses:
top 50% -3.7%, top 40% -6.3%, top 30% -6.2%, top 25% -7.8%, **top 19% -11.1%**. A genuine
gradient sharpens when you cut harder. This does the opposite.

Walk-forward on top-tercile overs: -5.0%, +3.0%, **-18.2%**. Execution stress is moot; the cell
is -6.8% before any slippage and -8.3% after 3 cents.

### Tier

**TIER 0 (noise).** The tradable form of the gradient does not exist. What survives BH
(p=0.0003 on raw production) is the trivially true statement that high-total games produce more
counting stats, which is in the price. The project's logged rho of +0.074 at p=0.0165 is
reproducible only on line-relative production, not on `over_won` or on PnL.

---

## 5. C4 - VOLATILITY GRADIENT

The pooled result reproduces and looks strong:

- rho(relvol, standardised beat) = **-0.0305**, player-market label permutation within market,
  one-sided, **p = 0.0147**. Survives BH.

| relvol tercile | n | over-rate | over ROI | 95% CI | under ROI |
|---|---|---|---|---|---|
| low | 3017 | 51.3% | -4.5% | [-9.8%, +0.5%] | -9.4% |
| mid | 2321 | 51.6% | -3.6% | [-9.1%, +1.9%] | -10.4% |
| **high** | 1856 | 48.2% | **-9.6%** | [-15.1%, -4.1%] | -4.8% |

Then the confound check destroys it. **`relvol` is defined as sd / line.** A small line
mechanically inflates it, so "high volatility" is very largely "low line". Two tests:

**(1) Drop the scaling constant.** Using RAW sd instead of sd/line:
rho = **+0.0269, p = 0.5107** - the sign *flips* and significance vanishes. The direction of
this claim is set by the denominator, which is Law 9's "arbitrary scaling constant that sets the
bet direction", verbatim.

**(2) Stratify on line size.** Within every band the pooled direction reverses:

| line band | mean relvol | high-vol over ROI | low-vol over ROI |
|---|---|---|---|
| < 10 | 0.517 | -11.7% (n=1257) | **-17.0%** (n=525) |
| 10-16 | 0.445 | -11.1% (n=354) | -6.0% (n=678) |
| 16-22 | 0.398 | **+0.6%** (n=213) | -1.5% (n=850) |
| 22+ | 0.298 | **+20.9%** (n=32) | +0.6% (n=964) |

In three of four bands high-volatility players' overs do *better*, not worse. The pooled
negative gradient is Simpson's paradox on line size.

And even taken at face value the claim is not tradable. It says high-vol overs lose - they do,
-9.6%, but the whole board loses -5.5%. The only bettable form is the **under** on high-vol
players, which returns **-4.8%**, below break-even at every boundary tested (top 50% -6.4%,
top 40% -5.5%, top 33% -4.8%, top 25% -5.0%, top 20% -5.2%). Walk-forward on the under:
+3.4%, -9.5%, -7.5%.

### Tier

**TIER 0 (noise).** A scaling artifact that reverses inside every line band, with no profitable
side. The corroborating "3-point-reliance shot mix" result cited in the project notes should be
re-examined for the same confound: shot mix correlates with role, and role correlates with line
size.

---

## 6. MULTIPLE TESTING

"""
FOOT = """
The corrected family is the 24 p-values written down in `MODEL.md`, `CLV_HISTORY.md` and the
handoffs, plus the 16 computed in this audit: **40**.

**This is a lower bound and should be stated as one.** The repository holds **295 analysis
scripts**, most of which sweep dozens of cells and report only the winner; `mega_sweep.py`
alone prices 226 cells in one run. The brief's own DEAD list names 15 buried hypotheses that
left no p-value behind. Every unlogged test makes the thresholds below stricter, never looser.

Benjamini-Hochberg at q = 0.10 over the family of 40:

| test | p | BH crit | survives |
|---|---|---|---|
| C3 total gradient on raw production, unadjusted for the line | 0.0003 | 0.0050 | **YES** |
| C1 staleness gradient on RAW PRODUCTION (player-block perm) | 0.0007 | 0.0075 | **YES** |
| C1 staleness gradient on RAW PRODUCTION (game-block perm) | 0.0013 | 0.0100 | **YES** |
| C2 Pinnacle beats 1xbet at forecasting the box (player-block perm) | 0.0085 | 0.0125 | **YES** |
| C4 relvol gradient (player-market label perm within market) | 0.0147 | 0.0200 | **YES** |
| C2 sharp gap, live cell ROI | 0.0158 | 0.0225 | **YES** |
| C2 sharp gap ROI, |gap| >= 1 | 0.0173 | 0.0250 | **YES** |
| C1 starred-minus-raised contrast | 0.0375 | 0.0400 | **YES** |
| C1 Model S ROI > 0 (game-clustered bootstrap) | 0.0468 | 0.0425 | no |
| C3 total gradient on over PnL | 0.2143 | 0.0625 | no |
| C1 chronologically-clean player split | 0.2483 | 0.0675 | no |
| C3 total gradient on standardised beat | 0.3037 | 0.0700 | no |
| C1 signal night-specificity, ROI | 0.4263 | 0.0850 | no |
| C3 total gradient on over_won | 0.4585 | 0.0900 | no |
| C4 same gradient using RAW sd (confound removed) | 0.5107 | 0.0925 | no |
| C1 signal night-specificity, RAW PRODUCTION | 0.8705 | 0.1000 | no |

16 of 40 survive. **But read what survives.** Six of the eight named survivors are *mechanism*
tests on raw production, not profitability tests. Of the survivors:

- C3's is the tautology that high-total games produce more points.
- C4's is falsified by its own confound control (which is itself in the family, at p=0.51).
- C1's two staleness-gradient results are genuine but describe a **negative-EV** filter.
- **Only C2's two ROI tests are both significant and about money**, and they rest on a sample
  whose unselected half is -20.4%.

Bonferroni at alpha 0.05/40 = 0.00125 leaves exactly two survivors, both raw-production
mechanism tests: C3's tautology and C1's staleness gradient. **No profitability claim in this
project survives Bonferroni.**

---

## 7. VERDICT

| claim | ROI | n bets | n games | 95% CI | clears ceiling | mechanism | **tier** |
|---|---|---|---|---|---|---|---|
| C1 Model S staleness | +14.9% | 119 | 75 | [-2.9%, +32.2%] | **no** (88th pct of null) | gate YES, signal **FALSIFIED** | **1** |
| C2 sharp gap | +7.8% | 148 | 71 | [-7.9%, +24.3%] | live cell only | **YES** (p=0.0085) | **2** |
| C3 game-total gradient | -6.8% | 1085 | 19 | [-14.7%, +0.6%] | no | in the price already | **0** |
| C4 volatility gradient | -4.8% (under) | 1856 | 132 | n/a | no | **FALSIFIED** by confound | **0** |

**Track verdict: PROMISING BUT UNCONFIRMED, and the project's flagship claim does not survive.**

Model S is not an edge at this bar. Its ROI is below the median of its own grid's noise ceiling,
its p fails BH, the night-level mechanism it depends on is falsified on raw production, its most
recent third is negative, and its live-logged forward record is -1.5% on 17 bets. What is left
of C1 is a real but unprofitable filter.

C2 is the only claim worth carrying forward, at Tier 2. It has the one thing the others lack -
a confirmed, well-powered, independently-measurable mechanism (Pinnacle's prop lines are simply
more accurate than 1xbet's, MAE 5.003 vs 5.439, on exactly the rows the rule bets). It fails
Tier 3 on out-of-sample survival, and its cleanest sample is negative.

### What would actually settle this

The four claims share one weakness that no amount of re-slicing can fix: **the independent unit
is the game, and there are 132 of them.** Nine weeks of one season cannot separate a +8% edge
from zero when the per-bet standard deviation is ~130%.

1. **Run `pinn_board.csv` continuously.** C2's whole ambiguity is that its clean half is 10
   games. A full-board Pinnacle sweep on every slate turns C2 into a decidable question in
   about six weeks. This is the single highest-value change available.
2. **Grade C2 on CLV against the Pinnacle closing line**, not on results. At n=148 the win rate
   has a 4 pp standard error; closing-line value converges an order of magnitude faster and is
   the project's own stated proof standard.
3. **Stop logging Model S backfill rows alongside live ones.** The 85 replayed rows at +19.2%
   and the 17 live rows at -1.5% are not the same evidence, and pooling them is how a flat
   record reads as a 64% winner.
4. **Freeze the filter space.** The Grid-U table shows the search space is already wide enough
   that its best cell is beaten by noise 88% of the time. Any further filter hunting on 231
   candidate rows will find something, and that something will be a ceiling artifact.

### Reproduce

`t4_build.py` -> `t4_ceiling.py` / `t4_ceiling2.py` -> `t4_audit.py`, `t4_c1b.py`, `t4_c1c.py`,
`t4_c1d.py`, `t4_diag.py`, `t4_mv.py` -> `t4_c234.py`, `t4_follow.py`, `t4_c2ceil.py` ->
`t4_final.py` -> `t4_report.py`. Raw logs in `outputs/t4_*.txt`.
"""

h = HDR
for tok, val in (("@UN@", "%d" % ceil["gridU_n"]), ("@UC@", "%d" % ceil["gridU_cellcount"]),
                 ("@UM@", "%+.1f%%" % (100*ceil["gridU_med"])), ("@UP@", "%+.1f%%" % (100*ceil["gridU_p95"])),
                 ("@GN@", "%d" % ceil["gridG_n"]), ("@GC@", "%d" % ceil["gridG_cellcount"]),
                 ("@GM@", "%+.1f%%" % (100*ceil["gridG_med"])), ("@GP@", "%+.1f%%" % (100*ceil["gridG_p95"])),
                 ("@PN@", "%d" % ceil["gridP_n"]), ("@PC@", "%d" % ceil["gridP_cellcount"]),
                 ("@PM@", "%+.1f%%" % (100*ceil["gridP_med"])), ("@PP@", "%+.1f%%" % (100*ceil["gridP_p95"]))):
    h = h.replace(tok, val)
md = h + rows + BODY + FOOT
p = os.path.join(O, "tables", "prop_edge_audit.md")
open(p, "w", encoding="utf-8").write(md)
print("written", p, len(md), "chars")

CAND = {
 "generated": "2026-08-26",
 "track": "4 - player prop edge audit",
 "standard": "brief: no edge unless it survives rigorous OOS validation and realistic execution",
 "independent_unit": "game", "n_games": 132, "n_quotes": 7227,
 "board_economics": {"mean_over_odds": 1.880, "mean_under_odds": 1.862,
                     "implied_margin_pct": 7.56, "breakeven_win_rate_pct": 53.2,
                     "unfiltered_over_roi_pct": -5.5, "unfiltered_under_roi_pct": -8.5},
 "noise_ceilings": {
   "gridU_signal_filters": {"cells": ceil["gridU_cellcount"], "null_median_pct": round(100*ceil["gridU_med"],1),
                            "p95_pct": round(100*ceil["gridU_p95"],1),
                            "matched_size_note": "at min n=119 the null p95 is +21.4% and the best real cell is +14.8%"},
   "gridG_game_labels": {"cells": ceil["gridG_cellcount"], "p95_pct": round(100*ceil["gridG_p95"],1)},
   "gridP_player_labels": {"cells": ceil["gridP_cellcount"], "p95_pct": round(100*ceil["gridP_p95"],1)},
   "gridC2_sharp_gap": {"cells": 96, "p95_pct": round(100*c2c["c2_p95"],1),
                        "best_real_pct": round(100*c2c["c2_best_real"],1)}},
 "candidates": [
  {"id": "C2_sharp_gap", "name": "Sharp gap: bet toward Pinnacle when 1xbet's player line differs by >= 1 pt, sharp read <= 6h to tip",
   "tier": 2, "status": "PROMISING - do not size up", "market": "1xbet pre-game player props, both sides",
   "roi_pct": 7.8, "n_bets": 148, "n_games": 71, "win_rate_pct": 60.1, "ci95_pct": [-7.9, 24.3],
   "p_prespecified_cell": 0.0158, "p_mechanism": 0.0085, "survives_bh_q10": True, "survives_bonferroni": False,
   "walk_forward_roi_pct": [30.7, 13.8, -7.3], "sign_stable": False,
   "mechanism": "Pinnacle's prop line forecasts the box score better than 1xbet's on exactly the rows the rule bets: MAE 5.003 vs 5.439; rho(gap, actual - 1xbet line) = +0.1229",
   "slippage_to_zero_cents": 12.9, "roi_at_1c": 7.2, "roi_at_2c": 6.6, "roi_at_3c": 6.0,
   "roi_10pct_missed": 7.7, "roi_25pct_missed": 7.7,
   "bankroll": {"flat_1u_final_u": 11.48, "max_dd_u": 11.6, "longest_losing_streak": 5,
                "full_kelly_f": 0.021, "quarter_kelly_stake_pct": 0.5, "eighth_kelly_stake_pct": 0.3,
                "p_50u_dd_on_100u_pct": 0.0, "p_ruin_pct": 0.0},
   "kill_shots": ["the only unselected sample (>= 2026-08-21, real Pinnacle board sweep) returns -20.4% on n=45 / 10 games",
                  "walk-forward fold 3 is -7.3%",
                  "the two directions no longer pay alike: over +22.5% (n=41) vs under +2.1% (n=107)",
                  "sharp line read 12h out instead of 6h returns -5.4%",
                  "best cell in the C2 grid (+22.5%) does not clear that grid's p95 (+25.4%)"],
   "execution_caveat": "needs a Pinnacle prop line <=10h stale AND a two-sided 1xbet quote at the same line inside a 6h window; that combination existed on 8.1% of quotes, about 2 bets per slate",
   "recommended_action": "track forward on CLV vs the Pinnacle close, flat 1u, no size increase until pinn_board.csv has 40+ clean games"},
  {"id": "C1_staleness_gate", "name": "Gate 3 / Model S: book has not raised her line since her previous game",
   "tier": 1, "status": "ANOMALY - headline ROI does not survive", "market": "1xbet pre-game player props, over side",
   "roi_pct": 14.9, "n_bets": 119, "n_games": 75, "win_rate_pct": 62.2, "ci95_pct": [-2.9, 32.2],
   "p_roi": 0.0468, "survives_bh_q10": False, "survives_bonferroni": False,
   "walk_forward_roi_pct": [20.2, 36.4, -10.1], "sign_stable": False,
   "seasonal_decay": {"202607_pct": 20.1, "202608_pct": 6.9, "202608_second_half_pct": -2.9},
   "live_forward": {"shadow_live_rows": 17, "shadow_live_roi_pct": -1.5,
                    "shadow_backfilled_rows": 85, "shadow_backfilled_roi_pct": 19.2,
                    "model_forward_settled": 26, "model_forward_roi_pct": 6.5},
   "mechanism": "SPLIT. The gate gradient is REAL on raw production (rho -0.0390, player-block p=0.0007, game-block p=0.0013, n=6606/127 games; over-rate 54.3/50.4/48.7 for mv -1/0/+1) but the flip/hotover/overshoot signal that supplies the profit is FALSIFIED: on her own other gate-pass nights she beats the line by +0.213 sd, on signal nights +0.191 sd, diff -0.023, p=0.8705",
   "decomposition": {"gate_main_effect_pp": 4.4, "board_margin_pp": 7.6,
                     "gate_pass_standalone_roi_pct": -4.4, "gate_pass_ci95_pct": [-8.6, -0.3],
                     "signal_night_specificity_p": 0.4263},
   "slippage_to_zero_cents": 24.0, "roi_at_1c": 14.3, "roi_at_2c": 13.7, "roi_at_3c": 13.0,
   "roi_10pct_missed": 15.0, "roi_25pct_missed": 14.9,
   "bankroll": {"flat_1u_final_u": 17.74, "max_dd_u": 9.0, "longest_losing_streak": 6,
                "full_kelly_f": 0.145, "quarter_kelly_stake_pct": 3.6, "quarter_kelly_max_dd_pct": 29.0,
                "eighth_kelly_stake_pct": 1.8, "eighth_kelly_max_dd_pct": 15.4,
                "p_50u_dd_on_100u_pct": 0.0, "p_ruin_pct": 0.0},
   "kill_shots": ["+14.9% sits at the 88th percentile from the top of its own grid's null best-of-cell; noise beats it 88% of the time",
                  "at every matched cell size the best real cell is at or below the null MEDIAN",
                  "night-specificity p=0.4263 on ROI and 0.8705 on raw production",
                  "the timing effect runs +37.3pp / +19.0pp / -17.5pp across three chronological folds",
                  "live-logged shadow rows are -1.5% on 17 bets while backfilled replays read +19.2%",
                  "1xbet moves player lines in whole points only, so the 0.5 in the gate is a free parameter that does nothing"],
   "execution_caveat": "24c of slippage tolerance is generous, but the reconstruction cannot see bets that were unreachable by ping time; the 17 live rows carry that information and are flat",
   "salvage": "the staleness gradient itself is a genuine Tier-2 FEATURE (survives BH and Bonferroni) but a negative-EV standalone bet at -4.4%; use it as a filter input, never as a signal"},
  {"id": "C3_game_total_gradient", "name": "Higher Pinnacle game total -> better player overs",
   "tier": 0, "status": "DEAD - in the price already", "market": "1xbet player props, over side",
   "roi_pct": -6.8, "n_bets": 1085, "n_games": 19, "ci95_pct": [-14.7, 0.6],
   "p_over_won_game_block": 0.4585, "p_pnl_game_block": 0.2143, "p_raw_production": 0.0003,
   "survives_bh_q10": False,
   "walk_forward_roi_pct": [-5.0, 3.0, -18.2], "sign_stable": False,
   "mechanism": "the total forecasts the realised score (rho +0.4795 over 50 games) and forecasts raw production (rho +0.0819, p=0.0003), but the effect vanishes the moment it is measured against the line: over_won rho +0.0201 at game-block p=0.4585",
   "kill_shots": ["terciles are non-monotone and the HIGH tercile is the worst: -5.3 / -4.5 / -6.8",
                  "boundary perturbation makes it worse, not sharper: top 50% -3.7%, top 25% -7.8%, top 19% -11.1%",
                  "best cell -4.5% against a declared Grid-G ceiling of p95 +10.9%",
                  "only 50 games carry a Pinnacle total; a quote-level shuffle would have made it look twice as strong (p 0.26 vs 0.46)"],
   "execution_caveat": "not executable - the cell is negative before any slippage"},
  {"id": "C4_volatility_gradient", "name": "High-variance players' overs underperform",
   "tier": 0, "status": "DEAD - scaling artifact", "market": "1xbet player props, both sides",
   "roi_pct": -4.8, "n_bets": 1856, "n_games": 132,
   "p_relvol": 0.0147, "p_raw_sd": 0.5107, "survives_bh_q10": "pooled yes, confound-controlled no",
   "walk_forward_roi_pct": [3.4, -9.5, -7.5], "sign_stable": False,
   "mechanism": "FALSIFIED. relvol = sd / line, so 'high volatility' is mostly 'low line'. Replacing sd/line with raw sd flips the sign (rho +0.0269, p=0.5107) and stratifying on line size reverses the direction in 3 of 4 bands",
   "kill_shots": ["raw-sd version has the opposite sign at p=0.51",
                  "within line bands high-vol overs do BETTER: 22+ band high-vol +20.9% vs low-vol +0.6%",
                  "the only bettable side (high-vol UNDER) is -4.8%, below break-even at every boundary tested"],
   "execution_caveat": "not executable - no side of it clears the 7.6% margin",
   "follow_up": "re-check the 3-point-reliance shot-mix corroboration for the same line-size confound"}],
 "multiple_testing": {"family_size_used": 40, "logged_in_repo": 24, "computed_in_this_audit": 16,
   "true_family_larger": True,
   "note": "295 analysis scripts in the repo, most sweeping many cells and reporting the winner; mega_sweep.py alone prices 226 cells per run; the brief's DEAD list names 15 hypotheses with no surviving p-value",
   "bh_q10_survivors_named": 8, "bonferroni_survivors": 2,
   "bonferroni_survivors_are": ["C3 raw-production tautology", "C1 staleness gradient on raw production"],
   "key_reading": "six of the eight named BH survivors are mechanism tests on raw production, not profitability tests; only C2's two ROI tests are both significant and about money"},
 "not_executable_sections": {"brief_sections": "8-20, 22-23, 45",
   "reason": "live_lines.csv has no score, clock, period or possession column, and elo_model/plays_full.csv has zero game overlap with the 27 games carrying in-play odds"},
 "recommendations": [
   "run pinn_board.csv continuously - C2's clean sample is 10 games and a full-board sweep makes it decidable in ~6 weeks",
   "grade C2 on CLV vs the Pinnacle close, not on results; at n=148 the win rate has a 4pp standard error",
   "stop pooling backfilled shadow rows with live ones (85 replays at +19.2% vs 17 live at -1.5%)",
   "freeze the filter space - the Grid-U best cell is beaten by noise 88% of the time, so further hunting on 231 candidate rows will only find ceiling artifacts"]}
p2 = os.path.join(O, "candidate_strategies.json")
json.dump(CAND, open(p2, "w", encoding="utf-8"), indent=1)
print("written", p2)
