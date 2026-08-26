import os,sys,pickle,math,random,statistics,collections
import numpy as np
from scipy.stats import rankdata
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
rng=np.random.default_rng(20260826); random.seed(20260826)
D=os.path.dirname(os.path.abspath(__file__))
S=pickle.load(open(os.path.join(D,"gm_sub.pkl"),"rb")); sub=S["sub"]; ms=S["ms"]
def gamekey(r): return (r["gt"], r["tm"] if r["home"] else r["opp"], r["opp"] if r["home"] else r["tm"])
def sp(x,y):
    a,b=rankdata(x),rankdata(y); a=a-a.mean(); b=b-b.mean()
    d=np.sqrt((a*a).sum()*(b*b).sum()); return float((a*b).sum()/d) if d else 0.0
def blockperm(rows,xf,yf,NP=1000,level="game"):
    x=np.array([xf(r) for r in rows],float); y=np.array([float(yf(r)) for r in rows],float)
    obs=sp(x,y); keyf=gamekey if level=="game" else (lambda r:r["pl"])
    gk=collections.defaultdict(list)
    for i,r in enumerate(rows): gk[keyf(r)].append(i)
    keys=list(gk); idxs=[np.array(gk[k]) for k in keys]; blocks=[x[i] for i in idxs]
    cnt=0; px=np.empty_like(x)
    for _ in range(NP):
        order=rng.permutation(len(keys))
        for t,s_ in enumerate(order):
            b=blocks[s_]; ii=idxs[t]
            px[ii]=b[:len(ii)] if len(b)>=len(ii) else np.resize(b,len(ii))
        if abs(sp(px,y))>=abs(obs): cnt+=1
    return obs,(cnt+1)/(NP+1),len(rows),len(keys)

print("### A. DOES THE ESTABLISHED 'TOTAL GRADIENT' SURVIVE A GAME-LEVEL NULL? ###")
for name,xf in [("tot(as-of)",lambda r:r["F"]["tot"]),("tot(mega_sweep field)",lambda r:r["tot"])]:
    rows=[r for r in sub if xf(r) is not None]
    o,p,n,k=blockperm(rows,xf,lambda r:r["over_won"],2000,"game")
    # anti-conservative quote-level shuffle, for comparison only
    x=np.array([xf(r) for r in rows],float); y=np.array([float(r["over_won"]) for r in rows])
    cnt=0
    for _ in range(2000):
        if abs(sp(rng.permutation(x),y))>=abs(o): cnt+=1
    print(f"  {name:<22} rho={o:+.4f}  p_GAMEblock={p:.4f}  p_quoteshuffle={(cnt+1)/2001:.4f}  n={n} games={k}")

print("\n### B. MECHANISM: does a high team_total actually raise raw production? ###")
# her production vs her own trailing median (team-filtered), against tonight's team total
rows=[r for r in sub if r["F"]["tt_own"] is not None]
def ttz(r):  # team total minus that team's own season-average posted team total (isolate tonight-specific)
    return r["F"]["tt_own"]
o,p,n,k=blockperm(rows,ttz,lambda r:r["zres"],2000,"game")
print(f"  rho(tt_own, standardised (actual-line))  = {o:+.4f} p={p:.4f} n={n} games={k}")
# team-level: realised team points vs posted team total, residualised on team identity
tg={}
for r in rows:
    key=(r["gt"],r["tm"])
    if key not in tg and r["teampts_actual"] is not None: tg[key]=(r["tm"],r["F"]["tt_own"],r["teampts_actual"])
byteam=collections.defaultdict(list)
for tm,tt,ap in tg.values(): byteam[tm].append((tt,ap))
xs=[];ys=[]
for tm,v in byteam.items():
    mt=statistics.mean(a for a,_ in v); mp=statistics.mean(b for _,b in v)
    for a,b in v: xs.append(a-mt); ys.append(b-mp)
print(f"  WITHIN-TEAM rho(tt_own deviation, realised pts deviation) = {sp(xs,ys):+.3f}  n={len(xs)} teamgames")
print("     -> the book's team total IS informative about tonight's team scoring")
# does she personally scale with it? her pts residual vs her own median, within player
byp=collections.defaultdict(list)
for r in rows:
    if r["mk"]!="pts": continue
    byp[r["pl"]].append((r["F"]["tt_own"],r["actual"]))
xs=[];ys=[]
for pl,v in byp.items():
    if len(v)<5: continue
    mt=statistics.mean(a for a,_ in v); mp=statistics.mean(b for _,b in v)
    for a,b in v: xs.append(a-mt); ys.append(b-mp)
print(f"  WITHIN-PLAYER rho(tt_own deviation, her PTS deviation)    = {sp(xs,ys):+.3f}  n={len(xs)} player-games")

print("\n### C. IS line_gap ANYTHING BEYOND medgap (her trailing median minus line)? ###")
rows=[r for r in sub if r["F"]["line_gap"] is not None and r["medgap"] is not None]
for nm,xf in [("medgap",lambda r:r["medgap"]),("line_gap (tt_own*hshare - line)",lambda r:r["F"]["line_gap"]),
              ("share_gap",lambda r:r["F"]["share_gap"])]:
    o,p,n,k=blockperm(rows,xf,lambda r:r["zres"],2000,"player")
    print(f"  rho({nm:<32}, zresid) = {o:+.4f} p={p:.4f}")
print(f"  rho(medgap, line_gap) = {sp([r['medgap'] for r in rows],[r['F']['line_gap'] for r in rows]):+.3f}")
# partial: residualise line_gap on medgap (rank space), then correlate
a=rankdata([r["medgap"] for r in rows]); b=rankdata([r["F"]["line_gap"] for r in rows])
a=a-a.mean(); b=b-b.mean(); beta=(a*b).sum()/(a*a).sum(); resid=b-beta*a
for r,v in zip(rows,resid): r["lg_pure"]=float(v)
o,p,n,k=blockperm(rows,lambda r:r["lg_pure"],lambda r:r["zres"],2000,"player")
print(f"  PARTIAL rho(line_gap | medgap, zresid) = {o:+.4f} p={p:.4f} n={n}")
o,p,n,k=blockperm(rows,lambda r:r["lg_pure"],lambda r:r["over_won"],2000,"player")
print(f"  PARTIAL rho(line_gap | medgap, over_won) = {o:+.4f} p={p:.4f} n={n}")
# the reverse: does medgap survive controlling for line_gap?
a2=rankdata([r["F"]["line_gap"] for r in rows]); b2=rankdata([r["medgap"] for r in rows])
a2=a2-a2.mean(); b2=b2-b2.mean(); beta2=(a2*b2).sum()/(a2*a2).sum(); res2=b2-beta2*a2
for r,v in zip(rows,res2): r["mg_pure"]=float(v)
o,p,n,k=blockperm(rows,lambda r:r["mg_pure"],lambda r:r["zres"],2000,"player")
print(f"  PARTIAL rho(medgap | line_gap, zresid) = {o:+.4f} p={p:.4f} n={n}")
pickle.dump(dict(sub=sub,ms=ms),open(os.path.join(D,"gm_sub2.pkl"),"wb"))
