# TESTS A / B / D re-run at the ONLY resolution the data supports: the ~15-min refresh step.
import os,sys,math,random,statistics,pickle,collections
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
random.seed(20260826)
OUT=r"C:\Users\Axioo\wnba-line-capture\outputs\track2"
REF=pickle.load(open(os.path.join(OUT,"ref.pkl"),"rb"))
games=pickle.load(open(os.path.join(OUT,"games.pkl"),"rb"))
def f(x):
    try: return float(x)
    except (TypeError,ValueError): return None
def am(p):
    v=f(p)
    if v is None: return None
    return (-v)/((-v)+100) if v<0 else 100/(v+100)
def pr(pv):
    s=(pv or "").split(",")
    if len(s)!=2: return None
    a,b=am(s[0]),am(s[1])
    if a is None or b is None or a+b<=0: return None
    return a/(a+b)
# numeric refresh-level series
NUM=collections.defaultdict(dict)  # gid -> key -> [(el,val)]
for gid,seq in REF.items():
    for el,snap in seq:
        for (tp,side,pts,alt),(p_,pv) in snap.items():
            if alt=="1": continue
            v=pr(pv)
            if tp=="moneyline" and v is not None: NUM[gid].setdefault("ml_p",[]).append((el,v))
            elif tp=="spread": 
                if f(pts) is not None: NUM[gid].setdefault("sp_line",[]).append((el,f(pts)))
            elif tp=="total":
                if f(pts) is not None: NUM[gid].setdefault("tot_line",[]).append((el,f(pts)))
            elif tp=="team_total":
                k="tth_line" if side=="home" else "tta_line"
                if f(pts) is not None: NUM[gid].setdefault(k,[]).append((el,f(pts)))
SERIES=["ml_p","sp_line","tot_line","tth_line","tta_line"]
print("="*100)
print("TESTS A/B/D AT TRUE RESOLUTION - one step = one ~15-min quote refresh")
print("GRID DECLARED: 5 series x 3 statistics (lag-1 autocorr of steps; reversion|step|>=1.5sd; reversion|step|>=2sd)")
print("             = 15 cells.  Independent unit = GAME.  Statistic pooled over steps, CI by game bootstrap.")
print("NULL: within-game random circular shift of the step sequence (preserves each game's step distribution).")
print("="*100)
D={}
for k in SERIES:
    d={}
    for gid in NUM:
        a=sorted(NUM[gid].get(k,[]))
        if len(a)<3: continue
        steps=[b[1]-c[1] for c,b in zip(a,a[1:])]
        d[gid]=steps
    D[k]=d
for k in SERIES:
    ns=sum(len(v) for v in D[k].values()); npair=sum(max(0,len(v)-1) for v in D[k].values())
    print("  %-9s games=%2d  refresh-steps=%3d  consecutive-step PAIRS=%3d"%(k,len(D[k]),ns,npair))

def pear(xs,ys):
    n=len(xs)
    if n<8: return None
    mx=sum(xs)/n; my=sum(ys)/n
    sx=sum((x-mx)**2 for x in xs); sy=sum((y-my)**2 for y in ys)
    if sx<=0 or sy<=0: return None
    return sum((x-mx)*(y-my) for x,y in zip(xs,ys))/math.sqrt(sx*sy)
def ac(d,shift=False):
    xs=[];ys=[];gs=set()
    for gid,s in d.items():
        s2=s[:]
        if shift and len(s2)>1:
            j=random.randrange(len(s2)); s2=s2[j:]+s2[:j]
        for a,b in zip(s2,s2[1:]): xs.append(a); ys.append(b); gs.add(gid)
    return pear(xs,ys),len(xs),len(gs)
def rev(d,kk,shift=False):
    tot=0;n=0;gs=set()
    for gid,s in d.items():
        s2=s[:]
        if shift and len(s2)>1:
            j=random.randrange(len(s2)); s2=s2[j:]+s2[:j]
        if len(s2)<3: continue
        sd=statistics.pstdev(s)
        if sd<=0: continue
        for a,b in zip(s2,s2[1:]):
            if abs(a)>=kk*sd:
                tot+=-math.copysign(1,a)*b/sd; n+=1; gs.add(gid)
    if n<10: return None,n,len(gs)
    return tot/n,n,len(gs)
CELLS=[("autocorr",None)]+[("revert",1.5),("revert",2.0)]
NP=2000; bn_ac=[];bn_rv=[]
for _ in range(NP):
    m1=0;m2=0
    for k in SERIES:
        r,_,_=ac(D[k],shift=True)
        if r is not None: m1=max(m1,abs(r))
        for kk in (1.5,2.0):
            v,_,_=rev(D[k],kk,shift=True)
            if v is not None: m2=max(m2,abs(v))
    bn_ac.append(m1); bn_rv.append(m2)
bn_ac.sort(); bn_rv.sort()
C_AC=bn_ac[int(.95*NP)]; C_RV=bn_rv[int(.95*NP)]
print("\nNOISE CEILING (%d game-block circular-shift permutations, family-wise over the 15-cell grid):"%NP)
print("  best-cell |lag-1 autocorr| : p50 %.3f  p95 CEILING %.3f  max %.3f"%(bn_ac[NP//2],C_AC,bn_ac[-1]))
print("  best-cell |reversion (sd)| : p50 %.3f  p95 CEILING %.3f  max %.3f"%(bn_rv[NP//2],C_RV,bn_rv[-1]))
print("  Nothing below these is a finding.\n")
def gboot(d,fn,B=2000,*a):
    gids=list(d); out=[]
    for _ in range(B):
        s=[random.choice(gids) for _ in gids]
        dd={}
        for i,g in enumerate(s): dd[(g,i)]=d[g]
        v=fn(dd,*a)[0]
        if v is not None: out.append(v)
    out.sort(); return (out[int(.025*len(out))],out[int(.975*len(out))]) if len(out)>50 else (float('nan'),float('nan'))
print("A - MOMENTUM / AUTOCORRELATION OF ~15-MIN PRICE STEPS   (+ = momentum, - = reversion)")
print("%-9s %+8s %-22s %6s %6s %8s %s"%("series","r","95% CI (game boot)","pairs","games","ceiling","verdict"))
for k in SERIES:
    r,n,ng=ac(D[k])
    if r is None: print("%-9s   (insufficient)"%k); continue
    lo,hi=gboot(D[k],ac)
    print("%-9s %+8.3f  [%+.3f, %+.3f]      %6d %6d %8.3f %s"%(k,r,lo,hi,n,ng,C_AC,"ABOVE CEILING" if abs(r)>C_AC else "under ceiling"))
print("\nB - MEAN REVERSION AFTER A LARGE STEP (large = >= k x that game's own step sd)")
print("%-9s %4s %+9s %-22s %6s %6s %8s %s"%("series","k","revert","95% CI (game boot)","n","games","ceiling","verdict"))
for k in SERIES:
    for kk in (1.5,2.0):
        v,n,ng=rev(D[k],kk)
        if v is None: print("%-9s %4.1f   (n=%d too small)"%(k,kk,n)); continue
        lo,hi=gboot(D[k],rev,2000,kk)
        print("%-9s %4.1f %+9.3f  [%+.3f, %+.3f]      %6d %6d %8.3f %s"%(k,kk,v,lo,hi,n,ng,C_RV,"ABOVE CEILING" if abs(v)>C_RV else "under ceiling"))
pickle.dump(NUM,open(os.path.join(OUT,"num.pkl"),"wb"))
