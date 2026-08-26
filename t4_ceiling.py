# TRACK 4 - NOISE CEILINGS, DECLARED AND COMPUTED BEFORE ANY REAL RESULT IS READ.
# Three grids, each matched to the level at which the claim's label lives.
import platform; platform._wmi = None
import os, sys, json, math, random, statistics, collections
import numpy as np
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
from t4_lib import base
R = base()
SIGS = ("flip", "hotover", "overshoot"); BM = ("pra", "pr", "pts")
ALLMK = ("pts", "pra", "pr", "pa", "reb", "ast", "ra")
OUT = {}

# ============================ GRID U : the signal-candidate universe ==========================
U = [r for r in R if any(s in SIGS for s in r["srcs"])]
print("GRID U universe: %d quotes, %d games, %d players" % (
    len(U), len(set(r["gt"] for r in U)), len(set(r["pl"] for r in U))))
srcsets = []
for m in range(1, 8):
    srcsets.append(tuple(s for i, s in enumerate(SIGS) if m >> i & 1))
mksets = []
for m in range(1, 8):
    mksets.append(tuple(s for i, s in enumerate(BM) if m >> i & 1))
mksets.append(ALLMK)
GATES = [("none", None), ("mv<0.5", 0.5), ("mv<0.0", 0.0), ("mv<1.0", 1.0),
         ("mv<2.0", 2.0), ("mv>=0.5", -1)]
CELLS_U = []
for ss in srcsets:
    for ms in mksets:
        for gn, gv in GATES:
            CELLS_U.append(("src%s|mk%s|%s" % ("+".join(x[:4] for x in ss), "+".join(ms), gn), ss, ms, gv))
print("GRID U declared: %d cells (7 src subsets x 8 market subsets x 6 line gates), min n = 25" % len(CELLS_U))

pl_idx = {}
for r in U: pl_idx.setdefault(r["pl"], len(pl_idx))
plarr = np.array([pl_idx[r["pl"]] for r in U])
price = np.array([r["over"] for r in U])
won0 = np.array([1.0 if r["actual"] > r["line"] else 0.0 for r in U])
masks = []
for nm, ss, ms, gv in CELLS_U:
    m = np.array([
        (any(s in ss for s in r["srcs"])) and (r["mk"] in ms) and
        (True if gv is None else
         (r["prev"] is not None and (r["line"] - r["prev"] < gv if gv >= 0 else r["line"] - r["prev"] >= 0.5)))
        for r in U], dtype=bool)
    masks.append(m)
M = np.array(masks)
NN = M.sum(axis=1)
ok = NN >= 25
print("   cells reaching n>=25: %d" % ok.sum())

def grid_roi(w):
    pay = np.where(w > 0.5, price - 1.0, -1.0)
    tot = M @ pay
    with np.errstate(invalid="ignore", divide="ignore"):
        v = np.where(ok, tot/np.maximum(NN, 1), -9.0)
    return v

rng = np.random.default_rng(20260826)
blocks = collections.defaultdict(list)
for i, p in enumerate(plarr): blocks[p].append(i)
blist = [np.array(v) for v in blocks.values()]
T = 3000
best = np.empty(T)
for k in range(T):
    w = won0.copy()
    for idx in blist:
        w[idx] = rng.permutation(w[idx])
    best[k] = grid_roi(w).max()
