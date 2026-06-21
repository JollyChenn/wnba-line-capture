# WNBA-LINE-CAPTURE — SESSION HANDOFF (updated 2026-06-21)

Repo: `JollyChenn/wnba-line-capture` (private), all on `main`.
**ARCHITECTURE CHANGED 2026-06-21:** it no longer "runs fully on GitHub Actions, laptop off." It's now SPLIT —
the **cloud does PAPER tracking, the LAPTOP does real-money + odds snapshots + the actionable pings.** So for
real-money alerts the laptop must be ON. This file = the complete state. Research lives in memory files (see §16).
**Read §1 + §3 + §6 first.**

---

## 1. TL;DR / READ FIRST
- **What it is:** a WNBA player-prop bot. Scrapes 1xbet/melbet lines, runs a cold/shrink/stingy "under" model,
  **PINGS Discord (NEVER auto-bets — 1xbet freezes bots)**, grades results, tracks CLV.
- **The edge:** SOFT-BOOK STALENESS (1xbet's line lags reality). **STILL UNPROVEN.** CLV is the only proof and it's
  not there yet → paper / tiny stakes only.
- **Real money = the `model` signal (COLD/SHRINK/STINGY) ONLY.** Everything else is paper/tracking.
- **Records (2026-06-21):** YOUR real money (`my_bets.csv`) = **4-1, +2.60u** (Cardoso/Hamby/Thornton W, C.Williams L,
  **Jaquez W +1.0u @2.0**). Model SIGNAL (take-on-sight, graded) ≈ **4-3, ~+0.6u** — live number on the dashboard
  BY-SIGNAL scoreboard. **No edge CLV-proven yet** (n tiny).
- **Golden rules:** bet **LATE** (~10-20 min before tip, never on sight) · grab the **~2.0 cap** when it's gifted
  (only ~24% of bets reach it — it's a lucky strike, not a plan) · skip a bet whose line moved ≥2 against you ·
  flat 1u · NEVER auto-bet · **skip outlier-driven signals** (see §6).

---

## 2. THE EDGE THESIS + HONEST STATUS
- Thesis: 1xbet posts a stale line ≈ the trailing-10 median; it lags a player's real decline → the UNDER on
  cold/declining players is +EV *if the book is slow*.
- **Every backtest number is vs a SYNTHETIC median anchor, NOT a real price** — it proves the SIDE predicts, NOT
  that the bet beats the book. (The NBA cousin had a real predictive side and STILL ran −6% beat-the-close.)
- **CLV is the only proof — 3 of them, in a hierarchy** (trust the sharpest with coverage):
  1. **★ sharp ODDS-CLV** = our price vs **Pinnacle's vig-free fair price** (singles only, matched line) = TRUE edge
     test. Fills slowly (pts unders). Headline once it has ≥10 pts.
  2. **sharp LINE-CLV** = our line vs Pinnacle line (combos incl.).
  3. **self odds-CLV** = vs 1xbet's OWN close = WEAK (just times the soft book). ≈ −0.6/−0.9% so far.
- Verdict: ⏳ **TOO EARLY** (~20-40 settled model bets + ≥10 sharp-CLV pts, ~2 weeks). Verdict logic auto-prefers
  sharp odds-CLV at ≥10 pts.
- Breakeven at 1xbet flat ~1.80-1.85 ≈ **54-56%/bet**. Prop odds **cap ~2.0** (only ~24% of bets ever reach it).

---

## 3. ARCHITECTURE — CLOUD = paper, LAPTOP = real money (the 2026-06-21 split)
Controlled by env `CAPTURE_ROLE` in `cloud_xbet.py` (`all` | `paper` | `real`):
- **`paper`** (cloud): logs only paper/experimental signals to `bets_log.csv`; **no odds snapshots, never pings.**
- **`real`** (laptop): logs only `model` (real-money) rows + writes `xbet_snapshots.csv`/`pinn_snapshots.csv` + **pings.**
- **`all`**: everything (single-host default).

**Cloud GitHub workflows:**
| Workflow | Cron (UTC) | Role |
|---|---|---|
| **daily-picks** | 13:23, 16:23 (delayed) | ESPN box+games+injuries → `box_2026`/`games_2026`; picks; CBS 2nd source; dashboard |
| **capture-xbet** | every 3h + every 30m (14:00-02:00) | `CAPTURE_ROLE=paper` — paper signals only, NO ping, NO snapshots |
| **grade-bets** | **04:41-09:41 (6×) + 15:23 + 18:23 + 20:41/22:41/00:41/02:41** | `daily_picks.py` (fetch finals) → `grade_bets.py` → `clv_reader.py` → `build_dashboard.py` → commit. Evening crons added so games settle ~1-2h after they END (games tip 17:00-02:00 UTC, end 19:30-04:30) |
| **lineup-confirm** | ~10m, tip hours | scratches + day-to-day + line-move ≥2 against |
| **cascade-watch** | ~20m, game hours | star-out cascade detection + ping |

**Pipeline:** laptop capture (model rows + snapshots) **and** cloud capture (paper rows) → both push `bets_log.csv`
→ grade-bets (cloud, tip-aware) → `graded_bets.csv` → CLV + dashboard. `my_bets.csv` = your HAND-ENTERED real-money log.

---

## 4. LAPTOP SCHEDULED TASKS (Windows Task Scheduler — laptop must be ON; SG = UTC+8)
Both run as the logged-on user, **hardened identically**: auto-kill if hung, `IgnoreNew` (never stacks), Hidden
(no console window), network-gated, below-normal priority (7). Verified leave **0 lingering procs**. Manage via
`schtasks` / the `Schedule.Service` COM API — NOT `Get-ScheduledTask`/WMI (those hang, see memory).

| Task | When | Action | Why |
|---|---|---|---|
| **WNBA-Grade-Trigger** | 13:30 + 18:30 SG (2×/day) | `grade_trigger.bat` → `gh workflow run grade-bets.yml` | Forces the cloud grade (GitHub free-tier drops scheduled runs); ~3s, all heavy work in cloud |
| **WNBA-Capture-Real** | every **20 min**, 22:00-10:00 SG (=14:00-02:00 UTC tip window) | `capture_real_hidden.vbs` → `capture_real.bat` (CAPTURE_ROLE=real) | Scrapes 1xbet for model bets + snapshots, **pings**, pushes. 20-min so a run lands in each bet's final-ping window |
| ~~WNBA-xbet-ping~~ | — | DELETED this session (stale, old `wnba_bot` dir) | superseded |

- **Webhook:** `capture_real.bat` reads the Discord URL from **`webhook.txt`** (gitignored — secret never hits git).
  It's set and verified delivering (HTTP 204).
- **Laptop-OFF gap:** WNBA games tip ~01:00-08:00 SG (overnight) — if the laptop's off, those get no real-money
  capture/ping/CLV. Your actual P&L (`my_bets.csv`, hand-entered) is unaffected. The 100% fix would be an external
  web-cron (cron-job.org → GitHub dispatch API); not built.
- Remove either: `schtasks /delete /tn "<TaskName>" /f`.
- The conhost pile-up the user sees in Task Manager = **Claude Code's** shell-per-command leak, **NOT** these tasks
  (they exit clean). Clears on a Claude restart / reboot.

---

## 5. PING POLICY — TWO SHOTS per real-money bet, nothing in between (2026-06-21)
Only the `model` (real-money) signal ever pings; paper is silent (lives on the dashboard).
1. **👀 HEADS-UP** — once, when a bet is first found and its game is still > `FINAL_MIN` (20) min out. "Don't bet yet."
2. **💰 PLACE IT NOW** — once, when the bet's OWN game is ≤ ~20 min from tip. State-tracked in `ping_state.json` so it
   fires exactly once even though the laptop scans every 20 min.
- **PER-GAME timed:** each bet uses ITS OWN game's tip (via `espn_near()` returning all-games tip times), so a late
  game (e.g. Jaquez, tip 8h out) does NOT get a premature BET ping off an earlier game.
- User sleeps through overnight tips → the FINAL ping is the wake-up/place-it call.

---

## 6. STRATEGY / BETTING RULES + signal quality
1. **BET LATE (~10-20 min before tip).** Backtest (`bet_timing_study.py`, n=55 settled): betting at the CLOSE beats
   on-sight (all-signal −7.25u → −5.16u; grab-the-peak → −3.94u). **But it's the ODDS, not the wins** — hit-rate
   barely moves (47%→49%); you just get paid more on the same wins. Still negative overall → it's "lose less", not edge.
2. **Take ~2.0 when it's there, don't chase it.** Only ~24% of bets ever reach ≥1.98. It's a lucky strike. 1.91 is
   "second-highest" but NOT the cap — no reason to grab it early; unders drift UP toward 2.0 by tip anyway.
3. **★ SKIP outlier-driven signals.** A "shrink" (minutes drop) caused by a single sub-15-min game (foul trouble/
   blowout) is fake. Backtest (`iriafen_signal_backtest.py`): outlier-driven cold+shrink unders hit ~57% (50% for PRA)
   vs 71% clean — BUT only **~11 distinct outlier games** (the 48/21 "pairs" double-count correlated markets), so it's
   a **lean, NOT proven**. Don't change the model on it yet; DO skip the specific bets manually. The model's live
   shrink rule (`mean(min[-5:]) − mean(min[-10:-5]) ≤ −3`) has no outlier guard, so it flags these.
4. **Line moved ≥2 against thesis** → skip (lineup_check flags). A line that gets PULLED entirely = repricing/news —
   re-check near tip (see Wheeler, §12).
5. **Flat 1u. NEVER auto-bet. One bet/player/day (top-EV market). Keep stakes tiny until CLV proves positive.**

---

## 7. CLV mechanics (what the columns mean)
- `grade_bets.py` is **idempotent** (rebuilds `graded_bets.csv` from `bets_log` + box each run).
- **CLV close = last capture AT OUR OPENING LINE** (not the absolute-last) → odds-CLV is apples-to-apples,
  deterministic, frozen post-tip (was bouncing because the book oscillates the price & shifts the line).
- **★ TIP-AWARE grading (2026-06-21 fix):** a bet only settles against a game whose **TIP is AFTER the bet's first
  capture**; captures taken at/after tip are dropped; a bet captured after all known games tipped stays PENDING. This
  killed a bug where the every-3h cloud scan (~05:13 UTC, after games ended) logged NEXT-day lines under today's LA
  slate and they got mis-settled against the finished game.
- `graded_bets.csv` cols: …, `sharp_clv`, `sharp_odds_clv`, `src`, **`opened`** (first-capture date — drives the
  dashboard "logged" column for transparency).
- Real-money CLV is HAND-ENTERED in `my_bets.csv` (entry/close odds you type) — never recomputed.

---

## 8. DASHBOARD (`dashboard.html`, local file — open it; cloud rebuilds it)
- **💰 REAL MONEY** = your placed bets (`my_bets`). **🧪 PAPER TESTING** = all other signals.
- **📊 BY-SIGNAL scoreboard** at top: W-L · P&L · CLV per model (take-on-sight, flat 1u — the SIGNAL record, not your
  placed bets). One-per-player-per-day dedup keeps the record honest.
- **Team nickname** next to each player (Sky/Lynx/…), mapped from box via ESPN full names.
- **`logged` column** = MM-DD the bet was FIRST captured (usually the day BEFORE the game). Transparency: a bet only
  shows its result once its game finishes, so a morning batch "appearing" is normal, not injected.

---

## 9. DATA SOURCES
- **ESPN** (free): scoreboard (games+tips), summary (box), injuries. PRIMARY. ✅
- **1xbet** `1x-bet.com/service-api` champ **197289** (curl_cffi impersonate=chrome) + **melbet.com fallback**. ✅
- **Pinnacle guest API** `guest.api.arcadia.pinnacle.com` (key `CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R`), sport 4, WNBA →
  sharp CLV. WNBA props post only NEAR TIP; singles only → combos = sum of singles (lines); **vig-free FAIR odds**
  per side (de-vig two-way price) → `pinn_snapshots.csv` (singles only). ✅
- **RotoWire** lineups (2nd source, fail-open). **CBS Sports** team stats (`cbs_check.py`, 142/150 match). ✅
- 1xbet TYPE-CODES (odd=Over even=Under, "Players' stats"): pts 1807/1806 · pr 5671/5672 · pa 5673/5674 ·
  ra 7141/7142 · pra 16427/16428 · ast 1491/1492 · reb 1489/1490 · 3pm 1495/1496.

---

## 10. SIGNAL REGISTRY (records fluctuate — dashboard scoreboard is live)
`src` keys are stable; display names for clarity. **Real money = `model` ONLY.**
| Signal (`src`) | Route | Notes |
|---|---|---|
| **COLD/SHRINK/STINGY** (`model`) | 💰 REAL | the edge. 2-of-3: cold(t3≤med−4)/shrink(min t5−prev5≤−3)/stingy(opp btm-qtile). Bet PTS over PRA. **SKIP outlier-driven (§6.3).** |
| HOT OVER (`hotover`) | 🧪 paper | variance; CLV flat |
| STAR-OUT CASCADE (`cascade`) | 🧪 exp | star OUT → teammate PRA over |
| FTUNDER (`newunder`) | 🧪 paper | ft-drought+steady; side-predicts only |
| FLIP UNDER (`flip`/`flip_paper`) | 🧪 paper | median-proxy artifact — weak |
| BOOK OVERSHOOT (`overshoot`) | 📝 paper | "too-low lines are correct" — not an edge |
| starout (`starout`) | 🧪 paper | under downgraded after a fresh star-out (inverse-cascade guard) |

**DEAD (never bet):** rebound · assist singles · totals · 3PM · teammate-volume (leakage) · last-5 overlay.

---

## 11. RECORDS (2026-06-21)
**💵 YOUR REAL MONEY (`my_bets.csv`): 4-1, +2.60u**
- 6/17 Cardoso PR U20.5 @1.893 ✅ +0.89u · 6/17 Hamby PRA U25.5 @1.8 ✅ +0.80u
- 6/19 Thornton PR U14.5 @1.91 ✅ +0.91u · 6/19 C.Williams PR U22.5 @1.73 ❌ −1.0u
- **6/20 Jaquez PTS U9.5 @2.0 ✅ +1.0u** (CHI, 6 pts; entry 2.0 beat 1.85 close = +8% CLV)

**📡 MODEL SIGNAL (graded take-on-sight) ≈ 4-3, ~+0.6u** — live on the dashboard. Still no edge CLV-proven.

**★ bet-late finding (n=55):** close > open by odds (−7.25u→−5.16u all-signal), odds-driven not win-driven.

---

## 12. TONIGHT'S OPEN BETS (2026-06-21 games) — all weak, lean SKIP
- **Kiki Iriafen** (WSH) PRA U23.5 @1.91 — `model`/real-money, but **outlier-driven shrink** (one 8-min game) +
  line 1.0 below median → **SKIP** (the ~50% kind).
- **Ariel Atkins** (LA) PRA U13.5 @1.73 — `model`/real-money, **outlier-driven + Brink-out usage risk** (she's LA,
  Cameron Brink OUT-ankle → Atkins usage may rise = star-out trap on an under) → **SKIP/tiny.** NOTE: the star-out
  guard did NOT downgrade her (still tagged `model`) — check why (Brink in watchlist?).
- **Erica Wheeler** (LA) PTS U8.5 — `model`, but **1xbet PULLED her points line** (she's still on the board for
  AST/PA, so NOT scratched — just repricing, likely Brink-out). Her **PA U12.5 does NOT qualify the model** (cold=False).
  → wait for the points line to repost near tip; reassess.
- Lesson reinforced: a pulled line = news/repricing → bet late, confirm at tip. Tool: `python check_wheeler.py <name>`
  pulls the live raw board for any player at any line.

---

## 13. KEY FINDINGS THIS SESSION (2026-06-20→21)
1. **Pinnacle sharp-CLV added** (vig-free fair odds) → the TRUE edge metric; old self-CLV demoted.
2. **GitHub free-tier drops/delays scheduled runs** (verified via `gh run list`) → stranded grading ~13h. Fixed:
   dense morning + evening grade crons + the laptop `WNBA-Grade-Trigger`.
3. **Grading was correct (audited 39→54/54 via `audit_results.py`)** — the "missing results" were un-fetched box
   scores (cron timing), not mis-grades.
4. **TIP-AWARE grading bug found+fixed** — post-game captures (next-day lines under today's LA slate) were
   mis-settling against finished games. User caught it.
5. **bet-late study (n=55):** close/peak-odds beats on-sight, but odds-driven not win-driven; 2.0 only 24% reachable.
6. **Outlier-driven signal study:** cold+shrink unders driven by one low-minute game hit ~57% (50% PRA) vs 71% clean
   — directional lean, NOT proven (~11 outlier games). Iriafen & Atkins are this type tonight.
7. **Capture split** (cloud=paper, laptop=real) + **two-shot per-game ping** + **dashboard transparency** (scoreboard,
   teams, `logged` column).
8. **Jaquez bet won** at the 2.0 cap (+1.0u) → real money 4-1, +2.60u.

---

## 14. TOOLS / FILE MAP (local, past Cloudflare via curl_cffi)
- `cloud_xbet.py` — capture+ping. Env: `CAPTURE_ROLE` (all/paper/real), `XBET_WINDOW_MIN`, `XBET_FINAL_MIN`,
  `DISCORD_WEBHOOK`. Test: `CAPTURE_ROLE=all XBET_WINDOW_MIN=1440 DISCORD_WEBHOOK="" python cloud_xbet.py`.
- `grade_bets.py` — settle (idempotent, tip-aware, CLV-locked-to-line). `clv_reader.py` — record + verdict (NO ping).
- `build_dashboard.py` → `dashboard.html`. `lineup_check.py` — near-tip guard.
- **Laptop launchers:** `grade_trigger.bat`, `capture_real.bat`, `capture_real_hidden.vbs` (hidden runner). Task XMLs:
  `wnba_grade_task.xml`, `wnba_capture_task.xml`.
- **Research/diag tools (re-run anytime):** `audit_results.py` (verify every graded result vs box),
  `fetch_finals.py YYYYMMDD` (manual box backfill), `bet_timing_study.py` (open/close/2.0), `iriafen_signal_backtest.py`
  (outlier-signal), `check_wheeler.py <name>` (live raw board for a player).
- Data: `data/box_2026.csv`, `data/games_2026.csv`, `bets_log.csv`, `xbet_snapshots.csv`, `pinn_snapshots.csv`,
  `graded_bets.csv` (16 cols, incl `sharp_odds_clv` + `opened`), `CLV_HISTORY.md`, `my_bets.csv`, `cascade_log.csv`.
- **Gitignored (laptop-local):** `webhook.txt`, `ping_state.json`, `*.log`.
- **Commit policy:** code freely; `my_bets.csv` yes; bot data files (`bets_log`, box/games, `graded_bets`,
  `dashboard.html`) are cloud/laptop-managed — let the cron own them (revert local churn). dashboard.html commits
  occasionally conflict (cloud regenerates each grade) — resolve by reset-to-origin + rebuild.

---

## 15. OPEN ITEMS / TODO
- **GROW THE CLV SAMPLE** — everything hinges on it (~20-40 model bets + ≥10 sharp-odds-CLV pts).
- **Star-out guard missed Atkins** (LA, Brink out, still `model`) — check the watchlist / why it didn't downgrade.
- **`actions/checkout@v4` + `setup-python@v5` on deprecated Node 20** — bump to @v5/@v6 across all 6 workflows.
- **Outlier-driven shrink filter** — DON'T add yet (n~11, would fit noise); re-run `iriafen_signal_backtest.py` in a
  few weeks, then decide.
- Offered, not built: peak-odds "take it" alert · open-vs-close dashboard metric · "line pulled / likely scratch" flag
  on pending bets · de-duplicated paper view · external web-cron for 100% laptop-off reliability.

---

## 16. MEMORIES (auto-loaded each session)
- `reference_wnba_signal_registry.md` · `reference_wnba_model_matrix.md` · `reference_wnba_bot_ops.md` ·
  `reference_pinnacle_api.md` · `reference_xbet_pull.md` · `reference_laptop_automation.md` (the two tasks + GitHub
  free-tier gotcha) · `project_wnba_bot.md`.

---

## 17. PRIOR-SESSION HIGHLIGHTS (pre-2026-06-19)
- teammate-volume "edge" = LEAKAGE; brute-force found only median-proxy artifacts. Built the honest-grading `src`
  split + `lineup_check.py`. Champ-feed bug (`2874802`→`197289`) was root cause of missing lines.

---
_Honest one-liner: a clean automated soft-book-staleness bot, NO proven edge yet. Cloud=paper, laptop=real-money
(must be on for overnight pings). Real money only on `model`, bet late, take 2.0 when gifted, skip outlier-driven
signals, flat 1u, never auto-bet. CLV over ~2 weeks decides if any of it is real._
