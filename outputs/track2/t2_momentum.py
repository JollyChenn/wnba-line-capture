# TESTS A (momentum), B (mean reversion), D (short-horizon price prediction)
# GRID DECLARED UP FRONT; game-block null ceiling computed BEFORE real results are printed.
import os,sys,math,random,statistics,pickle,collections
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
random.seed(20260826)
OUT=r"C:\Users\Axioo\wnba-line-capture\outputs\track2"
SER=pickle.load(open(os.path.join(OUT,"ser.pkl"),"rb"))
games=pickle.load(open(os.path.join(OUT,"games.pkl"),"rb"))

SERIES=["ml_p","sp_fair","tot_fair","sp_line","tot_line"]
LOOK=[1,2,5,10]; HOR=[1,2,5,10]
NCELL=len(SERIES)*len(LOOK)*len(HOR)
print("="*100)
print("GRID (declared before results): %d series x %d lookbacks x %d horizons = %d cells"%(len(SERIES),len(LOOK),len(HOR),NCELL))
print("  series   :",SERIES)
print("  lookbacks:",LOOK,"min   horizons:",HOR,"min")
print("  statistic: Pearson r between backward change (t-L -> t) and forward change (t -> t+H)")
print("  NULL     : within-game random circular shift of the forward-change series (game block preserved)")
print("="*100)

def val_at(arr,target,tol):
    # arr sorted list of (el,v); nearest within tol
    best=None
    for e,v in arr:
        d=abs(e-target)
        if d<=tol and (best is None or d<best[0]): best=(d,v)
    return best[1] if best else None

def build(gid,key,L,H):
    arr=sorted(SER[gid].get(key,[]))
    if len(arr)<5: return []
    out=[]
    tolL=max(0.75,0.30*L); tolH=max(0.75,0.30*H)
    for e,v in arr:
        a=val_at(arr,e-L,tolL); b=val_at(arr,e+H,tolH)
        if a is None or b is None: continue
        out.append((e,v-a,b-v))
    return out

# assemble once per (key,L,H)
DATA={}
for key in SERIES:
    for L in LOOK:
        for H in HOR:
            d={}
            for gid in SER:
                r=build(gid,key,L,H)
                if len(r)>=5: d[gid]=r
            DATA[(key,L,H)]=d

def pear(xs,ys):
    n=len(xs)
    if n<10: return None
    mx=sum(xs)/n; my=sum(ys)/n
    sx=sum((x-mx)**2 for x in xs); sy=sum((y-my)**2 for y in ys)
    if sx<=0 or sy<=0: return None
    return sum((x-mx)*(y-my) for x,y in zip(xs,ys))/math.sqrt(sx*sy)

def cell_r(d,shift=False):
    xs=[];ys=[]
    for gid,rows in d.items():
        b=[r[1] for r in rows]; fw=[r[2] for r in rows]
        if shift:
            k=random.randrange(len(fw)); fw=fw[k:]+fw[:k]
        xs+=b; ys+=fw
    return pear(xs,ys),len(xs),len(d)

# ---- NOISE CEILING under the null, computed BEFORE real numbers ----
NPERM=400
best_null=[]
for it in range(NPERM):
    m=0.0
    for k,d in DATA.items():
        r,_,_=cell_r(d,shift=True)
        if r is not None: m=max(m,abs(r))
    best_null.append(m)
