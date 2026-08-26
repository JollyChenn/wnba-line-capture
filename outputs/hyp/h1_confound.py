# Q3 done properly: stratify on resid_g = pts_G - med_G (the real "she scored a lot" variable),
# and check whether the +0.26 persistence coefficient is a shared-median artifact.
import os, sys, csv, math, random, statistics, datetime, collections, pickle
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hlib; ROOT = hlib.boot(globals())
random.seed(20260826)
M = pickle.load(open(os.path.join(ROOT,"outputs","hyp","h1_mech.pkl"),"rb"))
print("panel n=%d players=%d" % (len(M), len(set(r['pl'] for r in M))))

def blockp(sub, labfn, valfn, B=4000):
    a=[valfn(r) for r in sub if labfn(r)]; b=[valfn(r) for r in sub if not labfn(r)]
    if len(a)<5 or len(b)<5: return None,None,len(a),len(b)
    obs=statistics.mean(a)-statistics.mean(b)
    byp=collections.defaultdict(list)
    for i,r in enumerate(sub): byp[r["pl"]].append(i)
    lab=[labfn(r) for r in sub]; cnt=0
    for _ in range(B):
        l2=list(lab)
        for p_,ii in byp.items():
            v=[lab[i] for i in ii]; random.shuffle(v)
            for i,x in zip(ii,v): l2[i]=x
        aa=[valfn(sub[i]) for i in range(len(sub)) if l2[i]]
        bb=[valfn(sub[i]) for i in range(len(sub)) if not l2[i]]
        if len(aa)>=5 and len(bb)>=5 and abs(statistics.mean(aa)-statistics.mean(bb))>=abs(obs): cnt+=1
    return obs,(cnt+1)/(B+1),len(a),len(b)

EV = lambda r: r["h1"] > r["ref"]
print("\n--- STRATIFY ON resid_g = pts_G - med_G  (her own over/under-performance in G) ---")
print("%-16s %5s %9s %5s %9s %8s %8s" % ("resid_g bucket","nEv","ev resid","nNo","no resid","gap","p"))
cuts=[(-99,-3),(-3,0),(0,3),(3,7),(7,99)]
for lo,hi in cuts:
    sub=[r for r in M if lo<=r["resid_g"]<hi]
    obs,p,na,nb=blockp(sub,EV,lambda r:r["resid"])
    if obs is None:
        print("%-16s %5d %9s %5d" % (f"[{lo},{hi})",na,"-",nb)); continue
    a=[r["resid"] for r in sub if EV(r)]; b=[r["resid"] for r in sub if not EV(r)]
    print("%-16s %5d %+9.2f %5d %+9.2f %+8.2f %8.4f" % (f"[{lo},{hi})",na,statistics.mean(a),nb,statistics.mean(b),obs,p))

print("\n--- IS THE +0.26 PERSISTENCE REAL, OR A SHARED-MEDIAN ARTIFACT? ---")
# within-player demeaning removes the shared baseline entirely.
byp=collections.defaultdict(list)
for i,r in enumerate(M): byp[r["pl"]].append(i)
xs=[];ys=[]
for p_,ii in byp.items():
    if len(ii)<5: continue
    mg=statistics.mean(M[i]["resid_g"] for i in ii); mn=statistics.mean(M[i]["resid"] for i in ii)
    for i in ii: xs.append(M[i]["resid_g"]-mg); ys.append(M[i]["resid"]-mn)
def slope(x,y):
    n=len(x); mx=sum(x)/n; my=sum(y)/n
    sxy=sum((a-mx)*(b-my) for a,b in zip(x,y)); sxx=sum((a-mx)**2 for a in x)
    return sxy/sxx, sxy/math.sqrt(sxx*sum((b-my)**2 for b in y))
b_,r_=slope(xs,ys)
print("  within-player demeaned:  slope %+.4f  corr %+.4f  n=%d" % (b_,r_,len(xs)))
# permutation: shuffle y within player
cnt=0;B=2000
for _ in range(B):
    ys2=[]
    k=0
    for p_,ii in byp.items():
        if len(ii)<5: continue
        seg=ys[k:k+len(ii)]; k+=len(ii); random.shuffle(seg); ys2+=seg
    if abs(slope(xs,ys2)[0])>=abs(b_): cnt+=1
print("  player-block permutation p = %.4f  -> %s" % ((cnt+1)/(B+1),
      "big games DO persist (momentum), not regress" if b_>0 else "big games regress"))
# raw (undemeaned) for comparison
b2,r2=slope([r["resid_g"] for r in M],[r["resid"] for r in M])
print("  undemeaned (shares med_G on both sides): slope %+.4f corr %+.4f  <- the artifact-prone version" % (b2,r2))

print("\n--- DOES H1-CLEARING ADD ANYTHING ONCE resid_g IS MATCHED? (nearest-neighbour matching) ---")
# match each event row to non-event rows with resid_g within +/-1.0 and same player if possible
ev=[r for r in M if EV(r)]; ne=[r for r in M if not EV(r)]
bypl_ne=collections.defaultdict(list)
for r in ne: bypl_ne[r["pl"]].append(r)
diffs=[]; used=0
for r in ev:
    cands=[q for q in bypl_ne[r["pl"]] if abs(q["resid_g"]-r["resid_g"])<=1.0]
    if not cands: continue
    used+=1
    diffs.append(r["resid"]-statistics.mean(q["resid"] for q in cands))
print("  within-player, resid_g-matched pairs: n=%d  mean(event - matched control) = %+.3f pts" % (used, statistics.mean(diffs) if diffs else 0))
if diffs:
    se=statistics.pstdev(diffs)/math.sqrt(len(diffs)); print("  se %.3f  t %+.2f" % (se, statistics.mean(diffs)/se))
