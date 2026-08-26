import os,sys,random,statistics,collections
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import hlib; ROOT=hlib.boot(globals()); random.seed(11)
H1={}
for r in load("outputs/hyp/h1_all.csv"):
    g=r["game_id"]
    if g in gmeta: H1[(r["player"],gmeta[g][1])]=dict(h1=f(r["h1"]))
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
    nx=fut[0]; ln=Q.get((pl,gt))
    M.append(dict(pl=pl,gt=gt,h1=h["h1"],ref=ln if ln is not None else m,npts=nx["pts"],ngt=nx["tip"]))
pb=collections.defaultdict(list)
for (pl,gt),h in H1.items():
    g0=pgrow.get((pl,gt))
    if g0 and g0["min"]>=8: pb[pl].append((gt,g0["pts"]))
M2=[]
for r in M:
    v=[p for t,p in pb[r["pl"]] if t!=r["gt"] and t!=r["ngt"]]
    if len(v)>=4:
        q=dict(r); q["y"]=r["npts"]-statistics.mean(v); M2.append(q)
ev=lambda r:r["h1"]>r["ref"]
def gp(rows):
    a=[x["y"] for x in rows if ev(x)]; b=[x["y"] for x in rows if not ev(x)]
    return None if len(a)<5 or len(b)<5 else statistics.mean(a)-statistics.mean(b)
by=collections.defaultdict(list)
for r in M2: by[r["pl"]].append(r)
ks=list(by); out=[]
for _ in range(4000):
    s=[]
    for _ in range(len(ks)): s.extend(by[random.choice(ks)])
    g=gp(s)
    if g is not None: out.append(g)
out.sort()
print("corrected outcome (npts - leave-two-out player mean): gap %+.3f  n=%d  player-block CI [%+.3f, %+.3f]"
      % (gp(M2),len(M2),out[int(.025*len(out))],out[int(.975*len(out))]))
