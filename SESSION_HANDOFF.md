# WNBA-LINE-CAPTURE — SESSION HANDOFF (updated 2026-06-20)

Repo: `JollyChenn/wnba-line-capture` (private), all on `main`. Runs fully on GitHub Actions (laptop can be off).
This file = the complete state. Research lives in the memory files (see §12). **Read §1 + §5 first.**

---

## 1. TL;DR / READ FIRST
- **What it is:** a WNBA player-prop bot that scrapes 1xbet/melbet lines, runs a model, **PINGS Discord (never auto-bets — 1xbet freezes bots)**, and grades results + CLV.
- **The edge:** SOFT-BOOK STALENESS (the soft book's line lags reality). **UNPROVEN.** CLV is the only proof, and it's currently **~flat/slightly negative** → paper/tiny stakes only.
- **Real money = COLD/SHRINK/STINGY signal ONLY** (everything else is paper/tracking).
- **Records (2026-06-20):** your real bets (`my_bets`) **3-1, +1.60u**; the model SIGNAL (take-on-sight) **3-3, −0.39u**, odds-CLV −0.6%. No edge proven (n tiny).
- **Golden rules:** bet LATE (~T-30-60, not on sight) · grab the ~2.0 price ceiling when it appears · skip a bet whose line moved ≥2 against you · flat 1u · NEVER auto-bet.

---

## 2. THE EDGE THESIS + HONEST STATUS
- Thesis: 1xbet posts a stale line ≈ the trailing-10 median, which lags a player's real decline → the UNDER on cold/declining players is +EV *if the book is slow*.
- **Every backtest number is vs a SYNTHETIC median anchor, NOT a real price** — it proves the SIDE predicts, NOT that the bet beats the book. The NBA cousin of this method had a real predictive side and STILL ran −6% beat-the-close.
- **CLV is the only proof.** Current proven (model) odds-CLV ≈ **−0.6%** (n=6) = not beating the close yet. Verdict: ⏳ TOO EARLY (need ~20-40 settled, ~2 weeks).
- Breakeven at 1xbet flat ~1.80 = **55.6%/bet**. Prop odds **cap ~2.0** (see §5).

---

## 3. ARCHITECTURE — 5 GitHub workflows + pipeline
| Workflow | Cron (UTC) | Does |
|---|---|---|
| **daily-picks** | 13:23, 16:23 | ESPN box+games+injuries → `box_2026.csv`/`games_2026.csv`; picks → `picks_log.csv`/`PICKS.md`; runs `validate_data.py` + **`cbs_check.py`** (2nd source); rebuilds dashboard |
| **capture-xbet** | every 3h + every 30m (14:00-02:00) | scrapes 1xbet (`1x-bet.com`, fallback `melbet.com`) champ **197289**, 48h window → `bets_log.csv` (bets) + `xbet_snapshots.csv` (all lines) + Pinnacle `pinn`; **PINGS** real-money bets |
| **grade-bets** | **05:23, 06:23**, 15:23, 18:23 | pulls finals → `grade_bets.py` settles → result + P&L + 3×CLV → `graded_bets.csv`; `clv_reader.py` → `CLV_HISTORY.md` + verdict ping; rebuilds dashboard |
| **lineup-confirm** | ~every 10m, tip hours | `lineup_check.py` — NEAR-TIP guard: scratches + day-to-day + **line-move ≥2 against** |
| **cascade-watch** | ~every 20m, game hours | star-out cascade detection + ping |

**Pipeline:** capture (bets_log) → grade (graded_bets) → CLV (CLV_HISTORY) → dashboard. `my_bets.csv` = the user's HAND-ENTERED real-money log (separate from the bot's signal record).

---

