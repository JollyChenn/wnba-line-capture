# Part 2: is the +1.49 gap a shared-baseline (regression-to-mean) artifact?
import os, sys, math, random, statistics, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hlib; ROOT = hlib.boot(globals())
random.seed(20260826)

H1 = {}
for r in load("outputs/hyp/h1_all.csv"):
    gid = r["game_id"]
    if gid not in gmeta: continue
    H1[(r["player"], gmeta[gid][1])] = dict(h1=f(r["h1"]), pts=f(r["pts"]), gid=gid)
Q = {}
for (pl, mk, gt), sd in side.items():
    if mk != "pts" or "Over" not in sd or "Under" not in sd: continue
    if sd["Over"][1] == sd["Under"][1]: Q[(pl, gt)] = sd["Over"][1]
def trail(pl, gt, k=10):
    p = [x for x in hist.get(pl, []) if x["tip"] < gt and x["tm"] == teamof.get(pl)][-k:]
    return statistics.median(x["pts"] for x in p) if len(p) >= 5 else None
M = []
for (pl, gt), h in sorted(H1.items()):
    now = pgrow.get((pl, gt))
    if not now or now["min"] < 8: continue
    m = trail(pl, gt)
    if m is None: continue
    fut = [x for x in hist.get(pl, []) if x["tip"] > gt]
    if not fut or fut[0]["min"] < 8: continue
    nx = fut[0]; line = Q.get((pl, gt)); ref = line if line is not None else m
    M.append(dict(pl=pl, gt=gt, gid=h["gid"], h1=h["h1"], pts=now["pts"], ref=ref, real=line is not None,
                  med=m, npts=nx["pts"], resid=nx["pts"]-m, ngt=nx["tip"]))
ev = lambda r: r["h1"] > r["ref"]
def gapof(rows, lab, val):
    a=[val(r) for r,l in zip(rows,lab) if l]; b=[val(r) for r,l in zip(rows,lab) if not l]
    if len(a)<5 or len(b)<5: return None
    return statistics.mean(a)-statistics.mean(b)
V = lambda r: r["resid"]
obs = gapof(M, [ev(r) for r in M], V)
print("baseline gap %+.3f  n=%d  ev=%d" % (obs, len(M), sum(ev(r) for r in M)))

# ---------------- MDE ----------------
sd = statistics.pstdev([r["resid"] for r in M]); n1=sum(ev(r) for r in M); n0=len(M)-n1
se_iid = sd*math.sqrt(1/n1+1/n0)
# design-effect-corrected se from player-block bootstrap
by=collections.defaultdict(list)
for r in M: by[r["pl"]].append(r)
ks=list(by); bs=[]
for _ in range(3000):
    s=[]
    for _ in range(len(ks)): s.extend(by[random.choice(ks)])
    g=gapof(s,[ev(r) for r in s],V)
    if g is not None: bs.append(g)
se_blk = statistics.pstdev(bs)
print("resid sd %.2f  se(iid) %.3f  se(player-block) %.3f  designeff %.2f" % (sd, se_iid, se_blk, (se_blk/se_iid)**2))
print("MDE (80%% power, a=.05, block se) = %.3f pts   observed %.3f" % (2.802*se_blk, obs))

# ---------------- PLACEBO NULL that KEEPS the label's dependence on ref/med ----------------
# swap h1 with the same player's h1 from another game: label still fires more often when ref is low.
byp = collections.defaultdict(list)
for i,r in enumerate(M): byp[r["pl"]].append(i)
h1s = {p:[M[i]["h1"] for i in ii] for p,ii in byp.items()}
gs=[]
for _ in range(4000):
    lab=[]
    for r in M:
        pool = h1s[r["pl"]]
        lab.append(random.choice(pool) > r["ref"])
    g=gapof(M,lab,V)
    if g is not None: gs.append(g)
gs.sort()
print("\nPLACEBO NULL (h1 resampled within player, ref kept): mean %+.3f  p95 %+.3f  p99 %+.3f  p(>=obs)=%.4f"
      % (statistics.mean(gs), gs[int(.95*len(gs))], gs[int(.99*len(gs))],
         (sum(1 for x in gs if abs(x)>=abs(obs))+1)/(len(gs)+1)))

# ---------------- outcome baseline that does NOT contain med_g ----------------
# leave-two-out player mean over panel games (excludes G and G+1)
ptsby = collections.defaultdict(list)
for (pl,gt),h in H1.items():
    g0 = pgrow.get((pl,gt))
    if g0 and g0["min"]>=8: ptsby[pl].append((gt,g0["pts"]))
def loo(pl, gt, ngt):
    v=[p for t,p in ptsby[pl] if t!=gt and t!=ngt]
    return statistics.mean(v) if len(v)>=4 else None
M2=[]
for r in M:
    mu=loo(r["pl"],r["gt"],r["ngt"])
    if mu is None: continue
    q=dict(r); q["resid2"]=r["npts"]-mu; M2.append(q)
g2=gapof(M2,[ev(r) for r in M2],lambda r:r["resid2"])
def perm(rows,lab_f,val,B=4000):
    by=collections.defaultdict(list)
    for i,r in enumerate(rows): by[r["pl"]].append(i)
    lab=[lab_f(r) for r in rows]; o=gapof(rows,lab,val); c=0
    for _ in range(B):
        l2=list(lab)
        for p_,ii in by.items():
            v=[lab[i] for i in ii]; random.shuffle(v)
            for i,x in zip(ii,v): l2[i]=x
        z=gapof(rows,l2,val)
        if z is not None and abs(z)>=abs(o): c+=1
    return o,(c+1)/(B+1)
o2,p2=perm(M2,ev,lambda r:r["resid2"])
a=[r["resid2"] for r in M2 if ev(r)]; b=[r["resid2"] for r in M2 if not ev(r)]
print("\nBASELINE SWAP  outcome = npts - leave-two-out player mean (no med_g in outcome):")
print("  n=%d  ev n=%d mean %+.3f | non n=%d mean %+.3f | gap %+.3f  player-perm p=%.4f"
      % (len(M2),len(a),statistics.mean(a),len(b),statistics.mean(b),o2,p2))
# and the ORIGINAL outcome on the same subset, for apples-to-apples
oA,pA=perm(M2,ev,V)
print("  same rows, ORIGINAL outcome (npts-med_g): gap %+.3f p=%.4f" % (oA,pA))

# ---------------- real posted line only ----------------
for nm,sub in [("real posted line",[r for r in M if r["real"]]),("median proxy",[r for r in M if not r["real"]])]:
    o,p=perm(sub,ev,V,B=3000)
    print("%-18s n=%4d ev=%3d gap %+.3f p=%.4f" % (nm,len(sub),sum(ev(r) for r in sub),o,p))

# ---------------- stratify by med_g level ----------------
print("\nmed_g stratification (is the gap concentrated where med_g is low?)")
for lo,hi in [(0,6.5),(6.5,10.5),(10.5,14.5),(14.5,99)]:
    sub=[r for r in M if lo<=r["med"]<hi]
    g=gapof(sub,[ev(r) for r in sub],V)
    print("  med %4.1f-%4.1f n=%4d ev=%3d gap %s" % (lo,hi,len(sub),sum(ev(r) for r in sub),
          ("%+.3f"%g) if g is not None else "-"))
