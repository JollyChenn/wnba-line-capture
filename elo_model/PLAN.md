# WNBA Player-Elo → Team Lines (ML / Spread / Total) — MASTER PLAN
*2026-07-11. Big multi-phase project. Build phase-by-phase, gate before advancing.*

## 0. Thesis & honest odds of success
Combine per-player ratings (weighted by projected minutes) into team strength → price margin, total,
win prob. The **only structural edge** vs the book: player-granularity reprices INSTANTLY on
injury/lineup news (team Elo lags a game or more; our capture already logs injuries+lineups every 30min).
We will NOT out-rate Pinnacle on stable rosters — the target is (a) stale soft-book lines around
roster news, (b) a knowledge base that feeds the prop signals.
Bar for "works": beats closing line (CLV), not just results, AND beats a dumb team-Elo baseline.

## 1. How others do it (what we steal)
- **FiveThirtyEight NBA Elo (team)**: K=20, home +100 Elo (~2.8 pts), margin-of-victory multiplier
  `((MOV+3)^0.8)/(7.5+0.006*elodiff)` (dampens blowouts + autocorrelation), season carry-over
  `0.75*rating + 0.25*1505`. → We steal: MOV multiplier, HCA as Elo, season regression.
- **CARM-Elo / RAPTOR (538 player)**: player plus-minus blend, team pregame = minutes-weighted player
  ratings; injuries handled by re-weighting minutes. → the aggregation blueprint.
- **DARKO (NBA)**: Kalman/exponential-decay per-box-stat forecasts, updated daily, then composited.
  → We steal: rate each *component* separately, then composite (more data-efficient at WNBA sample sizes).
- **Chess Elo/Glicko-2**: rating deviation (uncertainty) → high-K for rookies/low-minute players,
  shrinking with games played. → variable K.
- **Soccer club Elo / KenPom**: pace-adjust everything (points per possession, not per game).
  → totals need PACE as a separate team rating.

## 2. Rating engine (the core design)
Two ratings per player, updated per game, all **per-possession**:
- **O-Elo**: offensive impact. Expected = f(own O-Elo vs opponent lineup's minutes-weighted D-Elo).
  Actual = player's offensive value this game (see production score).
- **D-Elo**: defensive impact. Without play-by-play, defense is attributed via TEAM defensive result
  (opp pts/100 vs expectation) shared by minutes — noisy but unbiased; plus personal stocks (stl/blk)
  and opponent-position production if we can get matchup data later.

**Production score (offense), per 36, pace-adjusted** — the components the user named:
- Scoring volume: FGA + 0.44*FTA (true shot attempts)
- Efficiency: TS% vs league average, weighted by volume (eff on 20 attempts >> eff on 5) — i.e.
  points above league-average-efficiency on same attempts: `pts - lgTS%*2*(FGA+0.44*FTA)`
- Creation: AST (weighted ~0.7 pts each) − TO (~1.0 each = the "intercept/liability" term)
- Rebounding: OREB heavier than DREB (possession value ~0.7/0.3)
- (v2: shot quality — rim/3pt mix if shot-location data obtainable)
Composite → z-scored vs league per-36 distribution → expected-vs-actual drives the Elo delta.

**Update:** `new = old + K * minutes_factor * (actual_z - expected_z)`; K starts 32 (rookie,
high uncertainty) decaying to 12 (veteran, 60+ games), Glicko-style. Season rollover: 0.7*old + 0.3*mean.
MOV-style damper on blowout garbage time (clip performances beyond ±2.5 z).

## 3. Team aggregation → the three markets
1. **Minutes model** (secretly the hardest part): projected minutes per player from trailing usage,
   confirmed lineup (lineups_log.csv), injury status (injuries_log.csv), blowout-risk adjustment.
   Redistribution rule when a player is OUT: minutes flow within position group ∝ recent share.
2. **Team O/D strength** = Σ minutes-weighted player O-Elo / D-Elo (+ bench depth term).
3. **Margin (spread)**: `a*(homeO-awayD) - a*(awayO-homeD) + HCA` — fit `a`, HCA on history.
4. **Total**: pace rating per team (possessions/48, own Elo-like update) → possessions × combined
   efficiency expectation.
5. **ML**: margin → win prob via logistic fit (calibrate on history; WNBA ~margin/11 rule of thumb to verify).

## 4. Data plan (Phase 1 deliverable)
Have: 2026 box (min/pts/reb/ast/fga/fta/to), games+scores, halves, injuries_log, lineups_log (fwd),
two-sided odds capture (fwd). NEED:
- **Full box lines**: FGM, 3PM/3PA, FTM, OREB/DREB, STL, BLK, PF → ESPN summary API has them; extend
  the box collector + backfill 2026 from stored game_ids.
- **History**: 2023-2025 seasons via ESPN scoreboard→summary crawl (~200 games/season, gentle paced)
  → needed to fit calibrations + backtest. 3 seasons is the minimum credible sample.
- **Historical closing lines** (the hard one): we have NONE pre-06-24. Backtest therefore grades vs
  RESULTS for calibration, but the EDGE test is FORWARD vs our captured Pinnacle/1xbet closes.
  (Accept this: calibration≠edge-proof; the forward capture is the judge. Do NOT trust a
  results-only backtest as proof — that's the gold-bot lesson.)

## 5. Gates (per feedback_edge_methodology — every phase must pass to advance)
- G1 data: 3 seasons full boxes, <2% missing minutes, totals reconcile with final scores.
- G2 ratings sanity: top-10 O-Elo list passes the eye test (A'ja, Stewart, Wilson-tier on top);
  rating distribution stable, no drift explosion.
- G3 backtest (time-ordered, walk-forward): margin MAE ≤ baseline team-Elo MAE; win-prob Brier ≤
  team-Elo Brier. If player-level ≤ team-level, STOP (complexity unearned).
- G4 market test (forward only): paper-log model line vs captured close daily; need CLV>0 with n≥100
  games before any real consideration. Injury-window bets tracked as their own bucket (the thesis).
- Shuffle control at G3 (shuffle player-game assignment; edge must vanish).

## 6. Phases
1. **Data expansion** — extend box collector (full stat line), backfill 2023-2026. ~1 session.
2. **Elo engine** — player O/D-Elo over history, variable K, season regression. G2 check. ~1 session.
3. **Minutes model + aggregation** — projected lineups → team strengths. ~1 session.
4. **Calibration** — margin/total/ML fits, walk-forward. G3 vs team-Elo baseline. ~1 session.
5. **Forward paper loop** — nightly: ratings update → tonight's lines → log vs capture close →
   auto-grade CLV. Reuse the existing Actions infra (new workflow, ~5 min/day). ~1 session.
6. **Review at n≥100** — keep / kill / narrow-to-injury-windows.

## 7. Structure
`elo_model/` inside wnba-line-capture (reuses data/, capture, Actions): `collect_history.py`,
`engine.py` (pure functions, no pandas — platform._wmi gotcha), `minutes.py`, `calibrate.py`,
`predict_tonight.py`, `ratings.csv` (state), `elo_forward_log.csv` (the judge).

## 8. Known risks
- WNBA sample tiny (13 teams × 40 games) → variable-K + component ratings mitigate, expectations modest.
- Defense unmeasurable from our box → D-Elo is team-shared = weakest link; say so in outputs.
- Minutes model error dominates rating error on most nights.
- Books already price star injuries in seconds; our edge window is role-player/lineup-config news.
- Results-calibrated ≠ market-beating; only Phase-5 CLV counts (repeat of every prior project's lesson).
