# PART B - SECOND-HALF RECENCY BLIND SPOT
#   divergence = rolling-10-game point differential  -  season-to-date point differential
#   (both strictly walk-forward: only games already played by that team this season)
import os, sys, math, statistics, collections, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
from tk_lib import load_games, annotate, block_boot
random.seed(20260826)

G = annotate(load_games())

hist = collections.defaultdict(list)     # (season,team) -> point differentials in order
MINPRIOR = 15
for g in G:
    for side, t in (("h", g["home"]), ("a", g["away"])):
        h = hist[(g["season"], t)]
        g["n_" + side] = len(h)
        if len(h) >= MINPRIOR:
            r10 = statistics.mean(h[-10:])
            std = statistics.mean(h)
            g["div_" + side] = r10 - std
            g["r10_" + side] = r10
            g["std_" + side] = std
        else:
            g["div_" + side] = None
    d = g["margin"]
    hist[(g["season"], g["home"])].append(d)
    hist[(g["season"], g["away"])].append(-d)

ELIG = [g for g in G if g["div_h"] is not None and g["div_a"] is not None and g["spread"] is not None]
print("eligible games (both teams >= %d prior games this season): %d of %d" % (MINPRIOR, len(ELIG), len(G)))
dd = [g["div_h"] - g["div_a"] for g in ELIG]
print("divergence-diff (home-away): sd=%.2f  p10=%.2f p50=%.2f p90=%.2f" % (
    statistics.pstdev(dd), sorted(dd)[len(dd)//10], statistics.median(dd), sorted(dd)[9*len(dd)//10]))
alld = [g["div_h"] for g in ELIG] + [g["div_a"] for g in ELIG]
print("team divergence: sd=%.2f  p20=%.2f p80=%.2f" % (
    statistics.pstdev(alld), sorted(alld)[len(alld)//5], sorted(alld)[4*len(alld)//5]))


def ols(X, y):
    k = len(X[0]); n = len(y)
    XtX = [[sum(X[i][a] * X[i][b] for i in range(n)) for b in range(k)] for a in range(k)]
    Xty = [sum(X[i][a] * y[i] for i in range(n)) for a in range(k)]
    A = [row[:] + [1.0 if i == j else 0.0 for j in range(k)] for i, row in enumerate(XtX)]
    for c in range(k):
        p = max(range(c, k), key=lambda r: abs(A[r][c])); A[c], A[p] = A[p], A[c]
        pv = A[c][c]
        A[c] = [v / pv for v in A[c]]
        for r in range(k):
            if r != c and A[r][c]:
                f = A[r][c]; A[r] = [a - f * b for a, b in zip(A[r], A[c])]
    inv = [row[k:] for row in A]
    beta = [sum(inv[a][b] * Xty[b] for b in range(k)) for a in range(k)]
    resid = [y[i] - sum(X[i][a] * beta[a] for a in range(k)) for i in range(n)]
    s2 = sum(r * r for r in resid) / (n - k)
    se = [math.sqrt(s2 * inv[a][a]) for a in range(k)]
    return beta, se, n

print("")
print("=== MECHANISM B: does divergence predict next-game margin beyond the closing spread? ===")
X = [[1.0, -g["spread"], g["div_h"] - g["div_a"]] for g in ELIG]
y = [g["margin"] for g in ELIG]
b, se, n = ols(X, y)
for i, na in enumerate(["const", "line (-spread)", "divergence diff"]):
    print("  %-18s coef=%+8.4f  se=%.4f  t=%+6.2f" % (na, b[i], se[i], b[i] / se[i]))
print("  n=%d" % n)

print("")
print("  same regression with raw components (line, roll10 diff, season-to-date diff):")
X2 = [[1.0, -g["spread"], g["r10_h"] - g["r10_a"], g["std_h"] - g["std_a"]] for g in ELIG]
b2, se2, _ = ols(X2, y)
for i, na in enumerate(["const", "line (-spread)", "roll10 diff", "season-to-date diff"]):
    print("  %-22s coef=%+8.4f  se=%.4f  t=%+6.2f" % (na, b2[i], se2[i], b2[i] / se2[i]))

print("")
print("  spread RESIDUAL regression: (margin + spread) ~ 1 + divergence diff")
X3 = [[1.0, g["div_h"] - g["div_a"]] for g in ELIG]
y3 = [g["margin"] + g["spread"] for g in ELIG]
b3, se3, _ = ols(X3, y3)
for i, na in enumerate(["const", "divergence diff"]):
    print("  %-18s coef=%+8.4f  se=%.4f  t=%+6.2f" % (na, b3[i], se3[i], b3[i] / se3[i]))

print("")
print("  is divergence already IN the line?  (-spread) ~ 1 + divergence diff")
b4, se4, _ = ols(X3, [-g["spread"] for g in ELIG])
for i, na in enumerate(["const", "divergence diff"]):
    print("  %-18s coef=%+8.4f  se=%.4f  t=%+6.2f" % (na, b4[i], se4[i], b4[i] / se4[i]))

MINN = 60
print("")
print("DECLARED GRID B: B1 = 5 team-divergence quintiles x 4 bets (back/fade x ML/SP) = 20 cells;")
print("                 B2 = 5 game divergence-diff quintiles x 2 bets = 10 cells.  30 total, min n = %d" % MINN)

qs = sorted(alld); CUT = [qs[int(k * len(qs) / 5)] for k in (1, 2, 3, 4)]
def qb(x):
    for i, c in enumerate(CUT):
        if x < c: return "Q%d" % (i + 1)
    return "Q5"
qd = sorted(dd); CUTD = [qd[int(k * len(qd) / 5)] for k in (1, 2, 3, 4)]
def qbd(x):
    for i, c in enumerate(CUTD):
        if x < c: return "D%d" % (i + 1)
    return "D5"
QORD = ["Q1", "Q2", "Q3", "Q4", "Q5"]; DORD = ["D1", "D2", "D3", "D4", "D5"]
print("  team-divergence quintile cuts: %s" % ["%.2f" % c for c in CUT])
print("  game divdiff quintile cuts   : %s" % ["%.2f" % c for c in CUTD])


def build(getdiv):
    cells = collections.defaultdict(list)
    for g in ELIG:
        dh, da, ddg = getdiv(g)
        for side, dv in (("h", dh), ("a", da)):
            b = qb(dv)
            if g["ml_h"] and g["ml_a"]:
                wo = (1.0 if g["margin"] > 0 else 0.0) if side == "h" else (1.0 if g["margin"] < 0 else 0.0)
                cells[(b, "ML_back")].append(((g["ml_h"] if side == "h" else g["ml_a"]) - 1.0) if wo else -1.0)
                cells[(b, "ML_fade")].append(((g["ml_a"] if side == "h" else g["ml_h"]) - 1.0) if not wo else -1.0)
            if g["sp_h"] and g["sp_a"]:
                d = (g["margin"] + g["spread"]) * (1 if side == "h" else -1)
                if d != 0:
                    cells[(b, "SP_back")].append(((g["sp_h"] if side == "h" else g["sp_a"]) - 1.0) if d > 0 else -1.0)
                    cells[(b, "SP_fade")].append(((g["sp_a"] if side == "h" else g["sp_h"]) - 1.0) if d < 0 else -1.0)
        bd = qbd(ddg)
        if g["ml_h"] and g["ml_a"]:
            cells[(bd, "ML_home")].append((g["ml_h"] - 1.0) if g["margin"] > 0 else -1.0)
        if g["sp_h"] and g["sp_a"]:
            d = g["margin"] + g["spread"]
            if d != 0:
                cells[(bd, "SP_home")].append((g["sp_h"] - 1.0) if d > 0 else -1.0)
    return cells

real = build(lambda g: (g["div_h"], g["div_a"], g["div_h"] - g["div_a"]))

by_s = collections.defaultdict(list)
for g in ELIG: by_s[g["season"]].append(g)
rnd = random.Random(777)
bests = []
for _ in range(1000):
    pm = {}
    for s, gs in by_s.items():
        labs = [(x["div_h"], x["div_a"]) for x in gs]; rnd.shuffle(labs)
        for x, l in zip(gs, labs): pm[x["gid"]] = l
    c = build(lambda g: (pm[g["gid"]][0], pm[g["gid"]][1], pm[g["gid"]][0] - pm[g["gid"]][1]))
    bests.append(max((sum(v) / len(v) for v in c.values() if len(v) >= MINN), default=-9))
bests.sort()
CEIL = bests[int(0.95 * len(bests))]
print("")
print("NOISE CEILING (1000 game-level permutations, best of 30 cells): p95 = %+.2f%%   median = %+.2f%%" % (
    CEIL * 100, statistics.median(bests) * 100))
print("")


def show(order, bets, title):
    print("=== " + title + " ===")
    print("%-4s " % "q" + " ".join("%20s" % b for b in bets))
    for b in order:
        line = "%-4s " % b
        for bt in bets:
            v = real.get((b, bt), [])
            line += (" %+7.2f%% n=%-4d" % (sum(v) / len(v) * 100, len(v))) if v else "%20s" % "--"
        print(line)
    print("")

show(QORD, ["ML_back", "ML_fade", "SP_back", "SP_fade"],
     "B1  by TEAM divergence quintile (Q1 = coldest recent form vs own season, Q5 = hottest)")
show(DORD, ["ML_home", "SP_home"],
     "B2  by GAME divergence-diff quintile (D5 = home team hottest relative to its own season)")

best = max(((sum(v) / len(v), k, len(v)) for k, v in real.items() if len(v) >= MINN))
print("BEST CELL: %s ROI=%+.2f%% n=%d  vs ceiling %+.2f%% -> %s" % (
    best[1], best[0] * 100, best[2], CEIL * 100, "CLEARS" if best[0] > CEIL else "UNDER CEILING (noise)"))
lo, hi = block_boot([[x] for x in real[best[1]]], iters=4000)
print("  game-level block-bootstrap CI on that cell: [%+.2f%%, %+.2f%%]" % (lo * 100, hi * 100))

print("")
print("=== per-season walk-forward: best cell + the headline claims ===")
def cellrows(qkey, bt):
    per = collections.defaultdict(list)
    for g in ELIG:
        for side, dv in (("h", g["div_h"]), ("a", g["div_a"])):
            if (qb(dv) if qkey[0] == "Q" else qbd(g["div_h"] - g["div_a"])) != qkey:
                continue
            if bt.startswith("ML"):
                if not (g["ml_h"] and g["ml_a"]): continue
                wo = (1.0 if g["margin"] > 0 else 0.0) if side == "h" else (1.0 if g["margin"] < 0 else 0.0)
                if bt.endswith("back"):
                    per[g["season"]].append(((g["ml_h"] if side == "h" else g["ml_a"]) - 1.0) if wo else -1.0)
                else:
                    per[g["season"]].append(((g["ml_a"] if side == "h" else g["ml_h"]) - 1.0) if not wo else -1.0)
            else:
                if not (g["sp_h"] and g["sp_a"]): continue
                d = (g["margin"] + g["spread"]) * (1 if side == "h" else -1)
                if d == 0: continue
                if bt.endswith("back"):
                    per[g["season"]].append(((g["sp_h"] if side == "h" else g["sp_a"]) - 1.0) if d > 0 else -1.0)
                else:
                    per[g["season"]].append(((g["sp_a"] if side == "h" else g["sp_h"]) - 1.0) if d < 0 else -1.0)
        if bt in ("ML_home", "SP_home"):
            break
    return per

for key in [best[1], ("Q5", "ML_back"), ("Q5", "SP_back"), ("Q1", "ML_fade"), ("Q1", "SP_fade")]:
    if key[1] in ("ML_home", "SP_home"):
        per = collections.defaultdict(list)
        for g in ELIG:
            if qbd(g["div_h"] - g["div_a"]) != key[0]: continue
            if key[1] == "ML_home" and g["ml_h"]:
                per[g["season"]].append((g["ml_h"] - 1.0) if g["margin"] > 0 else -1.0)
            if key[1] == "SP_home" and g["sp_h"]:
                d = g["margin"] + g["spread"]
                if d != 0: per[g["season"]].append((g["sp_h"] - 1.0) if d > 0 else -1.0)
    else:
        per = cellrows(key[0], key[1])
    if not per: continue
    print("  %s: %s" % (str(key), "  ".join(
        "%d:%+.1f%%(n=%d)" % (s, sum(v) / len(v) * 100, len(v)) for s, v in sorted(per.items()))))
