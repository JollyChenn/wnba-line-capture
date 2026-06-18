# WNBA LINE-CAPTURE BOT — SESSION HANDOFF
_Last updated: 2026-06-18. Repo: JollyChenn/wnba-line-capture (all on `main`). Runs on GitHub Actions (laptop-off)._

> **READ THIS FIRST.** This is the live WNBA player-prop bot. It is **UNPROVEN forward → paper/tiny only**. The account is **READ-ONLY; NEVER auto-bet 1xbet** (bot activity = account freeze). The one real proof of edge is **forward CLV**, not backtests.

---

## 0. TL;DR — the honest state
- **The edge thesis:** soft-book (1xbet) line **staleness** — grab a stale price before the sharp market moves it. It is a **timing** edge, proven by **CLV** (entry price vs close), NOT by hit-rate or P&L.
- **Status: NOT proven.** First real settlements (G6-17) went **2/3 on results but −4.6% ODDS-CLV** — i.e. we're getting *worse* prices than the close, the opposite of the edge. n=3, far too small to conclude, but it echoes the NBA cousin (−6%).
- **Everything is paper/tiny** until ~2 weeks of **positive** forward CLV. The NBA version of this bot got −6% CLV and never proved out — same risk here.
- **The recurring trap (learned hard this session):** a backtest vs a **trailing-median proxy line** manufactures fake 55-63% rates on right-skewed/low-integer stats (assists, 3pm, totals). Beating the proxy ≠ beating a book. Only CLV settles it.

---

## 1. THE 5 GITHUB WORKFLOWS (`.github/workflows/`)
| Workflow | Schedule (UTC) | Does | Pings? |
|---|---|---|---|
| **capture-xbet** | every ~30 min, off-peak mins :13/:43 (14:00-02:00) + every-3h | **THE HEART** — `cloud_xbet.py`: pull 1xbet lines (48h window) + injuries + Pinnacle, apply signals, log to `bets_log.csv`, ping Discord | ✅ **sole ping source** |
| **daily-picks** | 14:00 daily | `daily_picks.py`: refresh box scores, generate model picks → `picks_log.csv`, validate, commit | ❌ **ping disabled** (commit 049a6d8) |
| **grade-bets** | 15:00 daily | `grade_bets.py` → settle bets + CLV → `graded_bets.csv`; `clv_reader.py` → CLV verdict ping | ✅ CLV record |
| **cascade-watch** | every 20 min, game hrs (00-03/19-23) | `cascade_watch.py`: poll injuries, ping star-scratch cascade alerts; dedup via `cascade_pinged.json` | ✅ cascade |
| **capture-wnba-lines** | **DISABLED** | old Odds-API path (redundant w/ Pinnacle guest API); manual `workflow_dispatch` only | — |

**Crons are best-effort** (GitHub skips/delays top-of-hour runs under load → hence off-peak :13/:43). Cron is UTC-fixed; WNBA tips vary 22:00-02:00 UTC.

---

## 2. DATA / PIPELINE FILES
- `data/box_2026.csv` — player box scores (game results); `data/games_2026.csv` — schedule/dates/scores.
- `picks_log.csv` — the model's daily picks (cols: pick_date, game_id, player, team, opp, market, anchor, signals, fair_p, fair_odds, proj, sd).
- `bets_log.csv` — **every 1xbet capture** of a pick (for CLV); cols incl. `src` + `pinn`. Append-only, multiple captures per bet = the open→close trajectory.
- `graded_bets.csv` — settled bets + result + 3 CLVs (rebuilt each grade run).
- `my_bets.csv` — **YOUR real placed bets** (the record that actually matters). 1 entry so far: Cardoso PR U20.5 @1.893 → WIN.
- `xbet_snapshots.csv` — raw line snapshots (all pick markets, every cycle).
- `market_codes.json` — 1xbet market discovery dump. `cascade_pinged.json` — cascade dedup state.

**Flow:** daily-picks → `picks_log` → capture-xbet reads picks + pulls 1xbet → `bets_log` (+ pings) → grade-bets → `graded_bets` + CLV.

---

## 3. THE SIGNALS (honest `src` taxonomy)
**PROVEN headline record = {model, flip} only.** Everything else is walled-off EXPERIMENTAL/paper, never in the headline ROI/CLV.

