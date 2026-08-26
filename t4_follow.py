import platform; platform._wmi = None
import os, sys, json, math, random, statistics, collections
import numpy as np
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, D)
from t4_lib import base, boot_ci_by_game
R = base(); LOG = []
def P(s=""):
    print(s); LOG.append(s)
def spear(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    rx = np.argsort(np.argsort(x)).astype(float); ry = np.argsort(np.argsort(y)).astype(float)
    rx -= rx.mean(); ry -= ry.mean()
    return float((rx@ry)/math.sqrt((rx@rx)*(ry@ry)))
rng = np.random.default_rng(7)
SIGS = ("flip", "hotover", "overshoot")

P("="*100)
P("C3 FOLLOW-UP: the original claim was rho +0.074, p=0.0165. Which specification gives that?")
P("="*100)
G = [r for r in R if r["tot"] is not None]
gt_of = {r["gt"]: r["tot"] for r in G}
gids = sorted(gt_of); gidx = {g: i for i, g in enumerate(gids)}
garr = np.array([gidx[r["gt"]] for r in G]); gvals = np.array([gt_of[g] for g in gids])
SPECS = {
  "over_won (0/1)":            [1.0 if r["actual"] > r["line"] else 0.0 for r in G],
  "actual - line":             [r["actual"]-r["line"] for r in G],
  "(actual-line)/player sd":   [(r["actual"]-r["line"])/max(r["sd"] or 1, 1) for r in G],
  "over PnL at board price":   [(r["over"]-1) if r["actual"] > r["line"] else -1.0 for r in G],
  "actual (raw production)":   [r["actual"] for r in G],
}
for nm, y in SPECS.items():
    rho = spear(gvals[garr], y)
    yy = np.array(y, float); beat = 0; T = 3000
    for _ in range(T):
        if abs(spear(rng.permutation(gvals)[garr], yy)) >= abs(rho): beat += 1
    P("   %-28s rho %+.4f   GAME-block label perm p (two-sided) = %.4f" % (nm, rho, (beat+1)/(T+1)))
P("   A quote-level shuffle instead of a GAME-block one (what would produce a small p wrongly):")
y = np.array(SPECS["over_won (0/1)"])
rho = spear(gvals[garr], y); beat = 0
for _ in range(3000):
    if abs(spear(gvals[garr], rng.permutation(y))) >= abs(rho): beat += 1
P("      over_won, QUOTE-level shuffle: rho %+.4f  p = %.4f   <-- 2926 fake independent units" % (rho, (beat+1)/3001))
P("      the game-block version of the same statistic is p = %.4f. 50 games is the real n." % (
    (lambda: (sum(1 for _ in range(1)) ))() or 0.0))
# proper game-block p for over_won
beat = 0
for _ in range(3000):
    if abs(spear(rng.permutation(gvals)[garr], y)) >= abs(rho): beat += 1
P("      -> game-block p = %.4f" % ((beat+1)/3001))
P("   ALSO: only %d distinct games carry a Pinnacle total. That is the independent n for C3." % len(gids))

P("")
P("="*100)
P("C2 FOLLOW-UP: coverage split, direction split, and independence from the Model S signal")
P("="*100)
S = [r for r in R if r["sharp"] is not None]
for r in S: r["gap"] = round(r["sharp"]-r["line"], 2)
B1 = [r for r in S if abs(r["gap"]) >= 1]
def bet(r):
    side = "over" if r["gap"] > 0 else "under"
    if r["actual"] == r["line"]: return None
    w = (r["actual"] > r["line"]) if side == "over" else (r["actual"] < r["line"])
    return ((r["over"] if side == "over" else r["under"])-1) if w else -1.0
def roi(v):
    x = [bet(r) for r in v]; x = [q for q in x if q is not None]
    return (sum(x)/len(v)) if v else 0.0
def wr(v):
    n = 0; w = 0
    for r in v:
        side = "over" if r["gap"] > 0 else "under"
        if r["actual"] == r["line"]: continue
        n += 1; w += 1 if ((r["actual"] > r["line"]) if side == "over" else (r["actual"] < r["line"])) else 0
    return 100*w/max(n, 1)
P("  source split (pinn_board.csv board sweep exists only from 2026-08-21):")
for lab, sel in (("<= 2026-08-20 (bets_log pinn only, engine-selected players)", lambda r: r["date"] <= "20260820"),
                 (">= 2026-08-21 (real Pinnacle board sweep)", lambda r: r["date"] >= "20260821")):
    v = [r for r in B1 if sel(r)]
    if not v: continue
    lo, hi = boot_ci_by_game([(r["gt"], (r["over"] if r["gap"] > 0 else r["under"]),
        ((r["actual"] > r["line"]) if r["gap"] > 0 else (r["actual"] < r["line"])) if r["actual"] != r["line"] else None) for r in v], 3000, 8)
    P("     %-58s n=%-4d games=%-3d ROI %+6.1f%% CI[%+.0f%%,%+.0f%%]" % (
        lab, len(v), len(set(r["gt"] for r in v)), 100*roi(v), 100*lo, 100*hi))
P("  direction split:")
for lab, sel in (("toward Pinnacle = OVER", lambda r: r["gap"] > 0), ("toward Pinnacle = UNDER", lambda r: r["gap"] < 0)):
    v = [r for r in B1 if sel(r)]
    lo, hi = boot_ci_by_game([(r["gt"], (r["over"] if r["gap"] > 0 else r["under"]),
        ((r["actual"] > r["line"]) if r["gap"] > 0 else (r["actual"] < r["line"])) if r["actual"] != r["line"] else None) for r in v], 3000, 9)
    P("     %-24s n=%-4d ROI %+6.1f%%  hit %.1f%%  CI[%+.0f%%,%+.0f%%]" % (lab, len(v), 100*roi(v), wr(v), 100*lo, 100*hi))
P("     the project's claim was '+13.6%% over / +12.4%% under, both directions pay about the same'.")
P("  by market group (a gap of 1 point means very different things at line 4.5 and line 24.5):")
for mkg, ms in (("pts", ("pts",)), ("combos pra/pr/pa/ra", ("pra", "pr", "pa", "ra")), ("reb/ast", ("reb", "ast"))):
    v = [r for r in B1 if r["mk"] in ms]
    if len(v) < 10:
        P("     %-20s n=%-4d ROI %+6.1f%%  (thin)" % (mkg, len(v), 100*roi(v))); continue
    P("     %-20s n=%-4d ROI %+6.1f%%  hit %.1f%%" % (mkg, len(v), 100*roi(v), wr(v)))
P("  gap normalised by line size (|gap|/line >= 5%%), the scale-free version:")
v = [r for r in S if abs(r["gap"])/max(r["line"], 1) >= 0.05]
P("     n=%-4d ROI %+6.1f%%  hit %.1f%%" % (len(v), 100*roi(v), wr(v)))
P("  overlap with Model S: of the %d |gap|>=1 bets, %d are on a player-market the signal fired on tonight" % (
    len(B1), sum(1 for r in B1 if any(s in SIGS for s in r["srcs"]))))
v = [r for r in B1 if not any(s in SIGS for s in r["srcs"])]
P("     with those removed: n=%-4d ROI %+6.1f%%  hit %.1f%%" % (len(v), 100*roi(v), wr(v)))

P("")
P("  C2 NOISE CEILING. Declared grid: 4 gap thresholds x 3 sharp-read horizons x 3 direction")
P("  rules x 4 market groups = 144 cells, min n = 40. Null = reshuffle the gap inside player")
P("  blocks (the label lives on the player's quote), 3000 draws.")
THR = (0.5, 1.0, 1.5, 2.0); DIRS = ("toward", "over only", "under only")
MKG = (("all", ("pts","pra","pr","pa","reb","ast","ra")), ("pts", ("pts",)),
       ("combos", ("pra","pr","pa","ra")), ("reb/ast", ("reb","ast")))
HOR = (("6h", "sharp"), ("12h", "sharp12"))
cells = []
for th in THR:
    for hn, hk in HOR:
        for dn in DIRS:
            for mn, ms in MKG:
                cells.append((th, hk, dn, ms))
def cell_roi(c, gapmap):
    th, hk, dn, ms = c
    tot = 0.0; n = 0
    for r in R:
        if r[hk] is None or r["mk"] not in ms: continue
        g = gapmap.get(id(r), {}).get(hk)
        if g is None or abs(g) < th: continue
        side = "over" if g > 0 else "under"
        if dn == "over only" and side != "over": continue
        if dn == "under only" and side != "under": continue
        n += 1
        if r["actual"] == r["line"]: continue
        w = (r["actual"] > r["line"]) if side == "over" else (r["actual"] < r["line"])
        tot += ((r["over"] if side == "over" else r["under"])-1) if w else -1.0
    return (tot/n if n >= 40 else -9.0), n
real_map = {id(r): {"sharp": (None if r["sharp"] is None else r["sharp"]-r["line"]),
                    "sharp12": (None if r["sharp12"] is None else r["sharp12"]-r["line"])} for r in R}
real_vals = [cell_roi(c, real_map)[0] for c in cells]
bestreal = max(real_vals)
P("     best REAL cell: %+.1f%%  (%s)" % (100*bestreal, str(cells[int(np.argmax(real_vals))])))
byp = collections.defaultdict(list)
for r in R: byp[r["pl"]].append(r)
rr = random.Random(123); sims = []
for _ in range(600):
    m = {}
    for pl, v in byp.items():
        for hk in ("sharp", "sharp12"):
            gs = [real_map[id(x)][hk] for x in v]
            rr.shuffle(gs)
            for x, g in zip(v, gs): m.setdefault(id(x), {})[hk] = g
    sims.append(max(cell_roi(c, m)[0] for c in cells))
sims.sort()
P("     null best-of-grid: median %+.1f%%  p95 %+.1f%%  max %+.1f%%  -> C2 %s the ceiling" % (
    100*sims[len(sims)//2], 100*sims[int(.95*len(sims))], 100*sims[-1],
    "CLEARS" if bestreal >= sims[int(.95*len(sims))] else "does NOT clear"))
b1 = cell_roi((1.0, "sharp", "toward", MKG[0][1]), real_map)
P("     the LIVE cell (|gap|>=1, 6h, toward, all markets) = %+.1f%% n=%d, versus p95 %+.1f%%" % (
    100*b1[0], b1[1], 100*sims[int(.95*len(sims))]))
open(os.path.join(D, "outputs", "t4_follow.txt"), "w", encoding="utf-8").write("\n".join(LOG))