## 4. DATA SOURCES (used + status)
- **ESPN** (free): scoreboard (games+tips), summary (per-player box), injuries. PRIMARY game data. ✅
- **1xbet** `https://1x-bet.com/service-api` champ **197289** (curl_cffi impersonate=chrome past Cloudflare) + **melbet.com fallback** (same LineFeed engine, auto-switch if 1x-bet empty). ✅
- **Pinnacle guest API** `guest.api.arcadia.pinnacle.com` (key `CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R`), sport 4, league WNBA → sharp CLV ref. **WNBA props post only NEAR TIP**; single stats only (pts/reb/ast) → combos DERIVED by summing; filter `period==0`. ✅ (live near tip)
- **RotoWire** `rotowire.com/wnba/lineups.php` — non-ESPN 2nd lineup source (lineup_check, fail-open). ✅
- **CBS Sports** team stat pages — 2nd source for minutes/scoring (`cbs_check.py`, wired to daily-picks cron). 2026 data CONFIRMED 142/150 match. ✅
- 1xbet TYPE-CODES (odd=Over, even=Under, "Players' stats" subgame): pts 1807/1806 · pr 5671/5672 · pa 5673/5674 · ra 7141/7142 · pra 16427/16428 · **ast 1491/1492 · reb 1489/1490** · 3pm 1495/1496.

---

## 5. STRATEGY / BETTING RULES (decisions settled this session)
1. **BET LATE, not on sight.** odds-CLV is flat/negative → no early edge; betting near tip = settled line + confirmed lineup + (slightly) better price. Ping: **👀 WATCH early → 💰 BET near tip**.
2. **Prop odds cap ~2.0** (data: max 2.07, 95th pctile 2.00, only 1.7% >2.0). When a bet hits **~2.0 (ceiling), TAKE IT** — it can't go higher and usually *sags* toward tip (Thornton 2.0→1.83). **Don't wait for a hypothetical better line — at the cap there's no price upside, only downside.** Bird in hand.
3. **Alternate / "two lines":** the book often lists 2+ lines at once (e.g. U22.5 AND U25.5) and/or opens new ones + trims odds. Higher line = more cushion, lower odds. **Crossover (Jaquez ex.): a +1 line needs ≥1.80, a +2 line needs ≥1.65 to beat U-low @2.0.** Below that, take the cap. Higher-line "EV" is model-optimism (tail hit% inflated; book prices the curve fairly) — the *reliable* gain is lower variance, not profit.
4. **Line MOVED ≥2 against your thesis** (under RISES / over DROPS) by tip = sharp market correcting our stale signal → **SKIP/shrink** (lineup_check flags it). Hamby lesson: 22.5→25.5, scored 23 — the under was wrong; the 25.5 only won on cushion.
5. **Flat 1u stake. NEVER auto-bet 1xbet** (freeze). One bet per player per day (highest-EV market). Bet POINTS over PRA. Keep stakes tiny until CLV proves positive.

---

## 6. SIGNAL REGISTRY — every model, routing, record (settled, 2026-06-20)
Internal `src` keys are STABLE in the data; display names renamed for clarity.

| Signal (`src`) | Route | Settled W-L · P&L · oddsCLV | Verdict |
|---|---|---|---|
| **COLD/SHRINK/STINGY** (`model`) | 💰 REAL | 3-3 · −0.39u · −0.6% | core thesis; break-even, unproven. Any 2-of-3: cold(t3≤med−4)/shrink(t5−t10≤−3)/stingy(opp btm-quartile). Bet PTS not PRA |
| **HOT OVER** (`hotover`) | 🧪 paper | 4-0 · +3.38u · +0.1% | ⚠️ variance (CLV flat = not beating close) |
| **STAR-OUT CASCADE** (`cascade`) | 🧪 exp | 2-0 · +1.50u · ~0% | n=2 small. Star OUT → teammate PRA over |
| **FTUNDER** (`newunder`) | 🧪 paper | 4-4 · −0.82u · −3.5% | ft-drought(58.9% OOS)+steady(cv≤.45); side-predicts only |
| **FLIP UNDER** (`flip`) | 🧪 paper | 2-4 · −2.27u · −2.6% | ❌ suspect median-proxy artifact — confirmed weak |
| **BOOK OVERSHOOT** (`overshoot`) | 📝 logged | 5-7 · −2.79u · −0.2% | ❌ "too-low lines are correct" — not an edge |
| **starout** | 🧪 paper | 0-1 · −1.0u | downgraded-under after a star-out |
| **ALL signals (flat 1u)** | | **20-19 · −2.39u** | flat-betting everything LOSES; winners are small-n variance |

**DEAD (never bet):** rebound 53.7% · assist 53.8% (singles) · totals · 3PM · teammate-volume (leakage) · last-5 form overlay.

