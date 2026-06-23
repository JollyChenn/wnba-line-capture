#!/usr/bin/env python
"""BACKTEST: does the PRE-GAME minutes trend (t5−t10) predict (1) actual minutes and
(2) the stat landing UNDER its median? Tested on ALL rotation player-games (med_min≥15,
≥6 prior games) — NOT the bot's 87 selected bets, so no selection bias.
'under median' = would win an under at the trailing-10 median anchor (synthetic line:
proves the SIDE, not that it beats the book). Pure stdlib."""
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
        log[r["player"].lower()].append((d, float(r["min"]), float(r["pts"]), float(r["reb"]), float(r["ast"])))
    except (ValueError, TypeError):
        continue

# obs = (trend, actual_min, med_min, actual_pts, med_pts, actual_pra, med_pra)
obs = []
for pl, gl in log.items():
    gl = sorted(gl, key=lambda t: t[0])
    for i in range(len(gl)):
        if i < 6:
            continue
        prior, cur = gl[:i], gl[i]
        pm = [g[1] for g in prior]
        med_min = statistics.median(pm[-10:])
        if med_min < 15:                          # rotation players only (props live here)
            continue
        trend = statistics.mean(pm[-5:]) - statistics.mean(pm[-10:])
        med_pts = statistics.median([g[2] for g in prior][-10:])
        pra_prior = [g[2] + g[3] + g[4] for g in prior]
        med_pra = statistics.median(pra_prior[-10:])
        obs.append((trend, cur[1], med_min, cur[2], med_pts, cur[2] + cur[3] + cur[4], med_pra))

print(f"rotation player-games tested: {len(obs)}  (vs the bot's 87 selected bets)\n")

BUCKETS = ["shrinking (≤−3)", "flat (−3..+3)", "expanding (≥+3)"]


def bk(t):
    return BUCKETS[0] if t <= -3 else BUCKETS[2] if t >= 3 else BUCKETS[1]


groups = defaultdict(list)
for o in obs:
    groups[bk(o[0])].append(o)


def pctf(items, f):
    n = len(items)
    k = sum(1 for o in items if f(o))
    return f"{100 * k / n:4.0f}%  (n={n})" if n else "—"


print("=== TEST 1 — does the trend predict ACTUAL minutes? ===")
print(f"  BASE (all): played below median minutes = {pctf(obs, lambda o: o[1] < o[2])}")
for b in BUCKETS:
    g = groups[b]
    drop = statistics.mean([o[1] - o[2] for o in g]) if g else 0
    print(f"  {b:<16} avg minutes vs median {drop:+5.1f}   played-below-median {pctf(g, lambda o: o[1] < o[2])}")

print("\n=== TEST 2 — does the trend predict PTS vs its median? ===")
print(f"  BASE (all): pts UNDER median = {pctf(obs, lambda o: o[3] < o[4])}")
for b in BUCKETS:
    g = groups[b]
    print(f"  {b:<16} pts UNDER median {pctf(g, lambda o: o[3] < o[4])}    pts OVER median {pctf(g, lambda o: o[3] > o[4])}")

print("\n=== TEST 2b — same for PRA ===")
print(f"  BASE (all): pra UNDER median = {pctf(obs, lambda o: o[5] < o[6])}")
for b in BUCKETS:
    g = groups[b]
    print(f"  {b:<16} pra UNDER median {pctf(g, lambda o: o[5] < o[6])}    pra OVER median {pctf(g, lambda o: o[5] > o[6])}")
