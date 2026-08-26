import platform; platform._wmi = None
import os, sys, json, random, collections
import numpy as np
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, D)
from t4_lib import base
R = base()
# only rows that actually carry a sharp read at each horizon
HOR = ("sharp", "sharp12")
rows = {h: [r for r in R if r[h] is not None] for h in HOR}
for h in HOR:
    for r in rows[h]: r["g_"+h] = r[h] - r["line"]
THR = (0.5, 1.0, 1.5, 2.0); DIRS = ("toward", "over only", "under only")
MKG = (("all", ("pts","pra","pr","pa","reb","ast","ra")), ("pts", ("pts",)),
       ("combos", ("pra","pr","pa","ra")), ("reb/ast", ("reb","ast")))
CELLS = [(th, h, dn, ms) for th in THR for h in HOR for dn in DIRS for nm, ms in MKG]
MINN = 40
def evaluate(gapof):
    out = []
    for th, h, dn, ms in CELLS:
        tot = 0.0; n = 0
        for r in rows[h]:
            if r["mk"] not in ms: continue
            g = gapof[h][id(r)]
            if abs(g) < th: continue
            side = "over" if g > 0 else "under"
            if dn == "over only" and side != "over": continue
            if dn == "under only" and side != "under": continue
            n += 1
            if r["actual"] == r["line"]: continue
            w = (r["actual"] > r["line"]) if side == "over" else (r["actual"] < r["line"])
            tot += ((r["over"] if side == "over" else r["under"])-1) if w else -1.0
        out.append((tot/n if n >= MINN else -9.0, n))
    return out
real_gap = {h: {id(r): r["g_"+h] for r in rows[h]} for h in HOR}
rv = evaluate(real_gap)
live_i = CELLS.index((1.0, "sharp", "toward", MKG[0][1]))
print("C2 declared grid: %d cells (4 gap thresholds x 2 sharp horizons x 3 direction rules x 4 market")
print("groups), min n = %d. Cells reaching n: %d" % (MINN, sum(1 for v, n in rv if v > -8)))
order = sorted(range(len(CELLS)), key=lambda i: -rv[i][0])
print("  top 5 real cells:")
for i in order[:5]:
    th, h, dn, ms = CELLS[i]
    print("     |gap|>=%.1f  %-7s %-10s %-7s  n=%-4d ROI %+6.1f%%" % (
        th, h, dn, [nm for nm, m in MKG if m == ms][0], rv[i][1], 100*rv[i][0]))
print("  LIVE cell (|gap|>=1, 6h read, toward, all markets): n=%d ROI %+.1f%%" % (rv[live_i][1], 100*rv[live_i][0]))
# NULL: reshuffle the gap among each player's own sharp-bearing rows, per horizon
byp = {h: collections.defaultdict(list) for h in HOR}
for h in HOR:
    for r in rows[h]: byp[h][r["pl"]].append(r)
rr = random.Random(2026)
T = 1200
best = []; livesim = []
for _ in range(T):
    gm = {h: {} for h in HOR}
    for h in HOR:
        for pl, v in byp[h].items():
            gs = [x["g_"+h] for x in v]; rr.shuffle(gs)
            for x, g in zip(v, gs): gm[h][id(x)] = g
    ev = evaluate(gm)
    best.append(max(v for v, n in ev))
    livesim.append(ev[live_i][0])
best.sort(); livesim.sort()
p95 = best[int(.95*T)]
print("")
print("  NULL = reshuffle the gap among each player's own sharp-bearing quotes (%d draws)" % T)
print("  best-of-grid under null: median %+.1f%%  p95 %+.1f%%  max %+.1f%%" % (
    100*best[T//2], 100*p95, 100*best[-1]))
bestreal = max(v for v, n in rv)
print("  best REAL cell %+.1f%%  ->  %s the ceiling" % (
    100*bestreal, "CLEARS" if bestreal >= p95 else "does NOT clear"))
print("  LIVE cell %+.1f%% vs its OWN single-cell null: p = %.4f (median %+.1f%%)" % (
    100*rv[live_i][0], sum(1 for x in livesim if x >= rv[live_i][0])/T, 100*livesim[T//2]))
json.dump({"c2_p95": float(p95), "c2_best_real": float(bestreal),
           "c2_live_roi": float(rv[live_i][0]), "c2_live_n": rv[live_i][1],
           "c2_live_p": sum(1 for x in livesim if x >= rv[live_i][0])/T},
          open(os.path.join(D, "outputs", "t4_c2ceil.json"), "w"), indent=1)