---

## 7. RECORDS (2026-06-20)
**💵 YOUR real money (`my_bets.csv`): 3-1, +1.60u, CLV −3.5%**
- 6/17 Cardoso PR U20.5 @1.893 ✅ +0.89u
- 6/17 Hamby PRA U25.5 @1.8 ✅ +0.80u (took the drifted-up line vs bot's 22.5)
- 6/19 Thornton PR U14.5 @1.91 ✅ +0.91u (bet early; −4.5% CLV — drifted to 2.0)
- 6/19 C.Williams PR U22.5 @1.73 ❌ −1.0u (scored 33)

**📡 Model SIGNAL (graded take-on-sight): 3-3, −0.39u, oddsCLV −0.6%.** Your +1.60u beats it via line-shopping (Hamby) + skipping Jaquez (signal lost it). NOT in my_bets (user's choice): Austin 6/14 (signal won), Jaquez 6/17 (signal lost).

**★ KEY FINDING — bet-late, in dollars:** re-grading the SAME bets at the CLOSE line+odds:
- TOTAL: −2.39u → **−0.03u** (+2.36u just from timing).
- COLD/SHRINK/STINGY: 3-3 −0.39u → **4-2 +1.44u** (the **Hamby flip**: open 22.5=loss → close 25.5=win, her 23 cleared the higher line). This is why "the model record went 3-3 → 4-2."
- Drivers: odds drift longer by close + lines drift to more cushion on unders. Caveat: Hamby's flip is cushion-dependent, small n, still ~break-even at close.

**Tonight (6/19) settled:** Thornton ✅ (PR 9 vs U14.5), C.Williams ❌ (33). Paper: cascade 2/2 ✅, flip 0/3 ❌, FTUNDER Stewart ✅/Griner ❌/McBride ❌, Onyenwere overshoot ✅, Mabrey starout ❌ (37).

---

## 8. CHANGES MADE THIS SESSION (code commits, newest first)
- `759466d` my_bets: tonight's real bets (Thornton W, C.Williams L)
- `0bd9c7b` grade-bets: **+05:23/06:23 UTC crons** so the overnight slate settles right after games (was 15:23-only → ~10h lag)
- `e33c235` capture + show **alternate lines** (simultaneous "two lines") with cushion%
- `d8b6d3f` near-tip **line-move guard** (≥2 against = skip) + **bet-late ping** framing (WATCH→BET)
- `88b97b7` **name-key hardening** (full-name, accent-fold; Chance≠Chelsea Gray) + **CBS 2nd source** wired to cron
- `2e479b3` **Pinnacle fix**: `period==0` filter + **derive PR/PA/RA/PRA** by summing singles
- `16d2a9a` **lineup-guard fix**: write UPCOMING games (tips) to games_2026 → guard can fire (was skipping every player); dashboard REAL = my_bets
- `f7e0281` **cleanup**: real money = COLD/SHRINK/STINGY only (`PROVEN={model}`, flip→paper); pings ONLY real money (no heartbeat spam); dashboard = 2 sections
- `b50bea2` rename signals to proper display names
- `d63db6e` **melbet.com fallback mirror**
- `0d9eb10` **THE big fix**: champ `2874802` (junk mixed-league feed) → `197289` (clean WNBA) — root cause of "flickering/missing lines"

---

## 9. KEY FINDINGS (this session)
1. **Champ bug** (`2874802`) buried WNBA props the whole time → fixed to `197289`.
2. **Bet-late pays** (+2.36u at close; real signal flips to +1.44u). odds-CLV negative = early entries get worse prices.
3. **Prop odds cap ~2.0** — take the ceiling, don't wait.
4. **Name-key collision** (`"c gray"` merged Chance + Chelsea Gray) — fixed (Pinnacle + lineup). Model unaffected (groups by athlete-ID).
5. **Lineup guard was non-functional** (no tips for upcoming games) — fixed; caught Austin day-to-day.
6. **Pinnacle posts WNBA props only near tip** + single-stats only → derive combos.
7. **FLIP UNDER is a median-proxy artifact** (2-4, neg CLV) → demoted to paper.
8. Data CONFIRMED clean via CBS 2nd source (142/150) + the earlier 4-way ESPN/identity audit.

---

## 10. OPEN ITEMS / TODO / WATCH
- **GROW THE CLV SAMPLE** — everything hinges on this. ~20-40 settled model bets before any verdict. Currently n=6, CLV −0.6%.
- **Sharp-CLV coverage** still thin (Pinnacle near-tip only) — improving now combos are derived; watch it fill in.
- **Peak-odds alert (OFFERED, NOT BUILT):** ping when a real bet hits ≥1.95 (near cap) or a +2-cushion line opens ≥1.65 → "take it." Build if wanted.
- **Open-vs-close P&L as a standing dashboard metric** (offered, not built).
- **GitHub skips some crons** (free-tier) — morning grade has a 06:23 backstop; capture has dense tip-window crons.
- **my_bets is hand-entered** — the bot can't know what you staked; log each bet (player+line+odds) when you place it.

---

## 11. FILE MAP / HOW TO RUN (locally, past Cloudflare via curl_cffi)
- `cloud_xbet.py` — capture+ping bot. `XBET_WINDOW_MIN=1440 DISCORD_WEBHOOK="" python cloud_xbet.py` (wide gate, no ping). Mirrors in `MIRRORS`; champ in `CHAMP`.
- `daily_picks.py` — ESPN fetch + picks. `DISCORD_WEBHOOK="" python daily_picks.py`.
- `grade_bets.py` — settle (idempotent, rebuilds graded_bets from bets_log+box). `clv_reader.py` — record + verdict.
- `build_dashboard.py` → `dashboard.html` (LOCAL only, not GitHub Pages — open the file).
- `lineup_check.py` — near-tip guard. `LINEUP_WINDOW_MIN=1440 python lineup_check.py` to test wide.
- `cbs_check.py` — CBS 2nd-source cross-check (all teams).
- Data: `data/box_2026.csv`, `data/games_2026.csv`, `bets_log.csv`, `xbet_snapshots.csv`, `graded_bets.csv`, `CLV_HISTORY.md`, `my_bets.csv`, `cascade_log.csv`.
- **Commit policy:** code files freely; `my_bets.csv` (hand-entered) yes; the bot's data files (`bets_log`, `box_2026`, `games_2026`, `graded_bets`, `dashboard.html`) are cloud-managed — let the cron own them (revert local churn).

---

## 12. MEMORIES (knowledge base — auto-loaded each session)
- `reference_wnba_signal_registry.md` — THE model tracker (signals, routing, records, the 2026-06-19 cleanup).
- `reference_wnba_model_matrix.md` — full backtest research (signal defs, value-zones, flip matrix, dead ends, 4-way data audit).
- `reference_wnba_bot_ops.md` — plumbing (type-codes, Discord UA gotcha, ping policy, name-key, line-move guard, bet-late, alt-lines).
- `reference_pinnacle_api.md` — Pinnacle guest API recipe + period/combo/near-tip fixes.
- `reference_xbet_pull.md` — 1xbet scrape recipe. `project_wnba_bot.md` — project status.

---

## 13. PRIOR-SESSION HIGHLIGHTS (pre-2026-06-19, from summary/transcript)
- Re-confirmed 3 dead-ends DEAD; **teammate-volume "edge" = LEAKAGE** (sign-flips leak-free, corr −0.79 w/ own usage). Brute-force found only median-proxy artifacts.
- Audited signals into proven/paper/experimental; built the honest-grading `src` split.
- Built `lineup_check.py` (3-source near-tip guard) + injury filters on all pick masks.
- Fixed: flip-on-steady bug (→flip_paper), graded_bets staleness (cron top-of-hour skips), C.Williams EV display bug, dashboard double-emoji.
- Discovered the champ-feed bug (root cause of missing lines) — fixed this session.
- Established: proven record honest (no edge proven), recording verified (line/actual/result/CLV), injury check held (0 bets on players who sat).

---
_Honest one-liner: a clean, fully-automated soft-book-staleness bot with NO proven edge yet. Real money only on COLD/SHRINK/STINGY, bet late, take the ~2.0 cap, flat 1u, never auto-bet. CLV over ~2 weeks decides if any of it is real._
