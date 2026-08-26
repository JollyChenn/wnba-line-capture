# Is the live line an UNBIASED forecast of the final? (slope b vs 1). And WHY (staleness check).
import os,sys,math,random,statistics,pickle,collections
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
random.seed(20260826)
OUT=r"C:\Users\Axioo\wnba-line-capture\outputs\track2"
OBS,anch=pickle.load(open(os.path.join(OUT,"obs.pkl"),"rb"))
games=pickle.load(open(os.path.join(OUT,"games.pkl"),"rb"))
REF=pickle.load(open(os.path.join(OUT,"ref.pkl"),"rb"))
def ols(xs,ys):
    n=len(xs); mx=sum(xs)/n; my=sum(ys)/n
    sxx=sum((x-mx)**2 for x in xs)
    if sxx<=0: return None,None
    b=sum((x-mx)*(y-my) for x,y in zip(xs,ys))/sxx
    return b, my-b*mx
def gboot(rows,xk,yk,B=3000):
    gs=sorted(set(r["gid"] for r in rows)); byg=collections.defaultdict(list)
    for r in rows: byg[r["gid"]].append(r)
    out=[]
    for _ in range(B):
        s=[random.choice(gs) for _ in gs]; rr=[]
        for g in s: rr+=byg[g]
        b,_=ols([r[xk] for r in rr],[r[yk] for r in rr])
        if b is not None: out.append(b)
    out.sort(); return out[int(.025*len(out))],out[int(.975*len(out))]
print("="*100)
print("IS THE LIVE LINE UNBIASED?   FINAL = a + b * LIVE.   b=1 => unbiased.  b>1 => line UNDER-reacts.")
print("Independent unit = GAME; CI by game bootstrap. 27 games max.")
print("="*100)
print("%-8s %-9s %5s %5s %8s %-22s %8s"%("market","band","n","games","b","95% CI (game boot)","R2"))
for name,xk,yk,sgn in (("TOTAL","l_tot","fin_tot",1),("SPREAD","l_sp","fin_mar",-1)):
    for lo,hi in [(0,45),(45,90),(90,150),(0,150)]:
        rows=[dict(r,X=sgn*r[xk]) for r in OBS if lo<=r["el"]<hi and r.get(xk) is not None]
        if len(rows)<12: continue
        b,a=ols([r["X"] for r in rows],[r[yk] for r in rows])
        lo_,hi_=gboot(rows,"X",yk)
        my=statistics.mean([r[yk] for r in rows])
        sst=sum((r[yk]-my)**2 for r in rows); sse=sum((r[yk]-(a+b*r["X"]))**2 for r in rows)
        print("%-8s %-9s %5d %5d %8.3f  [%.3f, %.3f]        %8.3f"%(
            name,"%d-%d"%(lo,hi),len(rows),len(set(r["gid"] for r in rows)),b,lo_,hi_,1-sse/sst if sst>0 else float('nan')))
print("\n"+"="*100)
print("MECHANISM CHECK (law 6): is b>1 a real market bias, or an artifact of the 15-min STALE feed?")
print("If the quote we see is simply LAGGED, then b must be far above 1 where the line moved a lot at the")
print("NEXT refresh, and ~1 where the next refresh did not move. A real bias would not care.")
print("="*100)
# attach next-refresh move
NUM=pickle.load(open(os.path.join(OUT,"num.pkl"),"rb"))
def nxt(gid,key,el):
    a=sorted(NUM[gid].get(key,[]))
    for i,(e,v) in enumerate(a):
        if abs(e-el)<1e-9 and i+1<len(a): return a[i+1][1]-v
    return None
print("%-8s %-18s %5s %5s %8s %-22s"%("market","next-refresh move","n","games","b","95% CI (game boot)"))
for name,xk,yk,key,sgn in (("TOTAL","l_tot","fin_tot","tot_line",1),("SPREAD","l_sp","fin_mar","sp_line",-1)):
    rows=[]
    for r in OBS:
        if r.get(xk) is None: continue
        d=nxt(r["gid"],key,r["el"])
        if d is None: continue
        rows.append(dict(r,X=sgn*r[xk],nm=abs(d)))
    if not rows: continue
    med=statistics.median([r["nm"] for r in rows])
    for lab,sel in (("small (<=median)",lambda r:r["nm"]<=med),("large (> median)",lambda r:r["nm"]>med)):
        rr=[r for r in rows if sel(r)]
        if len(rr)<12: continue
        b,a=ols([r["X"] for r in rr],[r[yk] for r in rr]); lo_,hi_=gboot(rr,"X",yk)
        print("%-8s %-18s %5d %5d %8.3f  [%.3f, %.3f]"%(name,lab,len(rr),len(set(r['gid'] for r in rr)),b,lo_,hi_))
    print("   median |next-refresh move| = %.2f pts"%med)
