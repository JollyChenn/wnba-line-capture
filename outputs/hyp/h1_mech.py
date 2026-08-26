# MECHANISM: does clearing-by-halftime in G predict RAW production in G+1, above her own median?
# Runs on the FULL H1 window (5/08-7/15) using box production for G+1 (box runs to 8/25),
# so it is ~6x the sample of the bettable test.  Proxy line = trailing median (current team,>=5).
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
Q = {}
for (pl, mk, gt), sd in side.items():
    if mk != "pts" or "Over" not in sd or "Under" not in sd: continue
    if sd["Over"][1] != sd["Under"][1]: continue
    Q[(pl, gt)] = sd["Over"][1]

def trail(pl, gt, k=10, mk="pts"):
    p = [x for x in hist.get(pl, []) if x["tip"] < gt and x["tm"] == teamof.get(pl)][-k:]
    return statistics.median(x[mk] for x in p) if len(p) >= 5 else None

# --- how good is the median proxy for the real posted line? -------------------------
d = []; agree = 0; tot = 0
for (pl, gt), ln in Q.items():
    m = trail(pl, gt)
    if m is None or (pl, gt) not in H1: continue
    d.append(ln - m); tot += 1
    if (H1[(pl,gt)]["h1"] > ln) == (H1[(pl,gt)]["h1"] > m): agree += 1
print("PROXY CHECK  posted line - trailing median(10, current team): n=%d mean %+.2f  median %+.2f  sd %.2f" %
      (len(d), statistics.mean(d), statistics.median(d), statistics.pstdev(d)))
print("  event agreement (h1>line vs h1>median): %.1f%% of %d" % (100*agree/max(1,tot), tot))

# --- build the mechanism panel ------------------------------------------------------
M = []
for (pl, gt), h in sorted(H1.items(), key=lambda k: (k[0][0], k[0][1])):
    now = pgrow.get((pl, gt))
    if not now or now["min"] < 8: continue
    m_g = trail(pl, gt)
    if m_g is None: continue
    fut = [x for x in hist.get(pl, []) if x["tip"] > gt]
    if not fut: continue
    nx = fut[0]
    if nx["min"] < 8: continue
    line = Q.get((pl, gt))
    ref = line if line is not None else m_g
    M.append(dict(pl=pl, gt=gt, h1=h["h1"], pts=now["pts"], ref=ref, real_line=(line is not None),
                  med_g=m_g, npts=nx["pts"], nmin=nx["min"], gt2=nx["tip"],
                  resid=nx["pts"] - m_g, resid_g=now["pts"] - m_g, h1sh=(h["h1"]/h["pts"] if h["pts"] else None)))
print("\nMECHANISM PANEL n=%d  players=%d  (%d with a real posted line, %d median-proxy)" %
      (len(M), len(set(x["pl"] for x in M)), sum(1 for x in M if x["real_line"]), sum(1 for x in M if not x["real_line"])))

def blockperm_p(sel_fn, val_fn, B=4000):
    """permute the EVENT label inside player blocks; two-sided p on the group mean gap"""
    idx = list(range(len(M)))
    byp = collections.defaultdict(list)
    for i in idx: byp[M[i]["pl"]].append(i)
    lab = [sel_fn(M[i]) for i in idx]
    def gap(l):
        a = [val_fn(M[i]) for i in idx if l[i]]
        b = [val_fn(M[i]) for i in idx if not l[i]]
        if len(a) < 5 or len(b) < 5: return None
        return statistics.mean(a) - statistics.mean(b)
    obs = gap(lab)
    if obs is None: return None, None, 0, 0
    cnt = 0
    for _ in range(B):
        l2 = list(lab)
        for p, ii in byp.items():
            v = [lab[i] for i in ii]; random.shuffle(v)
            for i, x in zip(ii, v): l2[i] = x
        g = gap(l2)
        if g is not None and abs(g) >= abs(obs): cnt += 1
    na = sum(lab); return obs, (cnt+1)/(B+1), na, len(lab)-na

print("\n--- Q2 MECHANISM: next-game pts minus her trailing median ---")
for nm, fn in [("h1 > ref line", lambda r: r["h1"] > r["ref"]),
               ("h1 >= ref+2",   lambda r: r["h1"] >= r["ref"]+2),
               ("(control) full-game pts > ref", lambda r: r["pts"] > r["ref"])]:
    obs, p, na, nb = blockperm_p(fn, lambda r: r["resid"])
    a = [r["resid"] for r in M if fn(r)]; b = [r["resid"] for r in M if not fn(r)]
    print("%-32s  event n=%4d mean resid %+6.2f | non-event n=%4d mean %+6.2f | gap %+6.2f  p=%.4f" %
          (nm, len(a), statistics.mean(a), len(b), statistics.mean(b), obs, p))

