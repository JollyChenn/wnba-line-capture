#!/usr/bin/env python
"""Re-test, honestly. The 'under trailing median' test is self-centering (~50% by construction),
so it's weak. Measure persistence the RIGHT way:
  1. How CONSISTENT are players in LEVEL?  (coefficient of variation = std/mean)
  2. Real game-to-game PERSISTENCE = lag-1 autocorrelation of points (de-meaned per player).
  3. Direction persistence: after an above-average game, how often is the NEXT one above too?
  4. The fade, continuous: after a 2nd-half fade, the ACTUAL next-game points vs the player's
     average (a real magnitude, not a binary). Pure stdlib."""
import csv
import math
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
        log[r["player"].lower()].append((d, float(r["pts"])))
    except (ValueError, TypeError):
        pass
for pl in log:
    log[pl].sort(key=lambda t: t[0])

# 1. consistency in LEVEL
cvs = []
for pl, gl in log.items():
    pts = [p for _, p in gl]
    if len(pts) >= 8 and statistics.mean(pts) >= 8:
        cvs.append(statistics.pstdev(pts) / statistics.mean(pts))
print(f"1) CONSISTENCY (scorers, n={len(cvs)} players):")
print(f"   coefficient of variation std/mean — median {statistics.median(cvs):.2f}, mean {statistics.mean(cvs):.2f}")
print(f"   => a typical scorer's single game swings ~±{statistics.median(cvs)*100:.0f}% around their average\n")

# 2. lag-1 autocorrelation of de-meaned points (the real persistence measure)
pairs = []
for pl, gl in log.items():
    pts = [p for _, p in gl]
    if len(pts) < 8 or statistics.mean(pts) < 8:
        continue
    for i in range(4, len(pts) - 1):
        m = statistics.mean(pts[max(0, i - 10):i])      # trailing mean BEFORE game i
        pairs.append((pts[i] - m, pts[i + 1] - m))
xs = [a for a, _ in pairs]
ys = [b for _, b in pairs]
mx, my = statistics.mean(xs), statistics.mean(ys)
cov = sum((a - mx) * (b - my) for a, b in pairs) / len(pairs)
r = cov / (statistics.pstdev(xs) * statistics.pstdev(ys))
print(f"2) GAME-TO-GAME PERSISTENCE (n={len(pairs)} pairs):")
print(f"   lag-1 autocorrelation of points = r = {r:+.3f}")
print(f"   r²={r*r*100:.1f}% of next-game variance explained by this game")
print(f"   (r≈0 = single games are noise; r>0.3 = real momentum)\n")

# 3. direction persistence
ab_then_ab = ab = 0
for pl, gl in log.items():
    pts = [p for _, p in gl]
    if len(pts) < 8 or statistics.mean(pts) < 8:
        continue
    for i in range(4, len(pts) - 1):
        m = statistics.mean(pts[max(0, i - 10):i])
        if pts[i] > m:
            ab += 1
            if pts[i + 1] > m:
                ab_then_ab += 1
print(f"3) DIRECTION: after an ABOVE-average game, next is above = {100*ab_then_ab/ab:.0f}%  (50% = coin flip)\n")

# 4. the fade, in REAL points (not under/over). uses per-half data.
hlog = defaultdict(list)
for r in csv.DictReader(open("data/halves_2026.csv", encoding="utf-8")):
    try:
        hlog[r["player"]].append((r["date"], float(r["h1_pts"]), float(r["h2_pts"]), float(r["pts"])))
    except (ValueError, TypeError):
        pass
faded_next, normal_next = [], []
for pl, gl in hlog.items():
    gl.sort(key=lambda t: t[0])
    pts = [g[3] for g in gl]
    if len(pts) < 5 or statistics.mean(pts) < 8:
        continue
    for i in range(4, len(gl) - 1):
        avg = statistics.mean(pts[max(0, i - 10):i])
        nxt_vs_avg = gl[i + 1][3] - avg                 # next game points minus the player's recent average
        if gl[i][1] >= 8 and gl[i][2] <= gl[i][1] - 6:  # 2nd-half fade
            faded_next.append(nxt_vs_avg)
        else:
            normal_next.append(nxt_vs_avg)
print("4) AFTER A 2ND-HALF FADE — next game points vs the player's own average:")
print(f"   after a FADE   : {statistics.mean(faded_next):+.2f} pts vs avg   (n={len(faded_next)})")
print(f"   after NORMAL   : {statistics.mean(normal_next):+.2f} pts vs avg   (n={len(normal_next)})")
print(f"   difference     : {statistics.mean(faded_next)-statistics.mean(normal_next):+.2f} pts  (negative = the fade really does carry over)")
