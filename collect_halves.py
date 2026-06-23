#!/usr/bin/env python
"""Collect per-HALF player points from ESPN play-by-play (the box is full-game only).
For each played game: parse scoring plays, attribute scoreValue to the scorer (name before
' makes ' in the play text) and the half (period 1-2 = 1st, 3-4 = 2nd). Writes
data/halves_2026.csv and validates the reconstructed total against the box-score pts.
Run on a machine with network (laptop/cloud). Pure stdlib."""
import csv
import json
import statistics
import time
import urllib.request
from collections import defaultdict

games = []
for r in csv.DictReader(open("data/games_2026.csv", encoding="utf-8")):
    if (r.get("home_score") or "") not in ("", None):       # played games only
        games.append((r["game_id"], r.get("date", "")))
print(f"games to fetch: {len(games)}")

ROWS = []
ok = fail = 0
for i, (gid, date) in enumerate(games):
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/summary?event={gid}"
        d = json.load(urllib.request.urlopen(url, timeout=30))
        per = defaultdict(lambda: [0, 0])                   # player -> [h1, h2]
        for p in (d.get("plays") or []):
            if not p.get("scoringPlay"):
                continue
            sv = p.get("scoreValue") or 0
            t = p.get("text") or ""
            if sv <= 0 or " makes " not in t:
                continue
            name = t.split(" makes ")[0].strip().lower()
            num = (p.get("period") or {}).get("number") or 0
            per[name][0 if num <= 2 else 1] += sv
        for name, (h1, h2) in per.items():
            ROWS.append([gid, date, name, h1, h2, h1 + h2])
        ok += 1
    except Exception:
        fail += 1
    time.sleep(0.25)
    if (i + 1) % 25 == 0:
        print(f"  {i + 1}/{len(games)}  ok={ok} fail={fail}")

with open("data/halves_2026.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["game_id", "date", "player", "h1_pts", "h2_pts", "pts"])
    w.writerows(ROWS)
print(f"wrote data/halves_2026.csv: {len(ROWS)} player-games (ok={ok} fail={fail})")

# validation: reconstructed total vs the box-score pts (should match if attribution is right)
boxpts = {}
for r in csv.DictReader(open("data/box_2026.csv", encoding="utf-8")):
    try:
        boxpts[(r["game_id"], r["player"].lower())] = float(r["pts"])
    except (ValueError, TypeError):
        pass
diffs = [abs(tot - boxpts[(gid, name)]) for gid, date, name, h1, h2, tot in ROWS if (gid, name) in boxpts]
if diffs:
    print(f"VALIDATION vs box pts: matched {len(diffs)} rows · mean|diff|={statistics.mean(diffs):.2f} · "
          f"exact={sum(1 for x in diffs if x < 0.5)}/{len(diffs)} ({100*sum(1 for x in diffs if x<0.5)/len(diffs):.0f}%)")
