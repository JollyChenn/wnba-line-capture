# TRACK 3 — Closing Line Value and the Pre-Game Market

Brief sections 6, 7, 34, 42. Hostile audit. Read-only on the live pipeline; every number below is
reproducible from the scripts in `outputs/clv/`.

**Verdict: NO RELIABLE EDGE DETECTED.**
Two confirmed *diagnostic* findings (sharp CLV predicts realised ROI; the Pinnacle game close is
sharper than the open), one confirmed *data-integrity* finding (the stored CLV columns do not mean
what their names say), and one plainly negative answer to section 42 (Model S shows **no** closing
line value — its "beat the close" number is its ROI restated). Nothing here is tradable.

Scripts: `outputs/clv/t3_step1.py` … `t3_step10.py`.
Independent-unit counts are given for every cell. The independent unit is the **game**.

---

## 0. What the stored columns actually mean (read from `grade_bets.py`)

`graded_bets.csv` is **not** a record of bets the project placed. It is a rebuild of `bets_log.csv`
— every signal the capture bot ever fired, real-money and paper alike — collapsed to one row per
`(game date, player, market, side)` and then deduped to **one bet per player per day** by highest EV
(cascade legs exempt). 1,025 rows, 1,025 decided, 20260614–20260825.

| column | definition in `grade_bets.py` | sign convention |
|---|---|---|
| `odds` / `line` | the **first** capture of that bet (earliest alert = "take on sight") | — |
| `odds_clv` | `our_odds / close_odds − 1`, where **close = the last capture still at OUR opening line**, and only if ≥2 captures exist at that line | >0 = our price beat that "close" |
| `line_clv` | our line vs `cl[-1]`, the **last line in `bets_log` for that bet** (not the board) | >0 = we got the better number |
| `sharp_clv` | our line vs the `pinn` line recorded alongside the last at-our-line capture | >0 = better number than Pinnacle |
| `sharp_odds_clv` | `our_odds / pinn_fair − 1`, `pinn_fair` = Pinnacle **vig-free** decimal at the last pre-tip snapshot, **only when Pinnacle's line equals ours** | >0 = we beat the sharp's fair price |

Two structural consequences, both material:

1. `odds_clv`'s "close" is **truncated at the moment the line moves**. It is a median **15.08 h**
   before tip (mean 36.0 h). In the 44.1 % of bets where the 1xbet line moved away from our number
   before tip, the stored "close" is a median **13.80 h earlier** than the true last quote.
2. `sharp_odds_clv` compares a **vigged** 1xbet price against a **vig-free** Pinnacle price. It is
   therefore ≈ −(half the board margin) by construction unless a real edge exists. Mean −7.26 %,
   positive on only 4.2 % of 262 rows. That is not a bug — it is the correct EV test — but it must
   never be read as "we are losing 7 % of CLV".

---

## 1. CLV distribution by family (stored columns)

n = rows with that column populated; beat% excludes exact ties.

| family | n | ROI% (game-block CI) | odds_clv % | n | beat% | line_clv pts | n | beat% | sharp_clv pts | n | sharp_odds_clv % | n | beat% |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **ALL** | 1025 | −6.6 [−12.2, −0.9] | −0.14 | 955 | 48.4 | −0.04 | 975 | 43.9 | +0.10 | 334 | **−7.26** | 262 | 4.2 |
| newunder | 353 | −13.3 [−23.0, −3.6] | −0.51 | 337 | 45.3 | −0.11 | 345 | 29.4 | +0.05 | 211 | −7.52 | 184 | 4.9 |
| cascade | 239 | −7.0 [−18.2, +4.2] | −0.18 | 224 | 43.8 | +0.01 | 230 | 57.9 | +3.67 | 6 | n/a | 0 | — |
| overshoot | 171 | +0.9 [−12.8, +14.7] | +0.11 | 154 | 48.1 | +0.03 | 155 | 56.7 | −0.14 | 7 | −5.75 | 10 | 0.0 |
| flip_paper | 122 | +4.8 [−11.6, +21.2] | +0.95 | 110 | 62.5 | +0.07 | 113 | 68.2 | +0.00 | 63 | −6.80 | 56 | 3.6 |
| flip | 47 | +2.7 [−24.0, +29.4] | −1.03 | 43 | 40.7 | −0.16 | 43 | 28.6 | −0.19 | 21 | −10.00 | 1 | 0.0 |
| model | 45 | −20.6 [−48.1, +7.0] | −0.39 | 43 | 40.0 | −0.18 | 44 | 41.7 | +0.27 | 15 | −5.95 | 8 | 0.0 |
| hotover | 36 | −1.2 [−32.3, +29.8] | +0.18 | 34 | 52.6 | +0.15 | 34 | 71.4 | −0.40 | 5 | n/a | 0 | — |
| starout | 12 | −23.1 [−76.9, +30.8] | +1.34 | 10 | 80.0 | −0.64 | 11 | 0.0 | +0.50 | 6 | −7.67 | 3 | 0.0 |

