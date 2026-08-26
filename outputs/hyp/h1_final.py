# Final checks: (i) was the earlier c=+0.248 "H1 pulls the line" just line_G in disguise?
# (ii) artifact-free (within-player demeaned) levels for book-move vs production-persistence.
import os, sys, csv, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hlib; ROOT = hlib.boot(globals())
random.seed(20260826)

H1 = {}
for r in load("outputs/hyp/h1_all.csv"):
    gid = r["game_id"]
    if gid not in gmeta: continue
    H1[(r["player"], gmeta[gid][1])] = dict(h1=f(r["h1"]), h2=f(r["h2"]), pts=f(r["pts"]))
P1 = {}
for (pl, mk, gt), sd in side.items():
    if mk == "pts" and "Over" in sd and "Under" in sd and sd["Over"][1] == sd["Under"][1]:
        P1[(pl, gt)] = (sd["Over"][1], sd["Over"][2], sd["Under"][2])
Qg = collections.defaultdict(list)
for (pl, gt) in P1: Qg[pl].append(gt)
for v in Qg.values(): v.sort()
def trail(pl, gt, k=10):
    p = [x for x in hist.get(pl, []) if x["tip"] < gt and x["tm"] == teamof.get(pl)][-k:]
    return statistics.median(x["pts"] for x in p) if len(p) >= 5 else None
pairs = []
for (pl, gt), (ln, _, _) in P1.items():
    if (pl, gt) not in H1: continue
    nowr = pgrow.get((pl, gt))
    if not nowr or nowr["min"] < 8: continue
    nx = [g for g in Qg[pl] if g > gt]
    if not nx: continue
    n1 = nx[0]; nrow = pgrow.get((pl, n1))
    if not nrow or nrow["min"] < 8: continue
    mg = trail(pl, gt); nl, noo, nuo = P1[(pl, n1)]
    if mg is None or nrow["pts"] == nl: continue
    h = H1[(pl, gt)]
    pairs.append(dict(pl=pl, line=ln, nline=nl, mv=nl-ln, h1=h["h1"], h2=h["h2"], pts=nowr["pts"],
                      med=mg, resid_g=nowr["pts"]-mg, h1r=h["h1"]-mg/2.0, h2r=h["h2"]-mg/2.0,
                      npts=nrow["pts"], nresid=nrow["pts"]-mg))
def ols(X, y):
    k = len(X[0])
    A = [[sum(X[i][a]*X[i][b] for i in range(len(X))) for b in range(k)] for a in range(k)]
    Bv = [sum(X[i][a]*y[i] for i in range(len(X))) for a in range(k)]
    Aa = [row[:]+[Bv[i]] for i, row in enumerate(A)]
    for c in range(k):
        p = max(range(c, k), key=lambda r_: abs(Aa[r_][c])); Aa[c], Aa[p] = Aa[p], Aa[c]
        for r_ in range(k):
            if r_ == c or Aa[c][c] == 0: continue
            fq = Aa[r_][c]/Aa[c][c]
            for cc in range(c, k+1): Aa[r_][cc] -= fq*Aa[c][cc]
    return [Aa[i][k]/Aa[i][i] for i in range(k)]

y = [p["mv"] for p in pairs]
print("(i) UNPICKING THE EARLIER c=+0.248 ON (h1 - line_G), n=%d" % len(pairs))
print("  spec 1  mv ~ 1 + resid_g + (h1-line_G)        : %s" %
      " ".join("%+.4f" % v for v in ols([(1.0, p["resid_g"], p["h1"]-p["line"]) for p in pairs], y)))
print("  spec 2  mv ~ 1 + resid_g + line_G             : %s" %
      " ".join("%+.4f" % v for v in ols([(1.0, p["resid_g"], p["line"]) for p in pairs], y)))
