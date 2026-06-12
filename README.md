# wnba-line-capture

Two cloud jobs on free GitHub Actions — the full WNBA betting loop, laptop off:

| Workflow | Schedule | What it does |
|----------|----------|--------------|
| `capture-wnba-lines` | hourly | snapshots Pinnacle/EU WNBA prop lines near tip → `line_snapshots.csv` (the CLV benchmark) |
| `daily-picks` | 14:00 UTC daily | pulls fresh ESPN data, generates **core-only** picks → `PICKS.md` + `picks_log.csv` |

## REAL-MONEY RULES (core only, validated 11-season backtest)
- Bet ONLY what `PICKS.md` lists: **any-2-of-3 UNDERs** (61.6%, ~3/wk) and
  **CASCADE overs** when the named starter is actually ruled out (57.0%, ~2/wk).
- Flat 1u stakes (1-2% of bankroll). No singles, no parlays, never Clark props.
- Bet at 1xbet only when its line is AT/ABOVE the listed anchor (unders) or
  AT/BELOW (cascade overs) — that's the book being slow, which IS the edge.
- Grade weekly: `picks_log.csv` vs `line_snapshots.csv` closes (CLV). Two weeks
  of positive CLV = scale up; negative = stop and reassess.

## Why
The role-lag backtest showed a real signal (PRA/PTS under when minutes shrink,
~59%) but Pinnacle prices it in. The edge, if any, is at a **soft book (1xbet)** —
and the only way to prove it is **CLV vs Pinnacle's close**. This repo records
Pinnacle's WNBA prop lines every hour so we have the closing number to grade against.
(1xbet isn't on the-odds-api — capture that separately; this is the benchmark half.)

## What it does
- Hourly cron hits the-odds-api. The `/events` check is **FREE**, so runs with no
  game near tip spend **nothing**.
- When a WNBA game is within 90 min of tip, it pulls **points + PRA** props from
  **EU books (Pinnacle)** and appends them to `line_snapshots.csv`, committed back here.
- Quota: ~120 requests/month (shared 500/mo key with the MLB bot). Tune via secrets.

## One-time setup
1. **Create a GitHub repo** (private is fine) and push these files:
   ```
   cd C:\Users\Axioo\wnba-line-capture
   git init && git add -A && git commit -m "wnba line capture"
   git branch -M main
   git remote add origin https://github.com/<you>/wnba-line-capture.git
   git push -u origin main
   ```
2. **Add the API key secret**: repo → Settings → Secrets and variables → Actions →
   New repository secret → name `ODDS_API_KEYS`, value = your the-odds-api key
   (comma-separate two keys to pool ~1000/mo).
3. **Enable Actions**: the Actions tab → enable workflows. Confirm write permission:
   Settings → Actions → General → Workflow permissions → **Read and write**.
4. **Test now**: Actions tab → "capture-wnba-lines" → **Run workflow**. Check the log
   and that `line_snapshots.csv` appears.

## Tuning (repo secrets / workflow env)
| Var | Default | Notes |
|-----|---------|-------|
| `CAPTURE_MARKETS` | `player_points,player_points_rebounds_assists` | add `,player_rebounds,player_assists` for the full role-lag family (more quota) |
| `CAPTURE_REGIONS` | `eu` | Pinnacle. `eu,us` doubles quota — only if you want US books too |
| `CAPTURE_WINDOW_MIN` | `90` | smaller = fewer captures per game = less quota |
| `MAX_GAMES` | `5` | hard per-run cap |

## Then locally
Pull `line_snapshots.csv` and grade CLV: bet line (1xbet) vs Pinnacle close here.
Positive CLV = real edge. That is the only verdict.
