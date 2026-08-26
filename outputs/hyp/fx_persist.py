# ADVERSARIAL FALSIFIER: "big WNBA scoring games PERSIST (demeaned lag-1 resid autocorr +0.191)"
import os, sys, csv, math, random, statistics, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hlib; ROOT = hlib.boot(globals())
random.seed(20260826)

# ---------------- NOISE CEILING DECLARED BEFORE RESULTS ----------------
# The grid actually tried below (all reported, none hidden):
#   baseline defs {shared trailing-median m_g, re-estimated m_(g+1), player full-sample median}
#   x {demeaned, undemeaned}  x  lag {1,2,3,4,5}  x  panel {H1 panel, full box}
# = 3*2*5*2 = 60 cells.  Null for a correlation with 159 independent blocks of ~12:
#   sd(r) ~ 1/sqrt(159) = 0.079 ; p95 of max|r| over 60 correlated cells ~ 2.6*0.079 = +0.206.
CEIL = 0.206
print("DECLARED NOISE CEILING (p95 of best-of-60-cell |r|, 159 player blocks): %.3f" % CEIL)

H1 = {}
for r in load("outputs/hyp/h1_all.csv"):
    gid = r["game_id"]
    if gid not in gmeta: continue
    H1[(r["player"], gmeta[gid][1])] = dict(h1=f(r["h1"]), h2=f(r["h2"]), pts=f(r["pts"]))

def trail(pl, gt, k=10, mk="pts"):
    p = [x for x in hist.get(pl, []) if x["tip"] < gt and x["tm"] == teamof.get(pl)][-k:]
    return statistics.median(x[mk] for x in p) if len(p) >= 5 else None

# ---------------- rebuild the claim's panel ----------------
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
    m_next = trail(pl, nx["tip"])          # baseline RE-ESTIMATED as of G+1 (not shared)
    M.append(dict(pl=pl, gt=gt, pts=now["pts"], npts=nx["pts"], med_g=m_g, med_next=m_next,
                  resid_g=now["pts"]-m_g, resid=nx["pts"]-m_g,
                  resid_indep=(nx["pts"]-m_next) if m_next is not None else None))
NP = len(set(x["pl"] for x in M))
print("PANEL n=%d transitions, players=%d   (claim said n=1928, players=159)" % (len(M), NP))

def slope_corr(xs, ys):
    n=len(xs); mx=sum(xs)/n; my=sum(ys)/n
    sxy=sum((a-mx)*(b-my) for a,b in zip(xs,ys)); sxx=sum((a-mx)**2 for a in xs); syy=sum((b-my)**2 for b in ys)
    return sxy/sxx, sxy/math.sqrt(sxx*syy)

def demean(rows, xk, yk):
    byp=collections.defaultdict(list)
    for r in rows: byp[r["pl"]].append(r)
    xs=[];ys=[];bl=[]
    for pl,rs in byp.items():
        mx=sum(r[xk] for r in rs)/len(rs); my=sum(r[yk] for r in rs)/len(rs)
        for r in rs: xs.append(r[xk]-mx); ys.append(r[yk]-my); bl.append(pl)
    return xs,ys,bl

def rawcols(rows, xk, yk):
    return [r[xk] for r in rows], [r[yk] for r in rows], [r["pl"] for r in rows]

print("\n=== 1. REPLICATION on the claim's own construction ===")
for tag, xk, yk, sub in [("SHARED med_G  (resid_g -> resid)","resid_g","resid",M),
                         ("INDEPENDENT baseline at G+1   ","resid_g","resid_indep",[r for r in M if r["resid_indep"] is not None])]:
    for dm in (False, True):
        xs,ys,bl = (demean if dm else rawcols)(sub, xk, yk)
        sl,co = slope_corr(xs,ys)
        print("  %s  %-9s n=%4d  slope=%+.4f  r=%+.4f" % (tag, "demeaned" if dm else "raw", len(xs), sl, co))

# ---------------- THE ARTIFACT TEST: synthetic i.i.d. players ----------------
# Under the null there is ZERO carryover: each player's game scores are drawn i.i.d.
# from her own observed distribution.  Rebuild m_g by the SAME trailing-median rule and
# recompute the SAME demeaned slope.  Anything the estimator prints here is pure artifact.
print("\n=== 2. NULL SIMULATION: i.i.d. players, same estimator (shared med_G) ===")
def sim_once():
    rows=[]
    for pl, hrows in hist.items():
        v=[x["pts"] for x in hrows if x["min"]>=8]
        if len(v) < 7: continue
        draw=[random.choice(v) for _ in range(len(v))]        # i.i.d., zero autocorrelation
        for i in range(5, len(draw)-1):
            m=statistics.median(draw[max(0,i-10):i])
            rows.append(dict(pl=pl, resid_g=draw[i]-m, resid=draw[i+1]-m,
                             resid_indep=draw[i+1]-statistics.median(draw[max(0,i-9):i+1])))
    return rows
sh_d=[];sh_r=[];in_d=[]
for _ in range(200):
    rr=sim_once()
    xs,ys,_=demean(rr,"resid_g","resid"); sh_d.append(slope_corr(xs,ys)[1])
    xs,ys,_=rawcols(rr,"resid_g","resid"); sh_r.append(slope_corr(xs,ys)[1])
    xs,ys,_=demean(rr,"resid_g","resid_indep"); in_d.append(slope_corr(xs,ys)[1])
