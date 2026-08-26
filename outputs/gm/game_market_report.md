# WNBA GAME-MARKET EDGE HUNT — FINAL REPORT

**Date:** 2026-08-26
**Dataset:** `outputs/gm/gm_dataset.csv` — 1,842 games, 2019–2026 (8 seasons), CLOSING lines from a ~10-book median (`elo_model/be_odds.csv`) joined to `games_full.csv` results and, for 2023–2026, to 987 games of `feats_v5` pre-game features.
**Scope:** three game markets — moneyline, point spread (ATS), game total (O/U). Read-only on the live prop pipeline; every script and file written under `outputs/gm/`.

---

## 0. ONE-PARAGRAPH SUMMARY

Nothing beat the close. The WNBA 10-book closing consensus is calibrated on all three dimensions — win probability (recalibration slope 1.0045, HL p=0.253), margin (slope 0.929, intercept −0.085), and total (slope 1.0155, bias +0.50 pts, t=1.30) — and across **563 pre-declared grid cells in three markets, ZERO cleared its own permutation noise ceiling**. Thirty-nine model specifications lost to the market benchmark in essentially every walk-forward fold (26 of 27 moneyline model-folds, 15 of 15 spread specs, 6 of 6 total folds). Ten blind strategies all return −4.3% to −6.1% against a 5.2–5.3% overround, i.e. every one is statistically indistinguishable from paying exactly the vig. The honest verdict on all three markets is **NO RELIABLE EDGE DETECTED**, and the most valuable durable output of this run is the calibration evidence itself: this market is a wall, and future effort should not be spent trying to out-forecast it.

---

## 1. VERDICT PER MARKET

| Market | Verdict | n priced | Blind ROI floor | Best surviving cell | Its ceiling |
|---|---|---|---|---|---|
| **Moneyline** | **NO RELIABLE EDGE DETECTED** | 1,829 | home −5.23%, fav −6.12%, dog −4.26% | +14.94% (n=98, M2-feats EV>1% home-only) | p95 = +34.97% — **below the null MEDIAN of +15.36%** |
| **Spread (ATS)** | **NO RELIABLE EDGE DETECTED** | 1,830 | home −5.13%, away −4.97%, fav −4.83%, dog −5.26% | +13.03% (n=65, elastic-net away edge≥4) | p95 = +24.61% |
| **Total (O/U)** | **NO RELIABLE EDGE DETECTED** | 1,830 | over −5.53%, under −5.55% | +14.84% (n=103, tm_over_rate_5≥0.80 FOLLOW) | p95 = +21.14% |

