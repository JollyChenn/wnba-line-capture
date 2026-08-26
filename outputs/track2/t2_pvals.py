import os,sys,math,random,statistics,pickle,collections
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
random.seed(20260826)
OUT=r"C:\Users\Axioo\wnba-line-capture\outputs\track2"
NUM=pickle.load(open(os.path.join(OUT,"num.pkl"),"rb"))
OBS,anch=pickle.load(open(os.path.join(OUT,"obs.pkl"),"rb"))
games=pickle.load(open(os.path.join(OUT,"games.pkl"),"rb"))
def pear(xs,ys):
    n=len(xs); mx=sum(xs)/n; my=sum(ys)/n
    sx=sum((x-mx)**2 for x in xs); sy=sum((y-my)**2 for y in ys)
    if sx<=0 or sy<=0: return None
    return sum((x-mx)*(y-my) for x,y in zip(xs,ys))/math.sqrt(sx*sy)
# per-cell p: tot_line lag-1 autocorr
d={}
for gid in NUM:
    a=sorted(NUM[gid].get("tot_line",[]))
    if len(a)<3: continue
    d[gid]=[b[1]-c[1] for c,b in zip(a,a[1:])]
def ac(dd,shift=False):
    xs=[];ys=[]
    for g,s in dd.items():
        s2=s[:]
        if shift and len(s2)>1:
            j=random.randrange(len(s2)); s2=s2[j:]+s2[:j]
        for a,b in zip(s2,s2[1:]): xs.append(a); ys.append(b)
    return pear(xs,ys)
obs=ac(d); N=20000; c=sum(1 for _ in range(N) if abs(ac(d,True))>=abs(obs))
print("tot_line lag-1 autocorr r=%.3f  per-cell two-sided permutation p = %.4f"%(obs,(c+1)/(N+1)))
# per-cell p for the best ROI cell: sp follow thr>=9, 45-90 min
def f(x):
    try: return float(x)
    except: return None
def dec(a):
    v=f(a); return None if v is None else 1+(100/(-v) if v<0 else v/100)
bets=[]
for r in OBS:
    if not (45<=r["el"]<90): continue
    L=r.get("l_sp"); A=r.get("a_sp"); pv=r.get("l_sp_px")
    if L is None or A is None or not pv: continue
    dv=(-L)-(-A)
    if abs(dv)<9: continue
    s=pv.split(",")
    home = dv>0
    p=dec(s[0] if home else s[1])
    if p: bets.append((r["gid"],L,home,p))
RES={g:(games[g]["hs"]+games[g]["as_"],games[g]["hs"]-games[g]["as_"]) for g in set(o["gid"] for o in OBS)}
def roi(rp):
    t=0;n=0
    for gid,L,home,p in bets:
        v=rp[gid][1]+L
        if abs(v)<1e-9: continue
        win = v>0 if home else v<0
        t+= (p-1) if win else -1; n+=1
    return t/n if n else 0
gl=sorted(RES); o=roi(RES); N=20000; c=0
for _ in range(N):
    sh=list(RES.values()); random.shuffle(sh)
    if abs(roi(dict(zip(gl,sh))))>=abs(o): c+=1
print("sp follow thr>=9 45-90min: n=%d bets over %d games, ROI %+.1f%%  per-cell game-permutation p = %.4f"%(
    len(bets),len(set(b[0] for b in bets)),100*o,(c+1)/(N+1)))
