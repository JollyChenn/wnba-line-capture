#!/usr/bin/env python
"""Proxy for the user's 'hidden-issue' hypothesis. We have NO half/quarter splits (box is
full-game), so we test the closest thing: does a game where the player was ON THE FLOOR
(full minutes) but UNDER-PRODUCED (a possible developing injury/fatigue tell) predict the
NEXT game also coming in under their median? Compared against benched games and the base rate.
All rotation player-games (med_min>=15, >=4 prior, a next game exists). Pure stdlib."""
import csv
import statistics
import sys
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def nd(d):
    return ''.join(c for c in str(d) if c.isdigit())[:8]


gdate = {r["game_id"]: nd(r.get("date", "")) for r in csv.DictReader(open("data/games_2026.csv", encoding="utf-8"))}
log = defaultdict(list)
for r in csv.DictReader(open("data/box_2026.csv", encoding="utf-8")):
    d = gdate.get(r["game_id"])
    if not d:
        continue
    try:
        log[r["player"].lower()].append((d, float(r["pts"]), float(r["min"])))
    except (ValueError, TypeError):
        continue

# rows: (klass, next_under, next_min_drop)
rows = []
for pl, gl in log.items():
    gl = sorted(gl, key=lambda t: t[0])
    for i in range(len(gl)):
        if i < 4 or i + 1 >= len(gl):                      # need history + a next game
            continue
        prior = gl[:i]
        med = statistics.median([g[1] for g in prior][-10:])
        med_min = statistics.median([g[2] for g in prior][-10:])
        if med_min < 15 or med <= 0:
            continue
        cur_pts, cur_min = gl[i][1], gl[i][2]
        full = cur_min >= 0.85 * med_min                   # was on the floor his usual amount
        bad = cur_pts <= 0.75 * med                        # produced 25%+ under his median
        if full and bad:
            klass = "INEFFECTIVE (full min, bad output)"
        elif not full:
            klass = "benched (low minutes)"
        elif cur_pts >= 1.15 * med:
            klass = "good game"
        else:
            klass = "normal"
        # the NEXT game
        nxt = gl[i + 1]
        nmed = statistics.median([g[1] for g in gl[:i + 1]][-10:])
        rows.append((klass, 1 if nxt[1] < nmed else 0, 1 if nxt[2] < med_min else 0))

base_under = sum(r[1] for r in rows) / len(rows)
print(f"player-game transitions tested: {len(rows)}")
print(f"BASE: next game comes in UNDER its median = {base_under*100:.0f}%\n")
print(f"{'this game was…':<34}{'n':>5}{'NEXT under median':>20}{'NEXT fewer minutes':>20}")
order = ["good game", "normal", "benched (low minutes)", "INEFFECTIVE (full min, bad output)"]
groups = defaultdict(list)
for r in rows:
    groups[r[0]].append(r)
for k in order:
    g = groups.get(k, [])
    if not g:
        continue
    nu = sum(r[1] for r in g) / len(g)
    nm = sum(r[2] for r in g) / len(g)
    flag = "  <-- the tell?" if k.startswith("INEFFECTIVE") and nu > base_under + 0.04 else ""
    print(f"{k:<34}{len(g):>5}{nu*100:>18.0f}%{nm*100:>19.0f}%{flag}")