No cell in any market cleared its ceiling. Two came within 7pp of a ceiling and both had mirror-side cells losing symmetrically (the total's best FOLLOW cell +14.84% has a FADE mirror at −27.61%), which is the fingerprint of noise around the vig, not of signal.

**Grid accounting (all pre-declared before results were viewed):**

| Market | Families | Cells declared | Cells cleared |
|---|---|---|---|
| Moneyline | EV grid (150) + situational filters (52) | 202 | **0** |
| Spread | line-shape (26) + SpreadEdge (45) + model×filter (20) + situational (26) + EV-gated beta (15) | 132 | **0** |
| Total | model-edge (29) + filters (58) + regime (118) + env-gap (24) | 229 | **0** |
| **All** | | **563** | **0** |

---

## 2. IS THE CLOSING LINE CALIBRATED?

**Yes, on all three dimensions, to within statistical noise.** This is the durable finding.

### 2.1 Moneyline — calibrated as a probability

Logistic recalibration of the de-vigged closing home probability against realised home wins (n=1,829):

- intercept **+0.0019** (se 0.0533, t = +0.04)
- slope **+1.0045** (se 0.0591, t vs 1 = **+0.08**)
- Hosmer–Lemeshow, 10 equal-count deciles: **chi2 = 10.17, df = 8, p = 0.253**
- Market Brier **0.20063**, log loss **0.58613** (base-rate Brier 0.24722)

Reliability table — every bucket's Wilson 95% interval contains the market price:

| p bucket | n | mean p | realised |
|---|---|---|---|
| [0, 0.35) | 399 | 0.246 | 0.233 |
| [0.35, 0.45) | 237 | 0.398 | 0.435 |
| [0.45, 0.50) | 90 | 0.472 | 0.500 |
| [0.50, 0.55) | 115 | 0.530 | 0.504 |
| [0.55, 0.60) | 132 | 0.576 | 0.568 |
| [0.60, 0.65) | 154 | 0.627 | 0.623 |
| [0.65, 0.70) | 161 | 0.675 | 0.677 |
| [0.70, 0.75) | 149 | 0.725 | 0.745 |
| [0.75, 0.80) | 138 | 0.773 | 0.746 |
| [0.80, 1.0] | 254 | 0.859 | 0.858 |

Largest deviation is +3.7pp in [0.35, 0.45) — one bucket out of ten, exactly what chance delivers — and its home-side ROI of +3.45% has CI [−11.2, +18.8]. **No favourite–longshot bias:** the lowest bucket realises 23.3% against a 24.6% price (worth about a quarter of the vig) and the highest realises 85.8% against 85.9%.

Per-season recalibration slopes: 2019 0.897, 2020 1.105, 2021 1.164, 2022 1.100, 2023 1.078, 2024 1.132, 2025 0.786, 2026 0.959 — **not one is more than 1.76 se from 1.0, and there is no drift**.

### 2.2 Spread — unbiased as a margin forecast

Realised home margin regressed on market home margin (−spread), n=1,830:

- slope **+0.9292**, 95% game-bootstrap CI **[0.8523, 1.0038]** — H0 = 1 NOT rejected
- intercept **−0.085**, CI **[−0.699, +0.503]** — H0 = 0 NOT rejected
- mean ATS residual **−0.245 pts** (se 0.290, t = −0.85); home cover 48.85%
- the line's own RMSE against realised margin: **12.412 pts**, R2 0.2355, residual sd 12.41

Per-season home cover: 2019 54.4%, 2020 48.3%, 2021 48.5%, 2022 46.1%, 2023 54.2%, 2024 42.3%, 2025 50.3%, 2026 45.8%; per-season slope 0.83–1.06 straddling 1 in both directions. Per-season intercepts wander from +1.90 (2019) to −1.47 (2024) with no drift.

**The 12.41-point residual sd is the wall.** Even taking the slope point estimate at face value, the implied mispricing is worth about 0.02 sd of cover probability against a 2.63pp vig hurdle.

### 2.3 Total — unbiased and correctly scaled

Realised total regressed on the closing line, n=1,830:

- slope **+1.0155** (se 0.0566, t vs 1 = +0.27), CI [0.905, 1.126]
- intercept **−2.02** (se 9.22), CI [−20.1, +16.1]
- mean realised minus line: **+0.496 pts**, t = +1.30, **p = 0.193**, against residual sd 16.29
- market RMSE **16.40**

Per-season bias: 2019 +0.06, 2020 +0.29, 2021 −1.74, 2022 +0.05, 2023 +0.26, 2024 −0.09, 2025 +1.34, 2026 +3.36 (t = +2.62 — the only nominally significant season, discussed in section 4). Seven of eight are inside noise.

A +0.50 pt bias against sd 16.3 shifts the over rate by about +1.2pp, to 51.31%. **Breakeven at the quoted prices is 52.67%.** The bias is real in sign and roughly four times too small to pay the vig.

### 2.4 The overround — what any model must clear

| Market | Median two-way overround | Mean | Implied fair breakeven |
|---|---|---|---|
| Moneyline | 5.21% | 5.23% | 52.60% |
| Spread | 5.27% | 5.47% | 52.63% |
| Total | 5.34% | 5.60% | 52.67% |

All ten blind strategies land between −4.26% and −6.12% ROI. **No pooled CI excludes the overround.** Any model must clear roughly +5.3pp of ROI just to break even.

---

## 3. MODEL COMPARISON — DID ANYTHING BEAT THE MARKET?

**No. Not one specification, in any market, on any metric, in any fold — with a single 1-of-27 exception that is fewer than chance would produce.**

### 3.1 Moneyline — Brier / log loss, walk-forward by season (positive delta = WORSE than market)

| Model | Feature set | Folds | n | dBrier vs M1 | dLogLoss vs M1 |
|---|---|---|---|---|---|
| **M1 — de-vigged closing price** | — | — | 1,829 | **0 (benchmark 0.20063 / 0.58613)** | **0** |
| M2 market + elo + rest + b2b | own | 6 (2021–26) | 1,459 | +0.00131 | +0.00317 |
| M3 + form | own | 6 | 1,459 | +0.00217 | +0.00527 |
| M4 ridge, 11 cols | own | 6 | 1,459 | +0.00286 | +0.00710 |
| M5 HistGradientBoosting | own | 6 | 1,459 | +0.00927 | +0.02502 |
| Features WITHOUT market | own | 6 | 1,459 | +0.01246 | +0.02983 |
| M2 market + telo + rest + b2b + road | feats_v5 | 3 (2024–26) | 724 | +0.00280 | +0.00816 |
| M3 + form/pace/eff | feats_v5 | 3 | 724 | +0.00862 | +0.02351 |
| M4 ridge, all 30 clean features | feats_v5 | 3 | 724 | +0.00816 | +0.01879 |
| M5 gradient boosting | feats_v5 | 3 | 724 | +0.02423 | +0.06807 |

9 specifications x 9 folds = **27 model-fold cells; exactly ONE beat M1** (M2-feats, 2024, Brier −0.00177) — fewer than chance. **No fold of any model beat M1 on log loss.** Pooled OOS: M2-feats Brier 0.20836 / log loss 0.60541 vs M1's 0.20555 / 0.59725.

### 3.2 Spread — RMSE vs the closing line, walk-forward

| Model | 2024 | 2025 | 2026 | Pooled | Market pooled |
|---|---|---|---|---|---|
| **Closing line (benchmark)** | 10.84 | 13.36 | 13.17 | **12.49** | — |
| Elastic net + line, target margin (**best of 15**) | 10.95 | 13.37 | 13.20 | 12.53 | 12.49 |
| Elastic net, target ATS residual | — | — | — | 12.51 | 12.49 |
| Feature-only (no line) | — | — | — | 12.67 | 12.49 |
| HistGradientBoosting | — | — | — | 13.40 | 12.49 |
| Wide Elo model (2021–26, n=1,444, 6 folds) | — | — | — | 12.94 | 12.42 |

**All 15 specifications lose to the market in every fold.** OOS R2 on the ATS residual is negative for all 15 (−0.005 to −0.153) while the same features reach OOS R2 +0.10 to +0.25 on **raw** home margin — they forecast basketball well and forecast the market not at all.

### 3.3 Total — RMSE walk-forward, and residual R2

| Model | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Pooled |
|---|---|---|---|---|---|---|---|
| **Closing line (benchmark)** | 15.39 | 16.49 | 16.63 | 15.24 | 15.73 | 19.01 | **16.40** |
| Pace x efficiency score model | 15.86 | 16.83 | 16.82 | 15.30 | 16.02 | 20.67 | 16.91 |
| 50/50 blend with market | — | — | — | — | — | — | 16.55 |

**Worse in every one of six test seasons.** Encompassing regression `realised = a + b1*market + b2*model` gives **b1 = +1.101 (t = +9.56), b2 = −0.097 (t = −0.71)** — the model adds literally nothing the close does not already contain. Residual models: GBM OOS R2 −0.205 / −0.044 / −0.108 and ridge −0.003 / −0.005 / −0.007 for 2024 / 2025 / 2026. corr(model edge, realised residual): score −0.023, GBM +0.027, ridge −0.025.

### 3.4 OOS ROI of the best model in each market

| Market | Best model | Best EV-gated cell | n | ROI | CI | Ceiling | Clears |
|---|---|---|---|---|---|---|---|
| Moneyline | M2 on feats_v5 (a *worse* forecaster than M1) | EV>5%, both sides | 298 | +7.89% | [−8.55, +25.33] | +17.39% | No |
| Spread | elastic net + line | EV≥8% walk-forward | 116 | +6.16% | [−11.48, +23.54] | +15.70% | No |
| Total | score model / GBM-resid | edge≥5 UNDER-only | 135 | +8.58% | [−8.46, +25.49] | +15.25% | No |

**The best-model finding across all three markets is the same: the market benchmark IS the best model.** Every rival that showed positive ROI on a subset was demonstrably a worse probability or point estimator, which is the textbook signature of variance selection, not edge.

---

## 4. WHAT SURVIVED — RANKED

Nothing survived to a bettable state. Ranked by how close each came to being real.

### #1 — SpreadEdge to ATS-residual beta (the most dangerous false finding of the run)
- Feature model beta **+0.298** (se 0.128, **t = +2.33**, within-season permutation **p = 0.0044**); Elo model beta **+0.152** (se 0.075, t = +2.04, permutation p = 0.0160), **positive in 6 of 6 seasons** (sign test p = 0.0156).
- **It passed a permutation test AND a season sign test before dying.**
- EV-gated walk-forward: n=116, 55.17%, **ROI +6.16%**, CI [−11.48, +23.54], ceiling **+15.70%** — under ceiling.
- **Killed by four independent checks.** (1) *Trimming:* beta collapses as extreme edges are removed — feature model 0.298 → 0.219 (top 1% trimmed) → 0.161 (5%) → 0.106 (10%); Elo 0.152 → 0.161 → 0.162 → 0.083. Real information does not live only in the tail of a linear fit. (2) *Side disagreement:* the feature model's beta is carried entirely by away-lean games (+0.426 vs −0.139 home-lean); the Elo model's entirely by home-lean games (+0.248 vs −0.036). Two models cannot both be right about opposite halves of the sample. (3) *Controls:* adding market margin and |spread| drops t to +1.08 and +1.56. (4) *Chronology:* feature model +0.165 first half vs +0.497 second; Elo +0.201 vs +0.104 — moving in opposite directions. And the POOLED model, which should be strongest if the signal were real, is the WORST of the three (+2.18%, n=101).

### #2 — Big spreads go OVER (total market)
- Raw points: |spread| > 8.5 realises **+2.68 pts above the line, t = +3.66** (p = 0.0003), over rate 55.33%. The extra points come from the **underdog** (+1.89 vs implied, t = +4.03), not the favourite.
- **ROI +1.39%** (n=441), CI [−7.02, +10.21], ceiling +12.69% — far under.
- Folds: 2019 +19.61 (n=28), 2020 +2.49, 2021 −4.24, 2022 −12.59, 2023 +6.67, 2024 −0.67, 2025 −9.78, 2026 +25.78. **4 of 8 negative**; the pooled positive is 2019 and 2026 alone. Excluding 2026: **−1.65%**, raw bias falls to +1.97 (t = +2.56).
- **Dose–response falsified:** 8.5–11.5 → +4.00 pts (t = +3.92); 11.5–14.5 → +0.39 (t = +0.31); 14.5+ → +2.72 (t = +1.48). A genuine blowout mechanism should strengthen with spread size; this peaks and collapses.
- Cross-check: big favourites cover only 46.94% ATS, so the extra points are the dog's — an observation about the **spread** market, not a total edge.

### #3 — Big-spread dogs cover (spread market)
- |spread| ≥ 12 dog side: hit 55.09%, **ROI +3.08%** (n=216), CI [−9.89, +15.38], ceiling **+13.29%**. |spread| ≥ 14 dog +5.71% (n=117).
- Folds: 2019 −32.9 (n=14), 2020 −3.5, 2021 +9.5, 2022 +11.9, 2023 −0.5 (n=42), 2024 +26.7 (n=38), 2025 −12.5 (n=42), 2026 +13.0 (n=24). **Sign flips five times**; the point estimate is 2022 plus 2024.
- **Mechanism falsified:** favourite ATS regressed on favourite line size gives slope +0.0126 (se 0.0720, **t = +0.18**) — dead flat. Decile means of favourite ATS oscillate (−0.21, −0.99, −1.44, −2.32, −0.71, +0.22, +0.88, −2.03, −0.29, −1.66) with no monotone structure.

### #4 — 2026 totals running over
- 2026 raw bias **+3.36 pts, t = +2.62, p = 0.0094**, over rate 56.54%, rising through the year (May +0.85, Jun +4.10, Jul +5.08).
- **Blind OVER in 2026 still LOST money: −0.50% ROI** (n=214, CI [−12.33, +11.20]). The bias is a third of what is needed to clear the vig.
- In-sample by construction (current season); the null p95 of max|t| across 8 season tests is about 2.4, so t = +2.62 is barely the largest of eight coin flips. Every walk-forward rule that would have detected and traded the shift loses, **including inside 2026 itself (−6.69%)**.
- The market adapted on its own: 2026 lines average 169.26 vs 161.65 in 2025.

### #5 — Moneyline calibration bucket [0.35, 0.45)
- Home side +3.45% (n=237), CI [−11.2, +18.8]. One bucket in ten deviating by 3.7pp is the expected maximum under a perfectly calibrated null.

### #6 — Season cells (2025 home ML +5.97%, 2019 OVER +7.62%)
- Both are seasons, not strategies. 2025 home ML CI [−8.5, +20.3] against a +25.10% ceiling; 2019 OVER CI [−6.86, +21.26] against +12.69%. The negative tail is as deep as the positive tail is high (away 2019 −14.38%, home 2023 −12.70%).

---

## 5. WHAT DIED AND WHY

### Moneyline
| Hypothesis | Cause of death |
|---|---|
| A feature model can out-forecast the closing ML | 9 specs x 9 folds; **26 of 27 cells worse than M1**, every pooled fold worse. Own-Elo correlates +0.856 with the LINE vs +0.429 with the OUTCOME and −0.022 with the ATS residual — the close already contains the features. |
| Gradient boosting finds non-linear structure | M5 was the **worst** model in the study (+0.00927 / +0.02502 own; +0.02423 / +0.06807 feats), degrading in every fold. 250–810 training games against an already-priced target. |
| A worse forecaster still finds +EV where it disagrees most | Threshold curve non-monotone and mostly negative: M3own −17.8 → −10.5 across 0–5%; M4own −12.0 → −16.8. The one positive curve (M2-feats) belongs to a strictly inferior estimator. Best of 150 cells +14.94% vs p95 ceiling +34.97% — **below even the null median of +15.36%**. |
| Rest / back-to-back fatigue is priced slowly | Falsified on raw outcomes first. Home-b2b n=43, ATS residual −0.08 (se 1.99), 58.1% wins vs 55.8% priced; away-b2b n=59, −0.45 (se 1.44), 57.6% vs 58.4% priced. Rest differential t = +0.13 on the ML residual. About 100 b2b games in 8 seasons — unbettable even if real. |
| Injury/news is priced slowly (pnews, pstr) | pnews c = +0.0127, **t = +0.02, p = 0.981** (n=976); pstr c = −0.4021, t = −0.79, p = 0.430. The books already price the news. |
| Elo-vs-market disagreement identifies mispricings | c = +0.3380, **t = +0.74, p = 0.461**; best cell +1.24% (n=330) vs a +25.10% ceiling. |
| Longshot or favourite bias at the extremes | The reliability table kills it: 23.3% vs 24.6% priced at the bottom, 85.8% vs 85.9% at the top; slope 1.0045. Pooled dog ML −4.26%, favourite ML −6.12%. |
| A season / price band / venue split hides an edge | Best of 48 cells was a **season** (+5.97%, 2025) at under a quarter of ceiling; direction reverses in 2023 (−12.70) and 2024 (−9.08). |
| **Joint covariate test** | Logit `P(home) = a + b*market_logit + c*z` — five own features jointly: **chi2 = 0.82, df = 5, p = 0.976**. No single covariate reaches |t| = 1.0. |

### Spread
| Hypothesis | Cause of death |
|---|---|
| The closing spread is biased (slope ≠ 1 or intercept ≠ 0) | Slope CI [0.852, 1.004] contains 1; intercept CI [−0.699, +0.503] contains 0; mean residual −0.245 against sd 12.41. |
| Favourite–longshot bias: bet big dogs | Cell under ceiling (+3.08% vs +13.29%) AND mechanism flat (t = +0.18). Five sign flips across seasons. |
| A feature model out-forecasts the closing spread | 15 specs, 5 model classes, 2 targets, with and without the line. **All lose in every fold.** ATS-residual OOS R2 negative for all 15. |
| Non-linearity (GBM) | Worst model tested: RMSE 13.40 vs 12.49, residual OOS R2 −0.14. corr(edge, ats) +0.04 or negative. |
| Target the ATS residual directly | Best spec RMSE 12.51 vs 12.49, OOS R2 −0.005. The residual is white noise, so the model learns training-season sampling error. |
| Raising the SpreadEdge threshold concentrates edge | Curve runs the **wrong way**: feature model −5.44 / −7.08 / −4.83 / −6.64 / −3.99 at thresholds 1–5; Elo −0.94 / −2.76 / −4.01 / −6.37 / −5.83. Selectivity makes it worse — the model's biggest disagreements with a sharp close are its own biggest errors. |
| The SpreadEdge beta is real information | See section 4 #1 — four independent checks. |
| Schedule spots (b2b, rest mismatch, 3rd+ straight road game) | Home-b2b-vs-rested-away +0.44 (t = +0.18, n=32); away-b2b-vs-rested-home −1.05 (t = −0.62, n=50); home rest≥3 vs away≤1 −0.96 (t = −0.42, n=25); 3rd+ road game −0.29 (t = −0.25, n=132). |
| Recency overreaction (bounce-back / letdown after 20+ pt games) | Home off 20+ loss t = −1.51; away off 20+ loss t = −1.35; home off 20+ win t = +0.22; away off 20+ win t = +0.45. The two loss cells agree only because both favour the away side — a home-field artifact, not a bounce-back effect. |
| Win streaks are overpriced | Home streak≥3: +0.06 (t = +0.06, n=135); away streak≥3: +1.18 (t = +1.04, n=130). Best cell +4.12%, CI [−12.53, +20.75] vs ceiling +22.64%. |
| Rematch / familiarity, late season | Rematch within 14 days −0.47 (t = −0.82, **n=491**); late season −0.14 (t = −0.27, **n=575**). The two largest situational samples available, both dead flat. |
| Home underdogs undervalued | n=701, +0.60 (t = +1.24); home side −5.48%, away side −4.71% — **both sides losing symmetrically is the signature of a correctly priced split**. |
| Filters rescue the model edge | Family C, 20 cells, ceiling +18.83%. Best +3.28% (n=129) and favourite-side +2.37% (n=265). Filtering a dead signal produces dead cells. |
| Blowout / garbage-time dynamics | ATS residual sd by |spread| bucket: 12.10 / 12.90 / 12.68 / **11.14** — it FALLS at the extreme. corr(|spread|, |ats|) = −0.032; skew +0.10 / +0.03 / +0.05 / +0.07. Mean margin tracks the line in every bucket. No dynamic exists to exploit. |

### Total
| Hypothesis | Cause of death |
|---|---|
| Pace x efficiency beats the close | Worse RMSE in all 6 folds (16.91 vs 16.40); encompassing coefficient **−0.097 (t = −0.71)**; a 50/50 blend also loses. corr(model, market) = 0.85 while corr(edge, residual) = −0.023. |
| feats_v5 residual model (GBM / ridge) | OOS R2 negative in every fold. Structurally, most feats_v5 columns are **home-minus-away differentials**, near-useless for a sum; only pace_s and lgenv are sum-type and both are already in the line (lgenv corr +0.248 with the line, −0.030 with the residual). |
| Blowouts suppress totals | The sign is backwards (+2.68 pts OVER, t = +3.66), and the correct-direction version then failed dose–response and lost 4 of 8 folds. |
| Market lags the league scoring environment | All 11 prior-run signals correlate with the next residual at |t| < 1.1. Line-on-environment slope +0.517 (K=20) → +0.709 (K=100) — the book tracks it live. All 24 env-gap cells negative (−4.98% to −10.40%). |
| Totals mean reversion (fade a run) | The FADE side is symmetric-negative with FOLLOW = pure noise plus vig. **0 of 118 regime cells** cleared. Best FOLLOW cell +14.84% has a −27.61% mirror. |
| Rest / b2b move the total | Both-short-rest OVER −6.09%, both-long-rest OVER −4.42% — 1.7pp against a 5.3pp vig. The "one team on b2b" cell (+9.38%) is n=81, CI [−10.48, +28.52]. |
| 2026 up-shift is a tradeable regime | Blind OVER 2026 still −0.50%. Season-carryover rule pooled −5.85% (n=1,602 — exactly the vig); within-season lag rule pooled −10.44% (n=341, CI [−20.45, −0.14]) and −6.69% inside 2026 itself. |
| Very high / very low posted totals mispriced | All four line quartiles pay −3.28% to −7.05% (OVER) and −3.55% to −7.73% (UNDER), no monotone pattern. Slope CI [0.905, 1.126]. |
| **Thin book consensus leaks** (the structural analogue of the prop edge) | **Non-monotone and inverted.** Raw bias: 7–8 books −0.29 (t = −0.31); 9–10 books +1.29 (t = +2.09); 11+ books +0.27 (t = +0.46). The thinnest consensus leaks LEAST. All six cells negative. **This closes the last structural route inside this dataset.** |

---

## 6. FILTERS THAT MATTER vs FILTERS THAT ARE NOISE

**Filters that matter — they move raw outcomes, even though none pays:**
1. **|spread| > 8.5 on the total** — +2.68 pts over the line, t = +3.66, and the points are traceable to the underdog (+1.89, t = +4.03). Real in points, unstable in dose–response and across seasons, unprofitable at the price.
2. **lgenv tercile on the total** — the one filter with a monotone raw-points story: bias +1.81 / +1.34 / −0.64 across terciles. Best side pays +2.68%, below both ceiling and usable margin.
3. **Season** — genuinely different environments (2026 closing totals average 169.26 vs 161.65 in 2025), but this is a description, not a bettable filter; it is unknowable forward.
4. **Priced vs unpriced** — a data-integrity filter, not a betting one. See section 8.

**Filters that are noise — they select variance, not information:**
- Every rest / back-to-back cut in all three markets (n = 25–100, all |t| < 1.6).
- Win streaks, bounce-back, letdown, rematch, late season, 3rd-plus straight road game — all |t| ≤ 1.6, and the two biggest samples (rematch n=491, late season n=575) are the flattest of all.
- Home underdog (both sides lose symmetrically).
- Price and line buckets in every market — the calibration slopes near 1 rule these out globally before any cell is looked at.
- Pace terciles on the total (OVER ROI −7.69 / −5.31 / −4.66 low/mid/high — no bias at all).
- **n_bk_ou (book count)** — non-monotone and inverted relative to the staleness prediction.
- Any EV or model-edge threshold: the curves are non-monotone or run downward in all three markets.

**Rule extracted from this run:** a filter that improves ROI without also moving the raw-points or raw-cover mean in the same direction has been noise every single time here — six for six. Mechanism-before-ROI is not a formality in this dataset; it is the test that did all the killing.

---

## 7. GAME MARKET vs PROP SIDE — WHERE THE NEXT MONTH GOES

| | Prop board (1xbet) | Game markets (10-book close) |
|---|---|---|
| Overround | ~7.5% | 5.2–5.3% |
| Price quality | **Calibrated** — forecasting edges all died | **Calibrated** — forecasting edges all died |
| Line quality | **LEAKS** — stale player lines vs Pinnacle | No stale line; this IS the settled consensus |
| Cross-book divergence | Available, and it is the whole edge | **Unavailable** — only 14 games have both Pinnacle and 1xbet game lines |
| Surviving candidate | 1 (soft-vs-sharp staleness, n=45, Tier 2, unconfirmed) | **0** |
| Timing requirement | Bet the stale line before it moves | Would require getting the CLOSING price |

**The game-market side is emptier than the prop side, and it is empty for a structural reason, not a sample-size reason.** The prop finding transferred exactly: *the book's PRICES are calibrated; only its stale LINES leak.* On the game markets the price is calibrated — three independent calibration tests confirm it — and **there is no stale line to exploit**: a 10-book closing consensus at tip-off is the end state of price discovery, not a lagging quote. Every channel that leaks on the prop side is either absent here or tested and null:

- forecasting the outcome → dead on both sides (39 model specs here, all losing)
- slow injury repricing → tested here, p = 0.981
- slow rest / schedule repricing → tested here, all |t| < 1.6
- thin-consensus staleness → tested here, inverted
- **cross-book divergence → THE prop edge, and the one family this dataset CANNOT test**

**Recommendation: the next month goes to the prop side**, specifically to accumulating forward CLV on the soft-vs-sharp staleness signal toward its roughly 150-bet decision point. Do not spend it trying to out-forecast a 10-book close.

**The one game-market thread worth opening, and only if it is cheap:** capture a *single soft book's* WNBA game spread and total forward against Pinnacle, exactly as the prop pipeline already does for player lines. That is the one family this dataset could not test, and it is the only family that has ever survived in this project. It is an infrastructure task (forward capture), not an analysis task, and it must be judged by forward CLV, never by a backtest — this dataset contains no soft-book game lines to backtest it on.

**Do not bet the closing game markets from any model in this repo.**

---

## 8. HONEST LIMITATIONS

1. **These are CLOSING prices — the hardest possible test, and also the hardest to actually obtain.** Any edge found here would require getting the closing price, at a ~10-book median, on the side you want. In practice you get one book's number at one moment. An edge measured against this benchmark is a strictly harder claim than an edge measured against an opening line, and on the prop side we already know **every historical ROI in that repo is an opening-line number (OPEN +12.8% vs PING +4.0%)**. The two are not comparable and must never be quoted side by side.
2. **Sample size caps what could have been detected.** 1,829–1,830 priced games pooled; only **987** carry features (2023–2026); a walk-forward training on 2023–24 and testing on 2025–26 leaves about 470 test games. At those n, the smallest ROI a single cell can distinguish from the vig is large — which is exactly why the permutation ceilings sit at +13% to +35%. **A true edge of +2% to +4% ROI would be invisible in this dataset.** "No reliable edge detected" is not "no edge exists"; it is "nothing above roughly +13% ROI on a bettable subset exists, and nothing at all shows a surviving mechanism."
3. **The league changed underneath the data.** Expansion, roster size, and a materially different scoring environment: 2026 closing totals average **169.26** vs **161.65** in 2025, a 7.6-point shift in one year. Pooling eight seasons assumes a stability the league does not have; per-season splits fix that but cut n to 143–310, far too thin for a filtered cell. Both framings are reported throughout; neither is fully satisfying.
4. **Feature coverage is uneven and time-truncated.** 2019–2022 has odds but NO features; 2023–2026 has both; 2026 has only 163 of 214 games featurised because the feature build predates the recent games. Any finding concentrated in 2026 is partly a coverage artifact.
5. **`pnews` carries a soft look-ahead.** It is built from the game's own box score (re-weighting projected minutes onto players who logged ≥6 minutes), i.e. a proxy for the confirmed inactive list — normally known pre-tip but not guaranteed knowable at line-capture time. Quantified as harmless: orthogonalised against pstr it correlates +0.171 (t = +5.42) with the LINE, +0.123 (t = +3.88) with the OUTCOME, and only **+0.033 (t = +1.03) with the ATS residual**. Kept and used, but any future edge tracing back to pnews alone must be re-verified against a real pre-game injury feed.
6. **Two feats_v5 columns were REALISED RESULTS and were dropped.** `margin` and `total` correlate +1.0000 with realised home margin and game total, exact-equal on 100% of rows, and `build_feats.py` writes them as `home_score − away_score` and `home_score + away_score`. They are used as the regression TARGET in `mega_backtest.py` and `coach_pass.py`. They were renamed `f_margin` / `f_total` during the audit so they could not silently collide with be_odds `spread` / `total` on merge, then excluded entirely. **Any prior conclusion in this repo that used feats_v5 `margin` or `total` as a predictor is invalid.**
7. **Survivorship in which games have odds.** 229 games have a result but no closing odds, and they are a strongly non-random subset: **26.64% home win rate vs 55.28% for priced games (chi2 p = 5.1e-16)**, concentrated in 2020 (Bradenton bubble, 3.6% home wins), 2023 (6.3%) and 2026 (15.1%) — neutral-site games and slug-parse failures where the home label is nominal. This does not bias the analysis (unpriced games were never bettable, and the priced sample's home label is verified by the calibration itself: a home/away swap is irreconcilable with a slope of 1.0045), but **future work must not treat unpriced rows as a home-field sample.**
8. **11 rows were dropped for score disagreement, clustered in 2025–2026.** Ten rows where the be_odds score matches no games_full candidate for that matchup (mostly home/away-orientation errors or mis-scraped rows on the odds side) plus one with no matching key at all. They were dropped rather than force-matched. **If a future finding concentrates in 2025–2026, re-check that these exclusions are not doing the work.**
9. **Spread and moneyline are near-perfect substitutes** (measured rho = −0.998 on the prop side; here home_ml and home_spread agree on direction by construction). Nothing in this report counts a spread result and its ML twin as two pieces of evidence, and neither should any follow-up.
10. **Multiplicity is handled by pre-declared permutation ceilings, but the families themselves were chosen by a human.** 563 cells were declared before results were viewed; the *choice of which 563* was not itself randomised. The ceilings bound within-family selection, not the meta-selection of families.
11. **Base rates are live in this data and can masquerade as strategy:** home wins 55.3%, favourites win 68.6%, overs hit 51.3%. Any rule whose threshold happens to select mostly favourites or mostly overs is riding a fully-priced base rate.

---

## APPENDIX — FILES

**Data:** `gm_dataset.csv` (1,842 x 52), `gm_feature_audit.csv`, `gm_baseline.json`, `gm_ml_base.csv`, `gm_own_feats.csv`, `gm_preds.csv`, `gm_model_rows.csv`, `gm_modelB_rows.csv`, `gm_situ_rows.csv`, `gm_sp_work.csv`
**Build / audit:** `gm_build_dataset.py`, `gm_audit_leak2.py`
**Moneyline:** `gm_ml_01_calib.py` through `gm_ml_08_surv.py`
**Spread:** `gm_sp_calib.py`, `gm_sp_lineshape.py`, `gm_sp_model.py`, `gm_sp_eloB.py`, `gm_sp_edge.py`, `gm_sp_situ.py`, `gm_sp_final.py`, `gm_sp_betamech.py`, `gm_sp_familyE.py`
**Total:** `gm_tot_01_calib.py`, `gm_tot_02_model.py`, `gm_tot_03_edge.py`, `gm_tot_04_filters.py`, plus the downstream regime and environment scripts

All under `C:\Users\Axioo\wnba-line-capture\outputs\gm\`. Nothing in the live pipeline was modified.