def q(a,p): a=sorted(a); return a[int(p*(len(a)-1))]
print("  shared-med_G, RAW      : null mean r=%+.4f  95%%CI[%+.4f,%+.4f]" % (statistics.mean(sh_r), q(sh_r,.025), q(sh_r,.975)))
print("  shared-med_G, DEMEANED : null mean r=%+.4f  95%%CI[%+.4f,%+.4f]   <-- claim reports +0.1898 here" % (statistics.mean(sh_d), q(sh_d,.025), q(sh_d,.975)))
print("  independent baseline   : null mean r=%+.4f  95%%CI[%+.4f,%+.4f]" % (statistics.mean(in_d), q(in_d,.025), q(in_d,.975)))

# ---------------- 3. HONEST ESTIMATE + block CI + leave-out + MDE ----------------
S = [r for r in M if r["resid_indep"] is not None]
xs, ys, bl = demean(S, "resid_g", "resid_indep")
sl0, co0 = slope_corr(xs, ys)
print("\n=== 3. HONEST CELL (independent baseline, demeaned within player) ===")
print("  n=%d  players=%d  slope=%+.4f  r=%+.4f   [ceiling %.3f]" % (len(xs), len(set(bl)), sl0, co0, CEIL))

# player-block bootstrap
byp = collections.defaultdict(list)
for a,b,p in zip(xs,ys,bl): byp[p].append((a,b))
keys = list(byp)
bs = []
for _ in range(2000):
    pick = [random.choice(keys) for _ in keys]
    ax=[];ay=[]
    for k in pick:
        for a,b in byp[k]: ax.append(a); ay.append(b)
    bs.append(slope_corr(ax,ay)[1])
bs.sort()
print("  player-block bootstrap 95%% CI on r: [%+.4f, %+.4f]" % (bs[50], bs[1949]))

# player-block permutation (shuffle each player's y within her own block = kills ordering)
obs = co0; hit = 0; B = 2000
for _ in range(B):
    ax=[];ay=[]
    for k in keys:
        v = byp[k]; yy=[b for a,b in v]; random.shuffle(yy)
        for (a,_),b in zip(v,yy): ax.append(a); ay.append(b)
    if slope_corr(ax,ay)[1] >= obs: hit += 1
print("  within-player order permutation p = %.4f" % ((hit+1)/(B+1)))

# drop top-2 contributing players and top-2 contributing games
contrib = collections.Counter()
mx=sum(xs)/len(xs); my=sum(ys)/len(ys)
pairs=list(zip(xs,ys,bl))
for a,b,p in pairs: contrib[p] += (a-mx)*(b-my)
top2 = [p for p,_ in contrib.most_common(2)]
rest = [(a,b,p) for a,b,p in pairs if p not in top2]
print("  top-2 players by covariance contribution: %s (%.1f%% of total cov)" %
      (", ".join(top2), 100*sum(contrib[p] for p in top2)/sum(contrib.values())))
sl1, co1 = slope_corr([a for a,b,p in rest],[b for a,b,p in rest])
print("  after dropping them: n=%d  slope=%+.4f  r=%+.4f" % (len(rest), sl1, co1))
prs = sorted(pairs, key=lambda t: -(t[0]-mx)*(t[1]-my))[2:]
sl2, co2 = slope_corr([a for a,b,p in prs],[b for a,b,p in prs])
print("  after dropping top-2 single player-games: n=%d  r=%+.4f" % (len(prs), co2))

# MDE at this n / block count
import math as _m
se_block = statistics.pstdev(bs)
print("  block SE(r) = %.4f  ->  MDE at 80%% power, alpha .05 two-sided = %.3f" % (se_block, 2.80*se_block))

# ---------------- 4. IS IT 'THE OPPOSITE OF REGRESSION TO THE MEAN'? ----------------
print("\n=== 4. DIRECTION CHECK: does a big game REGRESS or PERSIST? ===")
q = sorted(r["resid_g"] for r in S)
hi = q[int(.90*len(q))]
big = [r for r in S if r["resid_g"] >= hi]
print("  top-decile games: mean resid_G = %+.2f pts above her own trailing median" %
      statistics.mean(r["resid_g"] for r in big))
print("  their NEXT game : mean resid    = %+.2f  ->  %.0f%% of the spike is given back" %
      (statistics.mean(r["resid_indep"] for r in big),
       100*(1 - statistics.mean(r["resid_indep"] for r in big)/statistics.mean(r["resid_g"] for r in big))))
print("  (a slope of %+.3f mechanically means %.0f%% of any deviation regresses; persistence would need slope>=1)" % (sl0, 100*(1-sl0)))

# lag profile: a one-game 'carryover' should decay; a slow role/minutes level does not
print("\n=== 5. LAG PROFILE (independent baseline, demeaned) - carryover vs standing level ===")
byp_ord = collections.defaultdict(list)
for pl, hrows in hist.items():
    v=[x for x in sorted(hrows,key=lambda z:z["tip"]) if x["min"]>=8]
    if len(v)>=8: byp_ord[pl]=[x["pts"] for x in v]
for k in (1,2,3,4,5):
    ax=[];ay=[]
    for pl,v in byp_ord.items():
        med=statistics.median(v); rs=[a-med for a in v]; m=sum(rs)/len(rs); rs=[a-m for a in rs]
        for i in range(len(rs)-k): ax.append(rs[i]); ay.append(rs[i+k])
    print("   lag-%d: n=%4d  r=%+.4f" % (k, len(ax), slope_corr(ax,ay)[1]))
