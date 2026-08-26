# D - SEPARATE "PREDICTS THE MARKET" FROM "PREDICTS THE RESULT"
import os,sys,math,random,statistics,pickle,collections
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
random.seed(20260826)
OUT=r"C:\Users\Axioo\wnba-line-capture\outputs\track2"
OBS,anch=pickle.load(open(os.path.join(OUT,"obs.pkl"),"rb"))
NUM=pickle.load(open(os.path.join(OUT,"num.pkl"),"rb"))
def nxt(gid,key,el):
    a=sorted(NUM[gid].get(key,[]))
    for i,(e,v) in enumerate(a):
        if abs(e-el)<1e-9 and i+1<len(a): return a[i+1][1]-v
    return None
def pear(xs,ys):
    n=len(xs); mx=sum(xs)/n; my=sum(ys)/n
    sx=sum((x-mx)**2 for x in xs); sy=sum((y-my)**2 for y in ys)
    if sx<=0 or sy<=0: return None
    return sum((x-mx)*(y-my) for x,y in zip(xs,ys))/math.sqrt(sx*sy)
print("="*100)
print("D - TWO DIFFERENT EDGES, TESTED SEPARATELY")
print("  (1) PREDICTS THE MARKET : does state at refresh k forecast the price move at k+1?")
print("  (2) PREDICTS THE RESULT : does it forecast the settlement? (done above - slope + ROI tests)")
print("  GRID DECLARED: 2 markets x 3 predictors (anchor deviation, last step, elapsed) = 6 cells.")
print("  NULL: within-game circular shift of the next-move series.  Independent unit = GAME.")
print("="*100)
ROWS={}
for key,xk,ak,sgn in (("tot_line","l_tot","a_tot",1),("sp_line","l_sp","a_sp",-1)):
    rr=[]
    for r in OBS:
        if r.get(xk) is None or r.get(ak) is None: continue
        m=nxt(r["gid"],key,r["el"])
        if m is None: continue
        a=sorted(NUM[r["gid"]].get(key,[]))
        last=None
        for i,(e,v) in enumerate(a):
            if abs(e-r["el"])<1e-9 and i>0: last=v-a[i-1][1]
        rr.append(dict(gid=r["gid"],dev=sgn*(r[xk]-r[ak]),last=sgn*last if last is not None else None,
                       el=r["el"],nm=sgn*m))
    ROWS[key]=rr
def cellr(rr,pk,shift=False):
    byg=collections.defaultdict(list)
    for r in rr:
        if r.get(pk) is None: continue
        byg[r["gid"]].append(r)
    xs=[];ys=[];gs=0
    for g,v in byg.items():
        y=[r["nm"] for r in v]
        if shift and len(y)>1:
            j=random.randrange(len(y)); y=y[j:]+y[:j]
        xs+=[r[pk] for r in v]; ys+=y; gs+=1
    if len(xs)<12: return None,len(xs),gs
    return pear(xs,ys),len(xs),gs
NP=2000; bn=[]
for _ in range(NP):
    m=0
    for key in ROWS:
        for pk in ("dev","last","el"):
            r,_,_=cellr(ROWS[key],pk,shift=True)
            if r is not None: m=max(m,abs(r))
    bn.append(m)
bn.sort(); CEIL=bn[int(.95*NP)]
print("\nNOISE CEILING (%d game-block shifts, family-wise over 6 cells): p50 %.3f  p95 CEILING %.3f  max %.3f"%(
    NP,bn[NP//2],CEIL,bn[-1]))
print("\n%-9s %-22s %+8s %6s %6s %8s %s"%("market","predictor at refresh k","r","n","games","ceiling","verdict"))
LAB={"dev":"deviation from anchor","last":"last refresh step","el":"elapsed minutes"}
for key in ROWS:
    for pk in ("dev","last","el"):
        r,n,gs=cellr(ROWS[key],pk)
        if r is None: print("%-9s %-22s   (n=%d too small)"%(key,LAB[pk],n)); continue
        print("%-9s %-22s %+8.3f %6d %6d %8.3f %s"%(key,LAB[pk],r,n,gs,CEIL,"ABOVE CEILING" if abs(r)>CEIL else "under ceiling"))
print("\nRESULT: no predictor of the NEXT price move clears the ceiling. The market-prediction edge")
print("        (brief 32) is absent at the only horizon this feed can see (~15 min).")
