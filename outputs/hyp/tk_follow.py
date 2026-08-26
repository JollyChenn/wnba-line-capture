# Follow-up MECHANISM checks for both tracks (no new ROI cells - regression / calibration only).
import os, sys, math, statistics, collections, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
from tk_lib import load_games, annotate, devig2
random.seed(20260826)

G = annotate(load_games())

def ols(X, y):
    k = len(X[0]); n = len(y)
    XtX = [[sum(X[i][a] * X[i][b] for i in range(n)) for b in range(k)] for a in range(k)]
    Xty = [sum(X[i][a] * y[i] for i in range(n)) for a in range(k)]
    A = [row[:] + [1.0 if i == j else 0.0 for j in range(k)] for i, row in enumerate(XtX)]
    for c in range(k):
        p = max(range(c, k), key=lambda r: abs(A[r][c])); A[c], A[p] = A[p], A[c]
        pv = A[c][c]; A[c] = [v / pv for v in A[c]]
        for r in range(k):
            if r != c and A[r][c]:
                f = A[r][c]; A[r] = [a - f * b for a, b in zip(A[r], A[c])]
    inv = [row[k:] for row in A]
    beta = [sum(inv[a][b] * Xty[b] for b in range(k)) for a in range(k)]
    resid = [y[i] - sum(X[i][a] * beta[a] for a in range(k)) for i in range(n)]
    s2 = sum(r * r for r in resid) / (n - k)
    return beta, [math.sqrt(s2 * inv[a][a]) for a in range(k)], n

print("=== A-FOLLOWUP: closing-line CALIBRATION SLOPE by week bucket ===")
print("  margin ~ a + b*(-spread);  b far from 1.0 = the line is soft/steep in that window")
def wkb(g):
    w = g["wk"]
    return "wk1-3" if w <= 3 else "wk4-6" if w <= 6 else "wk7-10" if w <= 10 else "wk11-14" if w <= 14 else "wk15+"
for bkt in ["wk1-3", "wk4-6", "wk7-10", "wk11-14", "wk15+", "ALL"]:
    S = [g for g in G if g["spread"] is not None and (bkt == "ALL" or wkb(g) == bkt)]
    b, se, n = ols([[1.0, -g["spread"]] for g in S], [g["margin"] for g in S])
    print("  %-8s n=%4d  intercept=%+6.3f (se %.3f)   slope=%+6.4f (se %.4f)  t(slope-1)=%+5.2f"
          % (bkt, n, b[0], se[0], b[1], se[1], (b[1] - 1) / se[1]))

print("")
print("  same for the TOTAL:  game_total ~ a + b*total")
for bkt in ["wk1-3", "wk4-6", "wk7-10", "wk11-14", "wk15+", "ALL"]:
    S = [g for g in G if g["total"] is not None and (bkt == "ALL" or wkb(g) == bkt)]
    b, se, n = ols([[1.0, g["total"]] for g in S], [g["gtot"] for g in S])
    print("  %-8s n=%4d  intercept=%+7.2f (se %.2f)   slope=%+6.4f (se %.4f)  t(slope-1)=%+5.2f"
          % (bkt, n, b[0], se[0], b[1], se[1], (b[1] - 1) / se[1]))

print("")
print("  ML calibration (devigged home prob) by week bucket: mean p vs realised home win rate")
for bkt in ["wk1-3", "wk4-6", "wk7-10", "wk11-14", "wk15+", "ALL"]:
    S = [g for g in G if g["ml_h"] and g["ml_a"] and (bkt == "ALL" or wkb(g) == bkt)]
    p = [devig2(g["ml_h"], g["ml_a"]) for g in S]
    y = [1.0 if g["margin"] > 0 else 0.0 for g in S]
    d = [yy - pp for yy, pp in zip(y, p)]
    se = statistics.pstdev(d) / math.sqrt(len(d))
    print("  %-8s n=%4d  mean p=%.4f  realised=%.4f  diff=%+.4f (t=%+5.2f)"
          % (bkt, n if False else len(S), statistics.mean(p), statistics.mean(y), statistics.mean(d), statistics.mean(d) / se))

# ---------------- B follow-ups ----------------
hist = collections.defaultdict(list)
for g in G:
    for side, t in (("h", g["home"]), ("a", g["away"])):
        h = hist[(g["season"], t)]
        g["hist_" + side] = list(h)
    d = g["margin"]
    hist[(g["season"], g["home"])].append(d)
    hist[(g["season"], g["away"])].append(-d)

def div(h, w, minprior):
    if len(h) < minprior: return None
    return statistics.mean(h[-w:]) - statistics.mean(h)

print("")
print("=== B-FOLLOWUP: divergence coefficient across window / eligibility choices ===")
print("  model: margin ~ 1 + (-spread) + (div_home - div_away).  Claim needs coef > 0 and t > 2.")
print("  %-30s %6s %10s %8s %8s" % ("spec", "n", "coef", "se", "t"))
for w, mp, lab in [(10, 15, "roll10 vs STD, >=15 prior"),
                   (10, 20, "roll10 vs STD, >=20 prior"),
                   (5, 12, "roll5  vs STD, >=12 prior"),
                   (5, 20, "roll5  vs STD, >=20 prior"),
                   (15, 22, "roll15 vs STD, >=22 prior"),
                   (10, 25, "roll10 vs STD, >=25 prior (deep 2nd half)")]:
    S = []
    for g in G:
        if g["spread"] is None: continue
        dh = div(g["hist_h"], w, mp); da = div(g["hist_a"], w, mp)
        if dh is None or da is None: continue
        S.append((g, dh - da))
    if len(S) < 80: continue
    b, se, n = ols([[1.0, -g["spread"], x] for g, x in S], [g["margin"] for g, x in S])
    print("  %-30s %6d %+10.4f %8.4f %+8.2f" % (lab, n, b[2], se[2], b[2] / se[2]))

print("")
print("  strict brief version: bad-early / good-late only (season-to-date diff < 0 AND roll10 > 0)")
S = []
for g in G:
    if g["spread"] is None: continue
    for side in ("h", "a"):
        h = g["hist_" + side]
        if len(h) < 15: continue
        r10 = statistics.mean(h[-10:]); std = statistics.mean(h)
        if std < 0 and r10 > 0:
            sgn = 1 if side == "h" else -1
            S.append(sgn * (g["margin"] + g["spread"]))
if S:
    se = statistics.pstdev(S) / math.sqrt(len(S))
    print("  n=%d team-nights   mean cover margin=%+.3f pts  t=%+.2f  (>0 = the market underrates them)"
          % (len(S), statistics.mean(S), statistics.mean(S) / se))
T = []
for g in G:
    if g["spread"] is None: continue
    for side in ("h", "a"):
        h = g["hist_" + side]
        if len(h) < 15: continue
        r10 = statistics.mean(h[-10:]); std = statistics.mean(h)
        if std > 0 and r10 < 0:
            sgn = 1 if side == "h" else -1
            T.append(sgn * (g["margin"] + g["spread"]))
if T:
    se = statistics.pstdev(T) / math.sqrt(len(T))
    print("  good-early/bad-late mirror: n=%d  mean cover margin=%+.3f pts  t=%+.2f" % (len(T), statistics.mean(T), statistics.mean(T) / se))

print("")
print("=== A3-FOLLOWUP: turnover FADE direction (the mirror the A3 grid did not declare) ===")
print("  reported for completeness only - see script tkA_turnover.py for the primary grid.")