**The self-CLV columns are almost information-free**: `odds_clv` is *exactly zero* on 44.8 % of rows
and `line_clv` on 78.3 % (median of both = 0.000). 1xbet's prop board barely moves.

---

## 2. THE KEY DIAGNOSTIC — does CLV predict realised ROI?

### 2a. Sharp odds-CLV (vs Pinnacle's vig-free close): YES, confirmed

n = 321 bets over **142 independent games** (pts props only — the Pinnacle sidecar is 97 % pts).
Sharp close quote captured a median 2.31 h before tip.

**Noise ceiling, declared before results were read**: grid = 2 metrics (at-entry, at-close) × 3
populations (all/Over/Under) × 7 cells (5 quintiles + top/bottom half) = 32 live cells. Null =
permutation of outcomes across **game blocks**, 1,500 draws. Best-cell ROI under the null:
p50 **+19.1 %**, **p95 = +35.2 %**, p99 +43.7 %.

| quintile of sharp odds-CLV | metric % | ROI % | game-block CI | n | games | vs p95 ceiling |
|---|---:|---:|---|---:|---:|---|
| Q1 | −13.64 | **−23.0** | [−44.7, −0.7] | 64 | 50 | under |
| Q2 | −9.43 | −31.0 | [−52.1, −8.5] | 64 | 55 | under |
| Q3 | −7.23 | −12.5 | [−34.0, +9.1] | 64 | 51 | under |
| Q4 | −5.11 | −1.1 | [−23.3, +20.2] | 64 | 54 | under |
| Q5 | −0.72 | **+14.8** | [−9.0, +37.1] | 65 | 52 | under |

Monotone. **Spearman(sharp odds-CLV, pnl) = +0.213, game-block permutation p = 0.0005**
(2,000 draws; Bonferroni ×6 for the metric×population grid still p ≈ 0.003).
Across families the relationship is almost mechanical: corr(sharp odds-CLV, ROI) = **+0.985**
(k = 4 families with ≥8 sharp-referenced bets) — newunder (−7.38 % → −15.8 %), flip_paper
(−7.08 % → −3.9 %), overshoot (−5.74 % → +14.2 %), model (−5.14 % → +31.4 %).

**Interpretation.** Pinnacle's vig-free fair price is a near-unbiased forecast of these props.
Aggregate: sharp CLV said −7.3 %, the board realised −6.6 %. This *validates CLV as the project's
proof standard* — but only against Pinnacle, and it is a **post-hoc diagnostic**: it uses the
near-tip sharp price, which is not known at entry.

### 2b. The executable version (sharp fair price **at the entry instant**): NOT confirmed

Gate and price at the same instant. n = 225 over 108 games; entry-time sharp quote staleness median
0.00 h (contemporaneous).

| quintile | metric % | ROI % | CI | n | games |
|---|---:|---:|---|---:|---:|
| Q1 | −13.38 | −20.2 | [−44.5, +5.2] | 45 | 34 |
| Q2 | −8.63 | −0.6 | [−27.3, +24.7] | 45 | 39 |
| Q3 | −7.21 | −38.0 | [−64.6, −11.9] | 45 | 37 |
| Q4 | −5.66 | +0.8 | [−27.2, +29.3] | 45 | 37 |
| Q5 | −2.04 | **−2.4** | [−28.6, +27.1] | 45 | 39 |

