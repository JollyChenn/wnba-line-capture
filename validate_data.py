# validate_data.py — gate the data BEFORE we trust the picks. Runs in the daily-picks
# workflow right after the model. Checks: freshness, enough games, in-range values,
# no duplicate player-games, picks complete. Exits 1 (warning) if anything's off.
import csv, sys, datetime
from zoneinfo import ZoneInfo
from collections import Counter

issues = []
games = {r["game_id"]: r for r in csv.DictReader(open("data/games_2026.csv", encoding="utf-8"))}
box = list(csv.DictReader(open("data/box_2026.csv", encoding="utf-8")))
dts = sorted(set(games.get(r["game_id"], {}).get("date", "") for r in box if r["game_id"] in games and games.get(r["game_id"], {}).get("date")))
latest = dts[-1] if dts else None
today = datetime.datetime.now(ZoneInfo("America/Los_Angeles")).date()

# 1) freshness
if latest:
    ld = datetime.datetime.strptime(latest, "%Y%m%d").date()
    if (today - ld).days > 4:
        issues.append(f"STALE: newest box game {latest} is {(today - ld).days} days old")
else:
    issues.append("NO dated box games")
# 2) enough data
if len(box) < 200:
    issues.append(f"THIN: only {len(box)} player-games")
# 3) value sanity
bad = 0
for r in box:
    try:
        p, m, rb, a = float(r["pts"]), float(r["min"]), float(r["reb"]), float(r["ast"])
        if not (0 <= p <= 70 and 0 <= m <= 50 and 0 <= rb <= 35 and 0 <= a <= 25):
            bad += 1
    except (ValueError, KeyError):
        bad += 1
if bad > len(box) * 0.02:
    issues.append(f"BAD VALUES: {bad} rows out of plausible range")
# 4) duplicate player-games
dups = sum(1 for v in Counter((r["game_id"], r["player"]) for r in box).values() if v > 1)
if dups:
    issues.append(f"DUPLICATES: {dups} duplicate player-games")
# 5) picks complete
rows = list(csv.DictReader(open("picks_log.csv", encoding="utf-8"))) if __import__("os").path.exists("picks_log.csv") else []
slate = max((r["pick_date"] for r in rows), default=None)
tdy = [r for r in rows if r["pick_date"] == slate]
if not tdy:
    issues.append("NO picks for the latest slate")
else:
    if slate != today.isoformat():            # daily_picks runs with `|| true`; if it silently failed, the newest slate is yesterday's
        issues.append(f"STALE PICKS: newest slate {slate} is not today ({today.isoformat()}) — daily_picks may have failed")
    if sum(1 for r in tdy if r.get("sd")) < len(tdy) * 0.9:
        issues.append("sd missing on >10% of picks")

print(f"DATA VALIDATION — box: {len(box)} player-games (newest {latest}) | picks slate: {slate} ({len(tdy)} picks)")
if issues:
    print("❌ DATA ISSUES:")
    for i in issues:
        print("   -", i)
    sys.exit(1)
print("✅ DATA VALID — fresh, in-range, no duplicates, picks complete")
