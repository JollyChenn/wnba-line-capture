#!/usr/bin/env python
"""THE 2ND-HALF FADE TEST (the user's hypothesis). Using per-half points from ESPN pbp:
does a player who SCORED in the 1st half but DROPPED OFF in the 2nd (a possible fatigue/
injury tell) come in UNDER their points median the NEXT game? vs base rate + a surge control.
Scorers only (median pts >=8). Pure stdlib."""
import csv
import statistics
import sys
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

log = defaultdict(list)
for r in csv.DictReader(open("data/halves_2026.csv", encoding="utf-8")):
    try:
        log[r["player"]].append((r["date"], float(r["h1_pts"]), float(r["h2_pts"]), float(r["pts"])))
    except (ValueError, TypeError):
        pass

rows = []   # (faded, faded_ratio, surged, next_under, next_also_fade)
for pl, gl in log.items():
    gl = sorted(gl, key=lambda t: t[0])
    for i in range(len(gl)):
        if i < 4 or i + 1 >= len(gl):
            continue
        med = statistics.median([g[3] for g in gl[:i]][-10:])
        if med < 8:                                     # real scorers (need room to fade)
            continue
        _, h1, h2, tot = gl[i]
        faded = (h1 >= 8 and h2 <= h1 - 6)              # scored 8+ in H1, dropped 6+ in H2
        faded_ratio = (tot >= 8 and h2 <= 0.30 * tot)   # scored <=30% of pts in H2
        surged = (h2 >= 8 and h1 <= h2 - 6)             # opposite control
        nxt = gl[i + 1]
        nmed = statistics.median([g[3] for g in gl[:i + 1]][-10:])
        next_under = nxt[3] < nmed
        next_also_fade = (nxt[1] >= 8 and nxt[2] <= nxt[1] - 6)
        rows.append((faded, faded_ratio, surged, next_under, next_also_fade))

base = sum(r[3] for r in rows) / len(rows)
print(f"transitions tested: {len(rows)}")
print(f"BASE: next game pts UNDER median = {base*100:.0f}%\n")


def rate(items):
    n = len(items)
    if not n:
        return "—"
    u = sum(r[3] for r in items)
    return f"{u / n * 100:4.0f}%  (n={n})"


print(f"{'group':<42}{'next UNDER median':>18}")
print(f"  no 2nd-half fade{'':<25}{rate([r for r in rows if not r[0]]):>18}")
print(f"  ★ 2ND-HALF FADE (H1>=8, H2<=H1-6){'':<8}{rate([r for r in rows if r[0]]):>18}")
print(f"  2nd-half fade by RATIO (H2<=30% pts){'':<5}{rate([r for r in rows if r[1]]):>18}")
print(f"  2nd-half SURGE control (H2>>H1){'':<11}{rate([r for r in rows if r[2]]):>18}")

faded = [r for r in rows if r[0]]
if faded:
    nf = sum(r[4] for r in faded) / len(faded)
    bf = sum(r[4] for r in rows) / len(rows)
    print(f"\ndoes the fade REPEAT? faded -> next game also fades = {nf*100:.0f}%  (base {bf*100:.0f}%)")
