# Q4b, part 2. Cleanly decompose the book's next-line move into an H1 pull and an H2 pull.
# If the book over-weights first-half scoring, an H1-heavy big game leaves an over-raised line
# and the UNDER is the bet. Tested with a declared noise ceiling.
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
    mg = trail(pl, gt)
    nl, noo, nuo = P1[(pl, n1)]
    if mg is None or nrow["pts"] == nl: continue
    h = H1[(pl, gt)]
    pairs.append(dict(pl=pl, gt=gt, n1=n1, line=ln, nline=nl, mv=nl-ln, h1=h["h1"], h2=h["h2"],
                      pts=nowr["pts"], med=mg, resid_g=nowr["pts"]-mg,
                      h1r=h["h1"]-mg/2.0, h2r=h["h2"]-mg/2.0,
                      share=(h["h1"]/h["pts"] if h["pts"] else 0.5),
                      npts=nrow["pts"], nresid=nrow["pts"]-mg, over_won=nrow["pts"] > nl,
                      noo=noo, nuo=nuo, ev=h["h1"] > ln))
N = len(pairs)
print("pairs n=%d  players=%d  G+1 games=%d" % (N, len(set(p["pl"] for p in pairs)),
                                                len(set(p["n1"] for p in pairs))))

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

def corr(a, b):
    ma = statistics.mean(a); mb = statistics.mean(b)
    return sum((x-ma)*(y-mb) for x, y in zip(a, b))/math.sqrt(
        sum((x-ma)**2 for x in a)*sum((y-mb)**2 for y in b))

print("")
print("--- A. WHAT DOES THE BOOK'S NEXT LINE RESPOND TO? ---")
print("  corr(h1r, h2r) = %+.3f   (the two halves are near-orthogonal, so the split is readable)" %
      corr([p["h1r"] for p in pairs], [p["h2r"] for p in pairs]))
y = [p["mv"] for p in pairs]
X = [(1.0, p["h1r"], p["h2r"]) for p in pairs]
b = ols(X, y)
print("  line_move ~ a + b1*h1_resid + b2*h2_resid :  a %+.3f  b1 %+.4f  b2 %+.4f  (b1-b2 %+.4f)" %
      (b[0], b[1], b[2], b[1]-b[2]))
# player-block permutation on the DIFFERENCE b1-b2: swap each row's two halves at random
byp = collections.defaultdict(list)
for i, p in enumerate(pairs): byp[p["pl"]].append(i)
obs = b[1]-b[2]; cnt = 0; B = 4000
for _ in range(B):
    X2 = []
    for p in pairs:
        if random.random() < 0.5: X2.append((1.0, p["h1r"], p["h2r"]))
        else: X2.append((1.0, p["h2r"], p["h1r"]))
    try:
        bb = ols(X2, y)
        if abs(bb[1]-bb[2]) >= abs(obs): cnt += 1
    except ZeroDivisionError: pass
print("  half-swap permutation p on (b1-b2) = %.4f" % ((cnt+1)/(B+1)))

print("")
print("--- B. WHAT DOES HER NEXT-GAME PRODUCTION RESPOND TO? ---")
y2 = [p["nresid"] for p in pairs]
b2 = ols(X, y2)
print("  next_resid ~ a + b1*h1_resid + b2*h2_resid :  a %+.3f  b1 %+.4f  b2 %+.4f  (b1-b2 %+.4f)" %
      (b2[0], b2[1], b2[2], b2[1]-b2[2]))
cnt = 0
for _ in range(B):
    X2 = []
    for p in pairs:
        if random.random() < 0.5: X2.append((1.0, p["h1r"], p["h2r"]))
        else: X2.append((1.0, p["h2r"], p["h1r"]))
    try:
        bb = ols(X2, y2)
        if abs(bb[1]-bb[2]) >= abs(b2[1]-b2[2]): cnt += 1
    except ZeroDivisionError: pass
print("  half-swap permutation p on (b1-b2) = %.4f" % ((cnt+1)/(B+1)))
print("")
print("  BOOK-vs-TRUTH per half:  book pays %+.4f pt of line per H1 pt, truth repays %+.4f" % (b[1], b2[1]))
print("                           book pays %+.4f pt of line per H2 pt, truth repays %+.4f" % (b[2], b2[2]))
print("  -> a positive (book - truth) gap on H1 relative to H2 is the tradable overreaction:")
print("     H1 gap %+.4f   H2 gap %+.4f   differential %+.4f" %
      (b[1]-b2[1], b[2]-b2[2], (b[1]-b2[1])-(b[2]-b2[2])))

# --------- C. the ROI grid, with a ceiling declared first ----------------------------
print("")
print("--- C. ROI GRID with the noise ceiling declared BEFORE the table ---")
GRID = []
for nm, fn in [("h1share>=.60 & big", lambda p: p["share"] >= .60 and p["resid_g"] >= 3),
               ("h1share>=.70 & big", lambda p: p["share"] >= .70 and p["resid_g"] >= 3),
               ("h1 cleared line",    lambda p: p["ev"]),
               ("h1r>=4",             lambda p: p["h1r"] >= 4),
               ("h1r>=6",             lambda p: p["h1r"] >= 6),
               ("h1r>=4 & raised",    lambda p: p["h1r"] >= 4 and p["mv"] > 0)]:
    GRID.append((nm, fn))
def roi(sel, sd):
    if not sel: return 0.0
    return sum(((p["noo"]-1) if p["over_won"] else -1) if sd == "Over"
               else ((p["nuo"]-1) if not p["over_won"] else -1) for p in sel)/len(sel)
flags = {nm: [fn(p) for p in pairs] for nm, fn in GRID}
def gridbest(fl):
    bst = 0.0
    for nm, _ in GRID:
        sel = [pairs[i] for i in range(N) if fl[nm][i]]
        if len(sel) < 20: continue
        for sd in ("Over", "Under"):
            v = roi(sel, sd)
            if abs(v) > abs(bst): bst = v
    return bst
null = []
for _ in range(1500):
    fl = {}
    for nm, _ in GRID:
        col = list(flags[nm])
        for p_, ii in byp.items():
            v = [col[i] for i in ii]; random.shuffle(v)
            for i, x in zip(ii, v): col[i] = x
        fl[nm] = col
    null.append(abs(gridbest(fl)))
null.sort()
CEIL = null[int(.95*len(null))]
print("  GRID = 6 filters x 2 sides, min n=20.  Player-block permutation, 1500 draws.")
print("  p95 of best |ROI| under the null = %+.2f%%   (median %+.2f%%)" % (100*CEIL, 100*null[len(null)//2]))
print("")
print("  %-22s %5s %6s %9s %9s %s" % ("filter", "n", "plyrs", "Over", "Under", "verdict"))
for nm, fn in GRID:
    sel = [p for p in pairs if fn(p)]
    if len(sel) < 20:
        print("  %-22s %5d  (below min n)" % (nm, len(sel))); continue
    ro, ru = roi(sel, "Over"), roi(sel, "Under")
    bb = max(abs(ro), abs(ru))
    print("  %-22s %5d %6d %+8.2f%% %+8.2f%%  %s" % (nm, len(sel), len(set(p["pl"] for p in sel)),
          100*ro, 100*ru, "CLEARS CEILING" if bb > CEIL else "under ceiling"))