Non-monotone, and the *best-priced* quintile loses money. Spearman +0.119, permutation p = 0.0285 —
which does not survive the ×6 grid correction. **The tradable form of the sharp-price signal is not
supported.** Almost all of the sharp CLV→ROI relationship lives in information that only arrives
after entry.

### 2c. Self-CLV (1xbet vs itself): a gradient, but not enough to clear the vig

Bet-level, using the **independently recomputed** line drift (see §3), game-block CI:

| bucket | n | games | ROI % |
|---|---:|---:|---|
| line moved AGAINST us | 135 | 90 | −16.7 [−32.7, −1.0] |
| line unchanged | 438 | 151 | −7.4 [−15.5, +0.7] |
| line moved TOWARD us | 261 | 124 | **+1.1** [−10.9, +12.5] |

Correct ordering, so soft-book line movement does carry information. But **even the best bucket only
reaches breakeven**: on a ~7 % board margin, winning the line move buys you back the vig and nothing
more. Across families, corr(line-CLV, ROI) = **−0.013** — there is no family-level relationship at all.

### 2d. Quadrant map

| quadrant | families | reading |
|---|---|---|
| **+ROI, no CLV → scepticism** | `flip` (+9.6 %), `overshoot` (+5.8 %), `flip_paper` (+3.6 %), **Model S** (+16.9 %) | line CLV ≈ 0 (+0.05 to +0.46 pts); sharp CLV −5.7 to −7.2 % (Pinnacle prices them as *negative* EV). Positive ROI with no market confirmation. |
| **−ROI, +line CLV → artifact** | `cascade` (line CLV **+1.59 pts**, ROI −10.9 %) | betting into a star-out line that is rising anyway makes line CLV mechanical, not skilful. Positive CLV here is a coverage artifact of *when* the bet fires, not evidence. |
| **−ROI, −CLV → consistent** | `newunder` (−12.8 %, sharp CLV −7.38 %), `model` unders (−22.4 %) | market and outcomes agree. Correctly retired (unders, −95.61u). |
| **+CLV, weak ROI → keep researching** | **none** | no family in the book has positive CLV on any flavour. |

---

## 3. Independent recompute from `xbet_board.csv` — do the two agree? **No.**

Rebuilt from the raw board: entry = the ping in `bets_log`; close = the **last two-sided quote before
tip**, at our line for the price and at whatever line the board ended on for the number.
834 rows over **159 independent games**.

| family | n | games | stored odds_clv % | **independent** odds_clv % | stored line_clv | **independent** line_clv | EV vs 1xbet vig-free close % | ROI % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ALL | 834 | 159 | −0.18 | −0.00 | −0.06 | **+0.44** | −7.03 | −6.2 |
| newunder | 316 | 136 | −0.55 | −0.14 | −0.13 | +0.13 | −7.36 | −12.8 |
| cascade | 145 | 58 | −0.29 | **−2.08** | −0.02 | **+1.59** | −8.73 | −10.9 |
| overshoot | 144 | 95 | +0.07 | −0.18 | +0.03 | +0.46 | −6.85 | +5.8 |
| flip_paper | 118 | 81 | +1.01 | +1.51 | +0.07 | +0.29 | −5.86 | +3.6 |
| flip | 39 | 38 | −1.22 | −0.39 | −0.23 | +0.05 | −7.21 | +9.6 |
| model | 34 | 32 | −0.48 | −0.49 | −0.18 | −0.12 | −7.19 | −22.4 |
| hotover | 27 | 24 | −0.00 | +1.05 | +0.16 | +0.26 | −5.49 | −10.5 |
| starout | 11 | 8 | +1.34 | +1.33 | −0.60 | −0.55 | −5.62 | −16.1 |

- **odds-CLV**: correlation stored↔independent = **+0.778**, exact agreement on only **176/708 = 24.9 %**.
- **line-CLV**: exact agreement 553/794 = 69.6 %; **mean stored −0.059 pts vs independent +0.444 pts** — a
  sign flip at the aggregate level, and a full 1 point apart on `cascade`.

**Which is right? The independent recompute.** Two reasons:

1. The stored close is the last capture *still at our opening line*, so it is censored exactly where
   the interesting movement is; it sits a median 15.1 h before tip, and 13.8 h earlier than the true
   last quote whenever the line moved.