best.sort()
p95U = best[int(0.95*T)]
print("   NULL = shuffle outcome within PLAYER block (preserves each player's own over-rate)")
print("   GRID U NOISE CEILING: median best-cell %+.1f%%   p95 %+.1f%%   max %+.1f%%" % (
    100*best[T//2], 100*p95U, 100*best[-1]))
OUT["gridU_p95"] = float(p95U); OUT["gridU_med"] = float(best[T//2]); OUT["gridU_cells"] = int(ok.sum())
OUT["gridU_n"] = len(U)

# ============================ GRID G : game-level labels on the full board ====================
G = [r for r in R if r["tot"] is not None]
print("")
print("GRID G universe: %d quotes, %d games" % (len(G), len(set(r["gt"] for r in G))))
gt_of = {}
for r in G: gt_of[r["gt"]] = r["tot"]
gids = sorted(gt_of)
gidx = {g: i for i, g in enumerate(gids)}
garr = np.array([gidx[r["gt"]] for r in G])
gtot = np.array([gt_of[g] for g in gids])
priceO = np.array([r["over"] for r in G]); priceU = np.array([r["under"] for r in G])
wonG = np.array([1.0 if r["actual"] > r["line"] else 0.0 for r in G])
mkarr = [r["mk"] for r in G]
CUTS = [("high half", 0.5, 1), ("low half", 0.5, 0), ("top tercile", 2/3., 1), ("bot tercile", 1/3., 0),
        ("top quartile", 0.75, 1), ("bot quartile", 0.25, 0)]
MKG = [("all", ALLMK), ("pts", ("pts",)), ("pra", ("pra",)), ("pr", ("pr",))]
CELLS_G = [(c[0], c, m, s) for c in CUTS for m in MKG for s in ("over", "under")]
print("GRID G declared: %d cells (6 total-cuts x 4 market groups x 2 sides), min n = 120" % len(CELLS_G))
mkmask = {nm: np.array([m in ms for m in mkarr]) for nm, ms in MKG}

def gridG(tv):
    rowtot = tv[garr]
    out = []
    for cn, (nm, q, hi) in [(c[0], c[1]) for c in CELLS_G][:0]: pass
    for cnm, cc, (mnm, ms), side in CELLS_G:
        nm, q, hi = cc
        thr = np.quantile(tv, q)
        sel = (rowtot >= thr) if hi else (rowtot < thr)
        sel = sel & mkmask[mnm]
        n = sel.sum()
        if n < 120: out.append(-9.0); continue
        if side == "over": pay = np.where(wonG > 0.5, priceO-1.0, -1.0)
        else:              pay = np.where(wonG < 0.5, priceU-1.0, -1.0)
        out.append(float(pay[sel].sum()/n))
    return np.array(out)

T2 = 2000
bestG = np.empty(T2)
for k in range(T2):
    bestG[k] = gridG(rng.permutation(gtot)).max()
bestG.sort()
p95G = bestG[int(0.95*T2)]
print("   NULL = permute the game TOTAL across games (label lives on the game)")
print("   GRID G NOISE CEILING: median best-cell %+.1f%%   p95 %+.1f%%   max %+.1f%%" % (
    100*bestG[T2//2], 100*p95G, 100*bestG[-1]))
OUT["gridG_p95"] = float(p95G); OUT["gridG_med"] = float(bestG[T2//2]); OUT["gridG_n"] = len(G)

# ============================ GRID P : player x market level labels ===========================
P = [r for r in R if r["relvol"] is not None and r["mean_ct"] is not None]
print("")
print("GRID P universe: %d quotes, %d player-market blocks" % (len(P), len(set((r["pl"], r["mk"]) for r in P))))
bkey = {}
for r in P: bkey.setdefault((r["pl"], r["mk"]), len(bkey))
barr = np.array([bkey[(r["pl"], r["mk"])] for r in P])
blab = {}
for r in P: blab.setdefault((r["pl"], r["mk"]), (r["relvol"], r["sd"], r["mean_ct"]/max(r["line"],1.0), r["mk"]))
bl = [blab[k] for k in sorted(bkey, key=lambda k: bkey[k])]
LV = {"relvol": np.array([x[0] for x in bl]), "sd": np.array([x[1] for x in bl]),
      "meanratio": np.array([x[2] for x in bl])}
bmk = [x[3] for x in bl]
priceOP = np.array([r["over"] for r in P]); priceUP = np.array([r["under"] for r in P])
wonP = np.array([1.0 if r["actual"] > r["line"] else 0.0 for r in P])
mkarrP = [r["mk"] for r in P]
mkmaskP = {nm: np.array([m in ms for m in mkarrP]) for nm, ms in MKG}
CUTS_P = [("high half", 0.5, 1), ("low half", 0.5, 0), ("top tercile", 2/3., 1), ("bot tercile", 1/3., 0)]
CELLS_P = [(fn, c, m, s) for fn in ("relvol", "sd", "meanratio") for c in CUTS_P
           for m in MKG for s in ("over", "under")]
print("GRID P declared: %d cells (3 player features x 4 cuts x 4 market groups x 2 sides), min n = 120" % len(CELLS_P))

def gridP(vals):
    out = []
    for fn, (cn, q, hi), (mnm, ms), side in CELLS_P:
        v = vals[fn]
        rowv = v[barr]
        thr = np.quantile(v, q)
        sel = (rowv >= thr) if hi else (rowv < thr)
        sel = sel & mkmaskP[mnm]
        n = sel.sum()
        if n < 120: out.append(-9.0); continue
        if side == "over": pay = np.where(wonP > 0.5, priceOP-1.0, -1.0)
        else:              pay = np.where(wonP < 0.5, priceUP-1.0, -1.0)
        out.append(float(pay[sel].sum()/n))
    return np.array(out)

# permute the player-market label WITHIN market so market composition is preserved
mkgroups = collections.defaultdict(list)
for i, m in enumerate(bmk): mkgroups[m].append(i)
mkgroups = {k: np.array(v) for k, v in mkgroups.items()}
T3 = 1500
bestP = np.empty(T3)
for k in range(T3):
    vv = {}
    for fn, arr in LV.items():
        a = arr.copy()
        for m, idx in mkgroups.items(): a[idx] = rng.permutation(a[idx])
        vv[fn] = a
    bestP[k] = gridP(vv).max()
bestP.sort()
p95P = bestP[int(0.95*T3)]
print("   NULL = permute the player-market volatility label across players WITHIN market")
print("   GRID P NOISE CEILING: median best-cell %+.1f%%   p95 %+.1f%%   max %+.1f%%" % (
    100*bestP[T3//2], 100*p95P, 100*bestP[-1]))
OUT["gridP_p95"] = float(p95P); OUT["gridP_med"] = float(bestP[T3//2]); OUT["gridP_n"] = len(P)
OUT["gridU_cellcount"] = len(CELLS_U); OUT["gridG_cellcount"] = len(CELLS_G); OUT["gridP_cellcount"] = len(CELLS_P)
json.dump(OUT, open(os.path.join(D, "outputs", "t4_ceilings.json"), "w"), indent=1)
print("")
print("CEILINGS WRITTEN. Any cell below its grid's p95 is indistinguishable from luck.")