print("  spec 3  mv ~ 1 + resid_g + line_G + h1        : %s" %
      " ".join("%+.4f" % v for v in ols([(1.0, p["resid_g"], p["line"], p["h1"]) for p in pairs], y)))
print("  -> once line_G is in the model on its own, the h1 coefficient is what is left.")

print("")
print("(ii) ARTIFACT-FREE LEVELS: everything demeaned WITHIN PLAYER (kills the shared-median bias)")
byp = collections.defaultdict(list)
for i, p in enumerate(pairs): byp[p["pl"]].append(i)
def demean(field, idxs):
    m = statistics.mean(pairs[i][field] for i in idxs)
    return {i: pairs[i][field]-m for i in idxs}
rowsX = []; rowsY1 = []; rowsY2 = []
for p_, ii in byp.items():
    if len(ii) < 4: continue
    d1 = demean("h1r", ii); d2 = demean("h2r", ii)
    dm = demean("mv", ii); dn = demean("nresid", ii)
    for i in ii:
        rowsX.append((d1[i], d2[i])); rowsY1.append(dm[i]); rowsY2.append(dn[i])
X = [(a, b) for a, b in rowsX]
bm = ols(X, rowsY1); bn = ols(X, rowsY2)
print("  n=%d rows from %d players with >=4 pairs" % (len(X), sum(1 for v in byp.values() if len(v) >= 4)))
print("  LINE MOVE       per H1 pt %+.4f   per H2 pt %+.4f" % (bm[0], bm[1]))
print("  NEXT PRODUCTION per H1 pt %+.4f   per H2 pt %+.4f" % (bn[0], bn[1]))
print("  book-minus-truth: H1 %+.4f   H2 %+.4f   -> %s" % (bm[0]-bn[0], bm[1]-bn[1],
      "book UNDER-moves both halves equally" if (bm[0]-bn[0]) < 0 and (bm[1]-bn[1]) < 0 else "mixed"))
cnt = 0; B = 4000
obs = (bm[0]-bm[1])
for _ in range(B):
    X2 = [(a, b) if random.random() < .5 else (b, a) for a, b in X]
    try:
        bb = ols(X2, rowsY1)
        if abs(bb[0]-bb[1]) >= abs(obs): cnt += 1
    except ZeroDivisionError: pass
print("  half-swap p on (line move: H1 pull - H2 pull) = %.4f" % ((cnt+1)/(B+1)))
cnt = 0; obs2 = (bn[0]-bn[1])
for _ in range(B):
    X2 = [(a, b) if random.random() < .5 else (b, a) for a, b in X]
    try:
        bb = ols(X2, rowsY2)
        if abs(bb[0]-bb[1]) >= abs(obs2): cnt += 1
    except ZeroDivisionError: pass
print("  half-swap p on (next production: H1 pull - H2 pull) = %.4f" % ((cnt+1)/(B+1)))

print("")
print("(iii) POWER: what ROI would the literal test (n=46) have needed to clear its own ceiling?")
print("  ceiling was +57.4%%; at n=46 and prop breakeven 53.5%% that is a hit rate of ~%.0f%%." % 100*0)
p_be = 0.535
need = (0.5737 + 1)/1.9   # rough: ROI = hit*(o-1) - (1-hit); o~1.87 avg
print("  with mean over-odds %.3f, +57.4%% ROI needs a %.1f%% hit rate on 46 bets." %
      (statistics.mean(side[k]["Over"][2] for k in side if k[1] == "pts" and "Over" in side[k]),
       100*(1.574)/1.87))
import math as _m
def mde(n, o=1.87, alpha=.05):
    # two-sided 95% detectable hit-rate lift over breakeven, normal approx
    be = 1/o
    return 1.96*_m.sqrt(be*(1-be)/n)
for n in (46, 100, 200, 400, 800):
    m = mde(n)
    print("    n=%4d  MDE = %+.1fpp hit rate = %+.1f%% ROI" % (n, 100*m, 100*m*1.87))