2. The stored line-CLV walks `bets_log`, which only records a line **when a filter fires**. That is a
   signal-triggered, censored sample of the line's history — not the line's history. The board has the
   full series.

**But even the independent number is not a close.** The true last 1xbet quote before tip is a median
**9.63 h** early for the graded population, and the situation is deteriorating:

| month | n | median hours from last quote to tip | within 2 h | within 6 h |
|---|---:|---:|---:|---:|
| 2026-06 | 83 | 4.67 | 23 % | 58 % |
| 2026-07 | 362 | 7.70 | 19 % | 44 % |
| 2026-08 | 392 | **12.13** | **9 %** | 24 % |

By market: `pts` median 12.28 h (5 % within 2 h), `pra` 3.64 h, `pr` 6.46 h, `pa` 4.31 h.
**Operational conclusion: on the current capture cadence the project's own stated proof standard is
not measurable for its main market.** (Stated as an observation only — nothing in the live pipeline
was touched.)

---

## 4. The pre-game GAME market (`gamelines.csv`)

220 matchups captured 2026-07-11 → 2026-08-26, median 104 rows/matchup (alt ladders included; the
"main" line is taken as the ladder rung with the most balanced two-sided price). 216 matchups linked
to a final score; usable open→close series for **111 spread games / 114 total games**. First capture
median 19.9 h before tip, last capture median **0.25 h** before tip (85 % inside 1 h) — unlike the
prop board, this **is** a genuine close.

Magnitude of movement: spread mean |line move| **1.04 pts** (unchanged 15 %), mean |price move| 1.81 %;
total mean |line move| **1.41 pts** (unchanged 16 %), mean |price move| 1.31 %.

### 4a. Does movement predict the *close*? No — it mean-reverts.

corr(move open→T−6h, move T−6h→close):
- spread **−0.211**, t = −2.29, n = 115 games
- total **−0.177**, t = −1.92, n = 115 games

Mean |open→T−6h| 0.88 pts vs mean |T−6h→close| 0.66 pts (spread). Early movement is partially given
back. This is the mechanism that kills momentum below.

### 4b. Does movement predict the *result*? Yes — the close is sharper than the open.

Diagnostic only (uses the close to pick the side, grades against the **opening** line):

| market | threshold | side the line moved toward beat the OPEN line | rate | 95 % CI | binomial p |
|---|---|---|---:|---|---:|
| spread | \|move\| ≥ 0.25 | 59/95 | **62.1 %** | [52.1, 72.2] | **0.0117** |
| spread | \|move\| ≥ 1.00 | 33/53 | 62.3 % | [48.8, 75.7] | 0.0492 |
| total | \|move\| ≥ 0.25 | 55/99 | 55.6 % | [45.7, 65.4] | 0.1574 |
| total | \|move\| ≥ 1.00 | 47/77 | **61.0 %** | [49.9, 72.2] | 0.0338 |

Games are the independent unit and each game contributes one observation, so the binomial is the right
null here. **Closing line value is a real phenomenon in Pinnacle's WNBA game markets.** Supporting
calibration: corr(closing total, realised total) = **+0.459** (n = 118, mean close 176.3 vs realised
178.1); corr(closing spread, realised margin) = **+0.521** (mean implied 1.8 vs realised 1.4).
Naive close-following baselines are all noise: first-listed ML −3.0 % [−19.9, +14.4], main total OVER
+1.6 % [−14.7, +19.3], first-listed spread +7.6 % [−10.3, +24.4].

### 4c. Is any of that executable? No.

Observe the move open→T−6h, bet that direction **at the T−6h price and line** (gate and price at the
same instant, no future information).

**Noise ceiling, declared first**: grid = 2 markets × 3 thresholds × 2 directions = 12 cells.
Null = the direction the line moved is independent of which side wins → flip the bet side per game,
keeping cell membership and the real two-sided prices. 4,000 draws.
Best-cell ROI under the null: p50 +14.5 %, **p95 = +33.1 %**, p99 +40.6 %.

