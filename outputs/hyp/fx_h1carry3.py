import os, sys, math, random, statistics, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hlib; ROOT = hlib.boot(globals())
random.seed(7770826)
H1={}
for r in load("outputs/hyp/h1_all.csv"):
    g=r["game_id"]
    if g in gmeta: H1[(r["player"],gmeta[g][1])]=dict(h1=f(r["h1"]),pts=f(r["pts"]),gid=g)
Q={}
for (pl,mk,gt),sd in side.items():
    if mk=="pts" and "Over" in sd and "Under" in sd and sd["Over"][1]==sd["Under"][1]: Q[(pl,gt)]=sd["Over"][1]
def trail(pl,gt,k=10):
    p=[x for x in hist.get(pl,[]) if x["tip"]<gt and x["tm"]==teamof.get(pl)][-k:]
    return statistics.median(x["pts"] for x in p) if len(p)>=5 else None
M=[]
for (pl,gt),h in sorted(H1.items()):
    now=pgrow.get((pl,gt))
    if not now or now["min"]<8: continue
    m=trail(pl,gt)
    if m is None: continue
    fut=[x for x in hist.get(pl,[]) if x["tip"]>gt]
    if not fut or fut[0]["min"]<8: continue
    nx=fut[0]; ln=Q.get((pl,gt)); ref=ln if ln is not None else m
    M.append(dict(pl=pl,gt=gt,h1=h["h1"],pts=now["pts"],ref=ref,med=m,npts=nx["pts"],resid=nx["pts"]-m,ngt=nx["tip"]))
ev=lambda r: r["h1"]>r["ref"]
def gapof(rows,lab,val):
    a=[val(r) for r,l in zip(rows,lab) if l]; b=[val(r) for r,l in zip(rows,lab) if not l]
    return None if len(a)<5 or len(b)<5 else statistics.mean(a)-statistics.mean(b)
V=lambda r:r["resid"]; obs=gapof(M,[ev(r) for r in M],V)

# WHY: the outcome baseline med_g is itself biased -> resid depends on med_g
print("mean resid by med_g bucket (the confound engine):")
for lo,hi in [(0,6.5),(6.5,10.5),(10.5,14.5),(14.5,99)]:
    s=[r for r in M if lo<=r["med"]<hi]
    print("  med %4.1f-%4.1f n=%4d  mean resid %+.3f   event rate %.1f%%" %
          (lo,hi,len(s),statistics.mean(r["resid"] for r in s),100*sum(ev(r) for r in s)/len(s)))

# placebo null, EXCLUDING the row's own h1 from the resample pool
byp=collections.defaultdict(list)
for i,r in enumerate(M): byp[r["pl"]].append(i)
gs=[]
for _ in range(4000):
    lab=[]
    for i,r in enumerate(M):
        pool=[j for j in byp[r["pl"]] if j!=i] or byp[r["pl"]]
        lab.append(M[random.choice(pool)]["h1"] > r["ref"])
    g=gapof(M,lab,V)
    if g is not None: gs.append(g)
gs.sort()
print("\nPLACEBO NULL (leave-self-out h1 resample within player, ref kept), B=%d" % len(gs))
print("  null mean %+.3f  p5 %+.3f  p95 %+.3f   OBSERVED %+.3f   p(|null|>=|obs|)=%.4f  p(null>=obs)=%.4f"
      % (statistics.mean(gs),gs[int(.05*len(gs))],gs[int(.95*len(gs))],obs,
         (sum(1 for x in gs if abs(x)>=abs(obs))+1)/(len(gs)+1),
         (sum(1 for x in gs if x>=obs)+1)/(len(gs)+1)))

# max-stat ceiling over the threshold grid actually available, under the SAME placebo null
grid=[("h1>ref",lambda r,h: h>r["ref"]),("h1>=ref+1",lambda r,h: h>=r["ref"]+1),
      ("h1>=ref+2",lambda r,h: h>=r["ref"]+2),("h1>=ref+3",lambda r,h: h>=r["ref"]+3),
      ("h1>=ref+4",lambda r,h: h>=r["ref"]+4),("h1>=ref-1",lambda r,h: h>=r["ref"]-1)]
real={nm:gapof(M,[fn(r,r["h1"]) for r in M],V) for nm,fn in grid}
mx=[]
for _ in range(1500):
    draw=[]
    for i,r in enumerate(M):
        pool=[j for j in byp[r["pl"]] if j!=i] or byp[r["pl"]]
        draw.append(M[random.choice(pool)]["h1"])
    best=0
    for nm,fn in grid:
        g=gapof(M,[fn(r,h) for r,h in zip(M,draw)],V)
        if g is not None: best=max(best,g)
    mx.append(best)
mx.sort()
print("\nGRID (6 thresholds).  max-cell ceiling under placebo null: p95 = %+.3f  median %+.3f" % (mx[int(.95*len(mx))],mx[int(.5*len(mx))]))
for nm,g in real.items(): print("   %-11s gap %+.3f  %s" % (nm,g,"OVER ceiling" if g>mx[int(.95*len(mx))] else "under ceiling"))