best_null.sort()
CEIL=best_null[int(0.95*NPERM)]
print("\nNOISE CEILING  (%d game-block circular-shift permutations over the full %d-cell grid)"%(NPERM,NCELL))
print("  p50 best-cell |r| = %.4f    p95 (THE CEILING) = %.4f    max = %.4f"%(best_null[NPERM//2],CEIL,best_null[-1]))
print("  ANY cell with |r| below %.4f is NOT a finding."%CEIL)

print("\n%-9s %3s %3s %8s %8s %6s %6s %s"%("series","L","H","r","ceil","n_obs","games","verdict"))
res=[]
for key in SERIES:
    for L in LOOK:
        for H in HOR:
            d=DATA[(key,L,H)]
            r,n,ng=cell_r(d)
            if r is None: continue
            res.append((abs(r),key,L,H,r,n,ng))
res.sort(reverse=True)
for a,key,L,H,r,n,ng in res[:20]:
    print("%-9s %3d %3d %+8.4f %8.4f %6d %6d %s"%(key,L,H,r,CEIL,n,ng,"ABOVE CEILING" if a>CEIL else "under ceiling"))
print("  ... (%d cells total, showing top 20 by |r|)"%len(res))
nab=sum(1 for a,*_ in res if a>CEIL)
print("\ncells above ceiling: %d / %d   (expect ~%.1f by chance at p95 family-wise)"%(nab,len(res),0.05*1))

# game-block bootstrap CI for the single best cell + a signed summary per market
print("\nPER-SERIES SUMMARY (L=H, the cleanest symmetric read); sign: + = MOMENTUM, - = MEAN REVERSION")
print("%-9s %3s %+9s %-24s %6s %6s"%("series","lag","r","95% CI (game-block boot)","n_obs","games"))
def boot_ci(d,B=600):
    gids=list(d); out=[]
    for _ in range(B):
        s=[random.choice(gids) for _ in gids]
        xs=[];ys=[]
        for gid in s:
            xs+=[r[1] for r in d[gid]]; ys+=[r[2] for r in d[gid]]
        r=pear(xs,ys)
        if r is not None: out.append(r)
    out.sort(); return out[int(.025*len(out))],out[int(.975*len(out))]
for key in SERIES:
    for L in LOOK:
        d=DATA[(key,L,L)]
        r,n,ng=cell_r(d)
        if r is None: continue
        lo,hi=boot_ci(d)
        print("%-9s %3d %+9.4f  [%+.4f, %+.4f]        %6d %6d"%(key,L,r,lo,hi,n,ng))

# ---- TEST B: MEAN REVERSION conditioned on move size in units of THAT GAME's realised vol ----
print("\n"+"="*100)
print("TEST B - MEAN REVERSION AFTER AN UNUSUALLY LARGE MOVE")
print("  'large' = |backward move| >= k x that game's own realised sd of L-min changes (k in {1.5,2,3})")
print("  GRID: 5 series x 4 lookbacks x 3 thresholds x (fwd horizon = L) = 60 cells")
KS=[1.5,2.0,3.0]
print("  NULL: same within-game circular shift.")
def revcell(d,k,shift=False):
    tot=0;n=0;ng=set()
    for gid,rows in d.items():
        b=[r[1] for r in rows]; fw=[r[2] for r in rows]
        if shift:
            j=random.randrange(len(fw)); fw=fw[j:]+fw[:j]
        if len(b)<8: continue
        sd=statistics.pstdev(b)
        if sd<=0: continue
        for bb,ff in zip(b,fw):
            if abs(bb)>=k*sd:
                tot+= -math.copysign(1,bb)*ff/sd   # positive = reverted
                n+=1; ng.add(gid)
    if n<20: return None,n,len(ng)
    return tot/n,n,len(ng)
NP2=400; bn=[]
for _ in range(NP2):
    m=0
    for key in SERIES:
        for L in LOOK:
            d=DATA[(key,L,L)]
            for k in KS:
                v,n,_=revcell(d,k,shift=True)
                if v is not None: m=max(m,abs(v))
    bn.append(m)
bn.sort(); CEIL2=bn[int(.95*NP2)]
print("\n  NOISE CEILING p95 best-cell |mean reversion (sd units)| = %.4f  (p50 %.4f, max %.4f)"%(CEIL2,bn[NP2//2],bn[-1]))
print("\n%-9s %3s %5s %10s %8s %6s %6s %s"%("series","L","k","revert","ceil","n","games","verdict"))
rows=[]
for key in SERIES:
    for L in LOOK:
        d=DATA[(key,L,L)]
        for k in KS:
            v,n,ng=revcell(d,k)
            if v is None: continue
            rows.append((abs(v),key,L,k,v,n,ng))
rows.sort(reverse=True)
for a,key,L,k,v,n,ng in rows[:15]:
    print("%-9s %3d %5.1f %+10.4f %8.4f %6d %6d %s"%(key,L,k,v,CEIL2,n,ng,"ABOVE CEILING" if a>CEIL2 else "under ceiling"))
print("  (%d cells; %d above ceiling)"%(len(rows),sum(1 for a,*_ in rows if a>CEIL2)))
pickle.dump(DATA,open(os.path.join(OUT,"mom.pkl"),"wb"))