| market | thr | dir | n games | ROI % | CI | vs ceiling |
|---|---:|---|---:|---:|---|---|
| spread | 0.5 | follow | 85 | −2.1 | [−22.6, +18.5] | under |
| spread | 0.5 | fade | 85 | −5.7 | [−25.8, +14.5] | under |
| spread | 1.0 | follow | 52 | +8.5 | [−18.0, +34.9] | under |
| spread | 1.0 | fade | 52 | −15.9 | [−41.5, +10.0] | under |
| spread | 1.5 | follow | 33 | +12.3 | [−21.9, +45.9] | under |
| spread | 1.5 | fade | 33 | −19.3 | [−53.5, +11.0] | under |
| total | 0.5 | follow | 98 | +2.7 | [−16.5, +20.5] | under |
| total | 0.5 | fade | 98 | −13.2 | [−32.4, +6.0] | under |
| total | 1.0 | follow | 71 | +9.7 | [−11.8, +31.2] | under |
| total | 1.0 | fade | 71 | −20.0 | [−41.5, +1.9] | under |
| total | 1.5 | follow | 47 | **+13.0** | [−11.7, +37.8] | under |
| total | 1.5 | fade | 47 | −23.3 | [−48.0, +4.6] | under |

**Best real cell +13.0 % vs p95 ceiling +33.1 % — does not clear.**

One residual thread worth naming honestly: `follow` beats `fade` in **6/6** pairings, and the paired
within-game contrast (same game, same instant, follow-minus-fade — removes all game-level noise) is
positive everywhere:

| market | thr | n games | follow − fade | CI | t | sign-flip p |
|---|---:|---:|---:|---|---:|---:|
| spread | 0.5 | 85 | +3.6 % | [−37.5, +44.7] | +0.17 | 0.416 |
| spread | 1.0 | 52 | +24.4 % | [−28.1, +76.8] | +0.91 | 0.167 |
| spread | 1.5 | 33 | +31.6 % | [−34.4, +97.6] | +0.94 | 0.156 |
| total | 0.5 | 98 | +15.9 % | [−21.7, +53.5] | +0.83 | 0.190 |
| total | 1.0 | 71 | **+29.6 %** | [−14.3, +73.5] | +1.32 | **0.088** |
| total | 1.5 | 47 | +36.2 % | [−17.6, +90.1] | +1.32 | 0.095 |

Every CI includes zero and no p clears 0.05 on a 12-cell grid. At n = 47–98 games this is
**inconclusive, not an edge**. It is also fighting the −0.18 to −0.21 mean reversion measured in §4a,
so the prior should be poor. Revisit at ~300 games, not before.

---

## 5. Section 42 — does Model S contain information not already in the price?

Populations: `shadow_forward.csv` config `MODEL_S` (102 settled, 101 matched to a closing quote,
**76 independent games**; markets pra 44 / pr 36 / pts 21), `model_forward.csv` (the live record,
26 settled / 25 matched, 18 games), and a Model-S-shaped slice of `graded_bets.csv` (286 matched,
134 games). Expected wins = the vig-free P(over) implied by the last two-sided 1xbet quote before tip,
**at our line**.

| population | n | games | actual hit | closing line implies | **beat-close delta** | block CI | realised ROI |
|---|---:|---:|---:|---:|---:|---|---:|
| shadow MODEL_S | 101 | 76 | 63.4 % | 50.7 % | **+12.7 pp** | [+2.9, +22.0] | +16.9 % [−1.2, +33.7] |
| live model_forward | 25 | 18 | 56.0 % | 50.3 % | +5.7 pp | [−15.8, +27.5] | +3.9 % [−38.9, +45.4] |
| graded Model-S-shape | 286 | 134 | 57.3 % | 50.8 % | +6.3 pp | [+0.4, +12.2] | +6.0 % [−4.6, +16.9] |

At face value this looks like the strongest evidence in the project. **It is not evidence at all.**
Three reasons, in order of severity:

**(i) The delta is the ROI restated, not a separate fact.** The 1xbet prop line for the Model S
population is *unchanged* 88 % of the time (mean move **+0.069 pts**; |move| ≥ 0.5 in 12 %), and the
vig-free P(over) at our line drifts a mean of **+0.41 pp** open→close. So:

| reference | implied P(over) | Model S delta | block CI | Bernoulli-null p |
|---|---:|---:|---|---:|
| 1xbet **OPEN** vig-free at our line | 50.3 % | **+13.1 pp** | [+3.3, +22.2] | 0.0057 |
| 1xbet **CLOSE** vig-free at our line | 50.7 % | **+12.7 pp** | [+2.9, +21.8] | 0.0070 |

