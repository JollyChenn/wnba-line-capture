# GRID U ceiling as a function of minimum cell size -- Model S sits at n=119, so the honest
# comparison is against the best-of-grid among cells of comparable size.
import platform; platform._wmi = None
import os, sys, json, collections
import numpy as np
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, D)
from t4_lib import base
R = base()
SIGS = ("flip", "hotover", "overshoot"); BM = ("pra", "pr", "pts")
ALLMK = ("pts", "pra", "pr", "pa", "reb", "ast", "ra")
U = [r for r in R if any(s in SIGS for s in r["srcs"])]
srcsets = [tuple(s for i, s in enumerate(SIGS) if m >> i & 1) for m in range(1, 8)]
mksets = [tuple(s for i, s in enumerate(BM) if m >> i & 1) for m in range(1, 8)] + [ALLMK]
GATES = [("none", None), ("mv<0.5", 0.5), ("mv<0.0", 0.0), ("mv<1.0", 1.0), ("mv<2.0", 2.0), ("mv>=0.5", -1)]
CELLS = [("src=%s | mk=%s | %s" % ("+".join(x[:4] for x in ss), "+".join(ms) if len(ms) < 7 else "ALL", gn), ss, ms, gv)
         for ss in srcsets for ms in mksets for gn, gv in GATES]
price = np.array([r["over"] for r in U])
won0 = np.array([1.0 if r["actual"] > r["line"] else 0.0 for r in U])
M = np.array([[(any(s in ss for s in r["srcs"])) and (r["mk"] in ms) and
               (True if gv is None else (r["prev"] is not None and
                (r["line"]-r["prev"] < gv if gv >= 0 else r["line"]-r["prev"] >= 0.5)))
               for r in U] for nm, ss, ms, gv in CELLS], dtype=bool)
NN = M.sum(axis=1)
rng = np.random.default_rng(20260826)
blocks = collections.defaultdict(list)
for i, r in enumerate(U): blocks[r["pl"]].append(i)
blist = [np.array(v) for v in blocks.values()]
pay0 = np.where(won0 > 0.5, price-1.0, -1.0)
real_all = (M @ pay0)/np.maximum(NN, 1)
T = 4000
sims = np.empty((T, len(CELLS)))
for k in range(T):
    w = won0.copy()
    for idx in blist: w[idx] = rng.permutation(w[idx])
    pay = np.where(w > 0.5, price-1.0, -1.0)
    sims[k] = (M @ pay)/np.maximum(NN, 1)
print("GRID U: 336 declared cells. Ceiling by minimum cell size (null = outcome shuffle within player).")
print("%-8s %6s  %10s %10s %10s   | %s" % ("min n", "cells", "null med", "null p95", "null max", "best REAL cell"))
CEIL = {}
for mn in (25, 50, 80, 100, 119, 140):
    ok = NN >= mn
    if ok.sum() == 0: continue
    b = sims[:, ok].max(axis=1); b.sort()
    rb = real_all[ok].max()
    nm = [CELLS[i][0] for i in np.where(ok)[0]][int(np.argmax(real_all[ok]))]
    rn = NN[ok][int(np.argmax(real_all[ok]))]
    CEIL[mn] = dict(p95=float(b[int(.95*T)]), med=float(b[T//2]), mx=float(b[-1]),
                    cells=int(ok.sum()), best_real=float(rb), best_name=nm, best_n=int(rn))
    print("%-8d %6d  %+9.1f%% %+9.1f%% %+9.1f%%   | %+.1f%% n=%d  %s" % (
        mn, ok.sum(), 100*b[T//2], 100*b[int(.95*T)], 100*b[-1], 100*rb, rn, nm))
# where does MODEL_S itself sit
i_ms = [i for i, c in enumerate(CELLS) if c[0] == "src=flip+hoto+over | mk=pts+pra+pr | mv<0.5"]
if not i_ms:
    i_ms = [i for i, c in enumerate(CELLS) if c[1] == tuple(SIGS) and set(c[2]) == set(BM) and c[3] == 0.5]
i = i_ms[0]
print("")
print("MODEL_S cell = '%s'  n=%d  ROI %+.1f%%" % (CELLS[i][0], NN[i], 100*real_all[i]))
print("   its own single-cell permutation p (player block) = %.4f" % (((sims[:, i] >= real_all[i]).sum()+1)/(T+1)))
print("   percentile of MODEL_S inside the null best-of-grid at min n=100: %.3f" % (
    (sims[:, NN >= 100].max(axis=1) >= real_all[i]).mean()))
json.dump(CEIL, open(os.path.join(D, "outputs", "t4_ceilU_byn.json"), "w"), indent=1)