print("\n--- Q3 THE CONFOUND: stratify on HER RAW PRODUCTION IN G (pts) ---")
print("Does H1-clearing separate INSIDE a stratum of last-game scoring?")
strata = [(0,9.5),(9.5,14.5),(14.5,19.5),(19.5,99)]
print("%-14s %5s %8s %5s %8s %8s %8s" % ("G pts bucket","nEv","ev resid","nNo","no resid","gap","p(block)"))
for lo, hi in strata:
    sub = [r for r in M if lo <= r["pts"] < hi]
    a = [r["resid"] for r in sub if r["h1"] > r["ref"]]
    b = [r["resid"] for r in sub if not (r["h1"] > r["ref"])]
    if len(a) < 5 or len(b) < 5:
        print("%-14s %5d %8s %5d %8s" % (f"{lo}-{hi}", len(a), "-", len(b), "-")); continue
    # block permutation within this stratum
    byp = collections.defaultdict(list)
    for i, r in enumerate(sub): byp[r["pl"]].append(i)
    lab = [r["h1"] > r["ref"] for r in sub]
    obs = statistics.mean(a) - statistics.mean(b); cnt = 0; B = 3000
    for _ in range(B):
        l2 = list(lab)
        for p_, ii in byp.items():
            v = [lab[i] for i in ii]; random.shuffle(v)
            for i, x in zip(ii, v): l2[i] = x
        aa = [sub[i]["resid"] for i in range(len(sub)) if l2[i]]
        bb = [sub[i]["resid"] for i in range(len(sub)) if not l2[i]]
        if len(aa) >= 5 and len(bb) >= 5 and abs(statistics.mean(aa)-statistics.mean(bb)) >= abs(obs): cnt += 1
    print("%-14s %5d %+8.2f %5d %+8.2f %+8.2f %8.4f" % (f"{lo}-{hi}", len(a), statistics.mean(a), len(b), statistics.mean(b), obs, (cnt+1)/(B+1)))

# residual regression: does h1-clearing add anything on top of pts_G?
print("\n--- Q3b: linear control.  resid(G+1) ~ a + b*(pts_G - med_G) + c*1[h1>ref] ---")
X = [(1.0, r["resid_g"], 1.0 if r["h1"] > r["ref"] else 0.0) for r in M]
y = [r["resid"] for r in M]
def ols(X, y):
    k = len(X[0]); A = [[sum(X[i][a]*X[i][b] for i in range(len(X))) for b in range(k)] for a in range(k)]
    B = [sum(X[i][a]*y[i] for i in range(len(X))) for a in range(k)]
    import copy
    Aa = [row[:]+[B[i]] for i, row in enumerate(A)]
    for c in range(k):
        p = max(range(c, k), key=lambda r_: abs(Aa[r_][c])); Aa[c], Aa[p] = Aa[p], Aa[c]
        for r_ in range(k):
            if r_ == c or Aa[c][c] == 0: continue
            f_ = Aa[r_][c]/Aa[c][c]
            for cc in range(c, k+1): Aa[r_][cc] -= f_*Aa[c][cc]
    return [Aa[i][k]/Aa[i][i] for i in range(k)]
bt = ols(X, y)
print("  intercept %+.3f   b(pts_G resid) %+.4f   c(h1 cleared) %+.3f" % tuple(bt))
# player-block permutation on c
byp = collections.defaultdict(list)
for i, r in enumerate(M): byp[r["pl"]].append(i)
cnt = 0; B = 2000
for _ in range(B):
    lab = [X[i][2] for i in range(len(X))]
    for p_, ii in byp.items():
        v = [lab[i] for i in ii]; random.shuffle(v)
        for i, x in zip(ii, v): lab[i] = x
    X2 = [(1.0, X[i][1], lab[i]) for i in range(len(X))]
    try:
        if abs(ols(X2, y)[2]) >= abs(bt[2]): cnt += 1
    except ZeroDivisionError: pass
print("  player-block permutation p on c = %.4f" % ((cnt+1)/(B+1)))
import pickle; pickle.dump(M, open(os.path.join(ROOT,"outputs","hyp","h1_mech.pkl"),"wb"))