Model S beats the open and the close by the *same amount*. Arithmetic check: hit-rate 63.4 % × mean
odds 1.845 − 1 = **+16.9 %**, and mean vig-free P(over) at close 50.7 % against mean closing OVER
decimal 1.842. In a market that does not move, "beat the close" and "positive ROI" are one statistic
in two units. **There is no closing line value here — only a backtested ROI.**

**(ii) Model S selects on non-movement.** Gate 3 requires the book to have *not raised* the line versus
her previous game. The filter therefore preferentially admits static lines, which guarantees a
near-zero line-CLV measurement. Self-CLV cannot falsify a strategy that is defined partly by the line
not moving.

**(iii) The one test that would count has never been run, and cannot be run on this data.** Against
the **sharp** close (Pinnacle vig-free fair, same line), only **8 Model S bets over 7 games** have a
reference at all — Model S is pra/pr-heavy and the Pinnacle sidecar is 97 % pts:

- Pinnacle close implies 49.6 %; Model S actual 50.0 %; **beat-the-sharp-close delta +0.4 pp
  [−37.3, +37.1], Bernoulli p = 0.6306**
- sharp odds-CLV **−7.73 % [−10.03, −5.28]**; realised ROI on that subset −6.9 % [−73.7, +63.9]

n = 8 is uninformative about the strategy — but it is decisive about the *evidence base*:
**the strongest available proof of Model S has never been attempted, because the sharp reference does
not cover the markets Model S bets.** The stored `sharp_odds_clv` column being blank on 74 % of
`graded_bets` is the same gap.

**Plain answer to section 42.** No. Model S bets do **not** systematically beat the closing prop line
in any sense that is independent of their realised ROI, and against the only sharp reference available
they are priced at −7.7 % EV. The +16.9 % backtest and the +6.8 % live ROI on 21–26 settled bets remain
**unconfirmed by any market-based evidence**. Given the project's own history (verdict revised five
times downward in one day) the correct posture is that Model S is an unvalidated ROI claim, not a
CLV-proven edge.

---

## 6. What would actually settle it

1. **Extend the Pinnacle sidecar to pra / pr.** Model S lives in pra/pr; the sharp reference is 97 %
   pts. Until that gap closes, no amount of forward Model S bets can be CLV-tested. This is the single
   highest-value change available and it is a *capture* change, not a modelling one.
2. **Capture 1xbet inside T−30min.** August's median last quote is 12.1 h before tip; 9 % of bets have
   a quote inside 2 h. "CLV" measured 12 hours out is not CLV.
3. **Stop using `odds_clv` / `line_clv` as evidence.** They agree with an honest recompute 25 % / 70 %
   of the time and their "close" is a censored, signal-triggered sample. Recompute from
   `xbet_board.csv` (§3), or drop the claim.
4. **Report the sharp odds-CLV distribution, not its mean.** The mean is −(half the margin) by
   construction; the *quintile* of it is what predicted ROI (§2a).

## 7. Failed / falsified hypotheses (recorded, not hidden)

- Executable at-entry sharp-price EV as a bet filter — non-monotone quintiles, top quintile −2.4 %.
- Pre-game spread/total **momentum** (follow the open→T−6h move at T−6h) — best cell +13.0 % vs a
  +33.1 % ceiling; and open→T−6h movement mean-reverts (corr −0.211 / −0.177).
- Pre-game **fade** of the move — negative in all six cells (−5.7 % to −23.3 %).
- Naive close-following baselines (home ML, main total over, first-listed spread) — all CIs span zero.
- Family-level line-CLV as a ROI predictor — corr −0.013 across seven families.
- `cascade`'s +1.59 pt line CLV as evidence of skill — mechanical (betting into a rising star-out
  line), and its ROI is −10.9 %.

## 8. Sections not executable on this data

None of sections 6, 7, 34, 42 required in-play state, so Track 3 is fully executable — unlike brief
sections 8–20, 22–23 and 45, which are dead because `live_lines.csv` has no score/clock/period column
and its 27 in-play games have zero overlap with `elo_model/plays_full.csv`.
