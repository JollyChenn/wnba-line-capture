# PART A - ROI GRID by season timing.  Grid + noise ceiling DECLARED BEFORE results.
import os, sys, math, statistics, collections, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
from tk_lib import load_games, annotate, block_boot

random.seed(20260826)
G = annotate(load_games())

def wkb(g):
    w = g["wk"]
    return "wk1-3" if w<=3 else "wk4-6" if w<=6 else "wk7-10" if w<=10 else "wk11-14" if w<=14 else "wk15+"
WORD = ["wk1-3","wk4-6","wk7-10","wk11-14","wk15+"]
def tgib(i):
    return "g1-5" if i<=5 else "g6-10" if i<=10 else "g11-20" if i<=20 else "g21-34" if i<=34 else "g35+"
TORD = ["g1-5","g6-10","g11-20","g21-34","g35+"]

# ---- bet definitions: (name, needs, resolve->(win01,odds)) ----
def bets_for(g):
    out = []
    if g["ml_h"] and g["ml_a"]:
        out.append(("ML_home", 1.0 if g["margin"]>0 else 0.0, g["ml_h"]))
        out.append(("ML_away", 1.0 if g["margin"]<0 else 0.0, g["ml_a"]))
    if g["spread"] is not None and g["sp_h"] and g["sp_a"]:
        d = g["margin"] + g["spread"]
        out.append(("SP_home", 0.5 if d==0 else (1.0 if d>0 else 0.0), g["sp_h"]))
        out.append(("SP_away", 0.5 if d==0 else (1.0 if d<0 else 0.0), g["sp_a"]))
    if g["total"] is not None and g["ou_o"] and g["ou_u"]:
        d = g["gtot"] - g["total"]
        out.append(("OU_over", 0.5 if d==0 else (1.0 if d>0 else 0.0), g["ou_o"]))
        out.append(("OU_under", 0.5 if d==0 else (1.0 if d<0 else 0.0), g["ou_u"]))
    return out

def net(w, o):
    return None if w == 0.5 else ((o-1.0) if w == 1.0 else -1.0)

# =========== DECLARED GRID ===========
# A1: 5 league-week buckets x 6 directional bets                     = 30 cells
# A2: 5 team-game-index buckets x 4 team-side bets (ML/SP, own side) = 20 cells
# TOTAL DECLARED = 50 cells.  Min n per cell = 60 bets.
MINN = 60
print("DECLARED GRID: A1 = 5 week buckets x 6 bets = 30 cells; A2 = 5 team-game-index buckets x 4 side-bets = 20 cells; 50 total. min n = %d" % MINN)

def build_A1(labfn):
    cells = collections.defaultdict(list)   # (bucket,bet) -> list of net units
    for g in G:
        b = labfn(g)
        for nm, w, o in bets_for(g):
            u = net(w, o)
            if u is not None:
                cells[(b, nm)].append(u)
    return cells

def build_A2(labfn):
    cells = collections.defaultdict(list)
    for g in G:
        bh, ba = labfn(g, "h"), labfn(g, "a")
        for nm, w, o in bets_for(g):
            u = net(w, o)
            if u is None: continue
            if nm in ("ML_home","SP_home"):
                cells[(bh, nm.replace("home","side"))].append(u)
            elif nm in ("ML_away","SP_away"):
                cells[(ba, nm.replace("away","side"))].append(u)
    return cells

def best_roi(cells, minn=MINN):
    best = -9
    for k, v in cells.items():
        if len(v) >= minn:
            r = sum(v)/len(v)
            if r > best: best = r
    return best

# =========== NOISE CEILING (computed BEFORE looking at real cells) ===========
# Permute at the GAME level: shuffle the timing label across games WITHIN season
# (preserves per-season game counts and per-game outcome/odds structure).
def ceiling(iters=1000):
    by_s = collections.defaultdict(list)
    for g in G: by_s[g["season"]].append(g)
    rnd = random.Random(4242)
    bests = []
    for _ in range(iters):
        perm = {}
        permT = {}
        for s, gs in by_s.items():
            wl = [wkb(x) for x in gs]; rnd.shuffle(wl)
            th = [tgib(x["tgi_h"]) for x in gs]; rnd.shuffle(th)
            ta = [tgib(x["tgi_a"]) for x in gs]; rnd.shuffle(ta)
            for i, x in enumerate(gs):
                perm[x["gid"]] = wl[i]; permT[x["gid"]] = (th[i], ta[i])
        c1 = build_A1(lambda g: perm[g["gid"]])
        c2 = build_A2(lambda g, s: permT[g["gid"]][0 if s=="h" else 1])
        bests.append(max(best_roi(c1), best_roi(c2)))
    bests.sort()
    return bests[int(0.95*len(bests))], statistics.median(bests)

CEIL, MED = ceiling(1000)
print(f"NOISE CEILING (1000 game-level permutations, best of 50 cells): p95 = {CEIL*100:+.2f}%   median = {MED*100:+.2f}%")
print("Anything under that ceiling is NOT a finding.\n")

def report(cells, order, title):
    print("=== " + title + " ===")
    bets = sorted(set(k[1] for k in cells))
    print(f"{'bucket':10s} " + " ".join(f"{b:>22s}" for b in bets))
    for b in order:
        line = f"{b:10s} "
        for bt in bets:
            v = cells.get((b, bt), [])
            line += f" {(sum(v)/len(v)*100 if v else 0):+7.2f}% n={len(v):<4d}   " if v else f" {'--':>22s}"
        print(line)
    print()

c1 = build_A1(wkb)
c2 = build_A2(lambda g, s: tgib(g["tgi_h"] if s=="h" else g["tgi_a"]))
report(c1, WORD, "A1  ROI by league-week bucket")
report(c2, TORD, "A2  ROI by team-game-index bucket (bet on the team in that bucket)")

print("=== HEADLINE TEST: weeks 1-3 vs rest, per market side ===")
for bt in ["ML_home","ML_away","SP_home","SP_away","OU_over","OU_under"]:
    e = c1.get(("wk1-3", bt), [])
    r = [x for b in WORD[1:] for x in c1.get((b, bt), [])]
    if not e: continue
    # game-level block bootstrap on the early cell
    lo, hi = block_boot([[x] for x in e], iters=3000)
    print(f"  {bt:9s} wk1-3 ROI={sum(e)/len(e)*100:+6.2f}% n={len(e):3d} CI[{lo*100:+.1f},{hi*100:+.1f}]   rest ROI={sum(r)/len(r)*100:+6.2f}% n={len(r)}")

best1 = max(((sum(v)/len(v), k, len(v)) for k, v in list(c1.items())+list(c2.items()) if len(v) >= MINN))
print(f"\nBEST CELL IN DECLARED GRID: {best1[1]} ROI={best1[0]*100:+.2f}% n={best1[2]}   vs ceiling {CEIL*100:+.2f}%  ->  {'CLEARS' if best1[0] > CEIL else 'UNDER CEILING (noise)'}")
