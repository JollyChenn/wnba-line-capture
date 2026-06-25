# WNBA line-capture — HANDOFF (2026-06-25)

**Mode: unattended DATA-GATHERING for ~2 months. Not betting.** The whole point is to accumulate a clean,
date-honest, two-sided odds + injury + lineup dataset so the "should we fade?" question can finally be
answered properly. Laptop stays on 24/7. Everything self-heals or alerts.

---

## TL;DR state
- Repo is **PUBLIC** (`JollyChenn/wnba-line-capture`) -> unlimited GitHub Actions, no minute cap. **0 secrets.**
- **Cloud is the SOLE capturer** (role=all). Laptop is near-idle (watchdog + a grade dispatch backstop).
- All 3 workflows green. All data streams fresh and pushing as `xbet-cloud-bot`.
- **The fade is NOT a proven edge** (details below). FTUNDER specifically *loses* at real prices.

---

## What runs where

### Cloud (GitHub Actions) — does everything
| workflow | schedule | job |
|---|---|---|
| **capture-xbet** | every ~30 min, 14:00–04:00 UTC (+3h baseline) | `cloud_xbet.py` (CAPTURE_ROLE=all) = 1xbet board both sides + xbet/pinn odds snapshots + all signals; then `capture_news.py` = injuries + lineups |
| **daily-picks** | 13:23 + 16:23 UTC | generate model picks -> picks_log.csv, refresh box scores |
| **grade-bets** | 12×/day (04:41–02:41 UTC sweep) | `grade_bets.py` settle results + CLV -> graded_bets.csv |

DISABLED (ping/odds-api only, not needed): cascade-watch, lineup-confirm, capture-wnba-lines.

### Laptop (Task Scheduler) — minimal
| task | schedule | job |
|---|---|---|
| **WNBA-Grade-Trigger** | 13:30 + 18:30 local | `gh workflow run grade-bets.yml` (drop-proof dispatch; ~3s) |
| **WNBA-Watchdog** | hourly | `watchdog_wnba.ps1` — self-heals git (resync to origin), re-enables Grade-Trigger if disabled, nudges cloud if stale. Logs to watchdog_wnba.log. (Webhook deleted -> alerts are log-only now.) |
| ~~WNBA-Capture-Real~~ | DISABLED | laptop no longer scrapes — cloud does it all |

All laptop tasks run hidden (wscript //B //Nologo `<name>_hidden.vbs`), IgnoreNew + 5-min kill-timer + Priority 7.

---

## Data streams (all committed to the repo)
| file | what | note |
|---|---|---|
| `xbet_board.csv` | **two-sided** board, every player both sides, logs only odds CHANGES | the odds-movement record. Started **06-24** |
| `xbet_snapshots.csv` | per-capture odds (mostly the bet side) | full period 06-13+ |
| `pinn_snapshots.csv` | sharp Pinnacle fair (vig-free) odds | the CLV reference |
| `bets_log.csv` | every signal fired | `src` col = model/newunder/overshoot/flip/hotover/cascade/… |
| `graded_bets.csv` | settled results + CLV | **result col: `WIN` (upper) vs `loss` (lower) — normalize case!** |
| `injuries_log.csv` | ESPN injury status changes | dedup on change |
| `lineups_log.csv` | official starters/actives | logged when a game is pre/in (~tip) |
| `picks_log.csv` | daily model picks | |

---

## The fade question — HONEST status (researched 2026-06-25)
**No fade is proven. Do not bet it.**
- Fade-everything: 53% fade-win vs ~53.5% breakeven = the market is efficient, vig eats the margin.
- **Fade FTUNDER (newunder): LOSES.** On the 11/50 bets with real same-date Over odds, fading = **−1.7u**. Its 54% fade-win is at breakeven. It is NOT a fade spot.
- Overshoot-fade: fade-win 56% but only 2/25 have real odds — unmeasurable.
- **The blocker:** proper two-sided odds only exist from **06-24** (when the board started). Historical complement-odds coverage is **14%** (13/93). You CANNOT properly backtest the fade on the old bets — the contemporaneous other-side price wasn't captured. (Earlier "+2u fade" numbers were small-sample / wrong-date artifacts.)
- **The fix is already running:** the board now captures both sides daily (81% coverage since 06-24). In a few weeks of accumulation, re-run **`python fade_study.py`** for a clean, date-honest answer.

`fade_study.py` = the canonical analysis (stdlib, no pandas). It date-matches the complement odds from board+snapshots and reports per-signal fade-win% + real-odds units + coverage.

---

## Gotchas (will bite a future session)
1. **graded_bets result casing:** wins are `WIN`, losses are `loss`. Filtering `=='win'` silently drops every win.
2. **Complement odds MUST be date-matched.** Matching by player+line only back-applies today's board to old bets (inflated my coverage to a bogus 46%; true is 26%).
3. **Shell `git add f1 f2 …` aborts the whole add if ANY file is missing** (e.g. lineups_log.csv before a live game) -> "nothing staged" with real data lost. Use a per-file `[ -f ] && git add` loop.
4. **`import platform; platform._wmi=None` BEFORE `import pandas`** on this box, or pandas hangs forever (WMI wedged). `fade_study.py`/`capture_news.py` are stdlib to avoid it.
5. **taskkill is broken** here — use `Stop-Process -Id`. WMI process queries hang — use `schtasks /query` + Get-Process.
6. The 21 untracked files in the tree (atoms*, *.bak.csv, old research .py) are harmless leftovers — pulls/watchdog only touch tracked files.

---

## One TODO for the user
**Revoke the the-odds-api key** `387645d689cd646ead0f9680f15e3713` at the-odds-api.com — it was hardcoded, removed from current code, but still in git HISTORY (public repo). Free-tier + unused, 30-second job. Nothing uses it anymore.

---

## To pick this back up in 2 months
1. `cd C:\Users\Axioo\wnba-line-capture && git pull`
2. `python fade_study.py` — the fade answer, now on a real two-sided sample.
3. Check `graded_bets.csv` growth + the dashboard. Re-slice signals with `signal_matrix.py`.
4. If anything looks stale: check `watchdog_wnba.log` and GitHub Actions for the repo.