| src | Signal | Status |
|---|---|---|
| **model** | cold+shrink UNDER (cold: t3≤med−~2-4; shrink: t5min−t10min≤−3) — the workhorse | PROVEN bucket; n=2 settled |
| **flip** | cratered-OVER (an under-player whose 1xbet over line overshot below proj) | PROVEN bucket; 0 settled |
| **newunder** | `ft_volume_drought` (fta_t6≤1.0, ~58.9%) + `steady` (cv_pts≤0.45 & mean10≥10) | PAPER forward-test |
| **hotover** | hot-PRA-over (downgraded weak signal) | PAPER (3/3, tiny n) |
| **overshoot** | line ≥3 below median → over | PAPER, **REMOVED from ping** (commit 32601f5) — 1/6→2/7, book prices it (5/7 came UNDER) |
| **starout** | a model UNDER downgraded because a teammate star is freshly out (usage trap) | PAPER (inverse-cascade guard) |
| **cascade** | star OUT → rank-3-6 teammate PRA OVER | PAPER (~57%, cascade_watch) |
| **usgshock** | usg5−usg20≥4 → ASSIST over | PAPER, **CONTESTED** (see §6) |

---

## 4. HONEST RECORD (as of G6-17 settlements)
- **PROVEN: 2/3** — Austin pts U15.5→8 WIN, Cardoso PRA U23.5→18 WIN, **Jaquez pts U8.5→22 LOSS** (was flagged weak/PASS by recheck — correctly).
- **★ ODDS-CLV = −4.6% (beat the close 1/3).** Cardoso "won" but we took 1.714 into a ~2.0 close = −14.3% CLV. **This is the number that matters and it's leaning NEGATIVE.** n=3.
- Experimental: hotover 3/3 (+2.5u), overshoot 1/6→2/7 (−).
- `my_bets.csv` (real): Cardoso PR U20.5 @1.893 WIN +0.89u, CLV 0 (line was dead-flat 25h).

---

## 5. WHAT WE BUILT/FIXED THIS SESSION (commit trail)
- **Pings now deliver** — every Discord post needs a `User-Agent` header (Discord silently drops default-agent; cost us "no pings" for days). `320778c`.
- **daily-picks ping disabled** → capture-xbet is the sole ping source. `045..049a6d8`.
- **One-bet-per-player** — within-section + **cross-section** (overshoot can't re-list a model-picked player). `9431f76`.
- **grade_bets dedup** (one bet/player/day highest-EV) + full rebuild — killed a counting artifact (overshoot fake 1/10→honest 1/6). `98f57dc`.
- **Inverse-cascade UNDER guard** — fresh star-out → teammate unders downgraded to paper (`new_star_outs`). `b6930f2`.
- **load_picks rollover** — falls back to yesterday's LA slate during the ~07:00-14:00 UTC post-midnight gap (model bets were vanishing). `7ee579b`.
- **Game-date resolution in grade_bets** — bets dated by capture-slate but results by game-date; now re-keyed so cross-midnight captures merge → every capture/CLV counts. `697a4bf`.
- **cascade_watch beneficiary-OUT filter** — was pinging Kiki Iriafen (OUT, ankle); now `_scratched` drops out-beneficiaries. `e0714c5`.
- **Cascade legs now logged** to bets_log (src=cascade) for grading (were display-only). `743aa76`.
- **Overshoot removed from ping** (kept logging). `32601f5`.
- **usgshock signal added** (paper) `7810fa3`, **conflict guard** `ab0c3e4`.
- **steady+streak → steady** (dropped the refuted streak filter). `a367f35`.
- 48h capture window (`XBET_WINDOW_MIN=2880`), off-peak crons, Pinnacle on free guest API.

---

## 6. RESEARCH FINDINGS (5 multi-agent edge-hunts, all leakage-safe + adversarially verified)
### CONFIRMED / kept
- **ft_volume_drought** (58.9%) + **steady (low-cv)** unders — the load-bearing paper signals. (steady's "streak" part was REFUTED & dropped; low-cv is the real component, +2.5pp matched, shuffle 6σ.)
- **cold+shrink UNDER** + **flip** — the proven bucket (prior validation).

### CONTESTED → paper, CLV decides
- **usgshock (usg5−usg20≥4 → ASSIST over):** dedicated backtest 59.2% vs median + every season + dose-response + assist-specific. BUT deeper verify: the median-proxy may be a **stale-line artifact** (assists low-integer right-skewed); lift collapses 73→50% vs a trend-aware line; "min-rising+ast-rising alone = 60.7%". My matched-baseline reconciliation still shows +5-6pp, so **genuinely contested**. Only LIVE CLV settles stale (edge) vs fair (artifact). Conflict guard: skip if player also cold+shrink-under (the under wins, 36.6%).

### DEAD ENDS (do NOT re-chase — all refuted)
- **3-pointers-made (tpm) over/under** — variance too high (R²=0.27 vs ast 0.44/pra 0.52), 49.7% push, ~52% of lines=0; every signal refuted. New 1xbet player-3pm code = **1495/1496** if ever needed.
- **Role-aware market selection (PR for C, PA for G)** — REFUTED; PRA is best cold-under for all positions; tight singles (ast/reb) BACKFIRE (cold-ast-under 41.9%).
- **Teammate-volume → reb/ast** — mechanism real (more teammate misses → bigs' **OFFENSIVE** rebounds, NOT dreb) but NOT bettable; the "62-71% teammate model" was a mean-vs-median artifact.
- **Style × defense matchup (perimeter scorer × leaky-perim-D)** — perimeter DEAD; interior REAL but diffuse (<0.5pt); only thin tail = UNDER big interior scorers vs stingy rim-D at line≥12-16. As an under-**filter/stack** it adds 0 / **backfires on cold+shrink** (personal collapse dominates the matchup). NOT implemented.
- **Totals (game points / team 2pt / team 3pt)** — ALL efficiently priced; apparent edges are median-proxy mirages that collapse vs a pace-aware line. Don't bet.
- **Forward × rim-protector:** REBOUND ticks up (not assist — kick-out hypothesis fails) but ~0.1pt = not bettable.
- **B2B/rest, pace→stocks** — minutes-selection / current-game-pace-leak artifacts.

---

## 7. 1xbet MARKET TYPE-CODES (`cloud_xbet.STAT_T`; ODD=Over, EVEN=Under; all in the "Players' stats" subgame)
pts 1807/1806 · pr 5671/5672 · pa 5673/5674 · ra 7141/7142 · pra 16427/16428 · **ast 1491/1492** · reb 1489/1490. (Discovered but unused: player 3pm 1495/1496.) Endpoint: `1x-bet.com/service-api/LineFeed`, champ **2874802**. `curl_cffi impersonate="chrome"` clears Cloudflare from the local Windows machine too (`scan_now.py`). Pinnacle sharp ref = FREE guest API `guest.api.arcadia.pinnacle.com` (key in cloud_xbet).

---

## 8. KEY GOTCHAS / OPS
- **Every Discord post MUST set a User-Agent** or it silently bounces.
- **bets_log dates by capture-slate, results by game-date** — grade_bets `game_date()` reconciles them; never match on slate date alone.
- **Median-proxy over-bias** — raw >52.4% on a trailing-median line is NOT automatically bettable (low-integer right-skewed stats manufacture a fake under/over bias). Always: half-point line, decided-only, MATCHED baseline, shuffle control.
- **Team-D is diffuse** (<0.5pt on a line) and barely persists game-to-game (perimeter corr 0.08, interior 0.12, blk 0.19) → never a standalone gate.
- **1xbet sits flat ~1.80** both sides → breakeven 55.6%/bet; price-sensitive signals (steady, usgshock) need ≥~1.84.
- ESPN gates near-tip; 1xbet posts days early (slate ≠ game date).
- Bots run via **GitHub Actions**, NOT Windows Task Scheduler.

---

## 9. NEXT STEPS (the only thing left = forward proof)
1. **Collect ~2 weeks of forward CLV** on the paper signals (usgshock, steady, ft_volume_drought) + the proven model/flip bets. **CLV is the only proof** — not hit-rate, not P&L.
2. **Watch the proven-bucket CLV** — it's −4.6% on n=3. If it stays negative over ~20+ bets, the staleness edge isn't there (like the NBA cousin).
3. Log real bets to `my_bets.csv` as placed (real positions = the record that matters).
4. Eyeball the **first graded cascade leg** (synthetic floor-line P&L sanity check).
5. Do NOT add more signals off median-proxy backtests; gate everything on forward CLV.

_Full research detail + thresholds in memory: `reference_wnba_model_matrix.md` (signals/edges/dead-ends) + `reference_wnba_bot_ops.md` (plumbing)._
