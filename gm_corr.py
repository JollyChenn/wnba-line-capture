import os,sys,pickle,math,random,statistics,collections
import numpy as np
from scipy.stats import rankdata
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
rng=np.random.default_rng(20260826); random.seed(20260826)
D=os.path.dirname(os.path.abspath(__file__))
R=pickle.load(open(os.path.join(D,"gm_rows.pkl"),"rb"))

def feats(r,pre="a_"):
    tot=r.get(pre+"tot"); spr=r.get(pre+"spr"); mlp=r.get(pre+"mlp")
    to=r.get(pre+"tt_own"); tp=r.get(pre+"tt_opp"); hm=r.get("hmshare")
    return dict(tot=tot,
        spr_abs=abs(spr) if spr is not None else None,
        spr_signed=spr, mlp=mlp, tt_own=to, tt_opp=tp,
        tt_diff=(to-tp) if (to is not None and tp is not None) else None,
        impshare=(r["line"]/to) if to else None,
        share_gap=(r["line"]/to-hm) if (to and hm is not None) else None,
        tt_line=(to*hm) if (to and hm is not None) else None,
        line_gap=(to*hm-r["line"]) if (to and hm is not None) else None)

MK=("pra","pr","pts")
for r in R:
    r["F"]=feats(r,"a_"); r["Fc"]=feats(r,"c_")
    r["modelS"]=(r["mk"] in MK and r.get("starred") is True)
sub=[r for r in R if r["F"]["tot"] is not None]
def gamekey(r): return (r["gt"], r["tm"] if r["home"] else r["opp"], r["opp"] if r["home"] else r["tm"])
print("rows with as-of pinnacle:",len(sub)," modelS-shaped:",sum(1 for r in sub if r["modelS"]),
      " games:",len(set(gamekey(r) for r in sub)))
d0=min(r["date"] for r in sub); d1=max(r["date"] for r in sub)
print("date range",d0,"-",d1)

def roi(rows,sd="Over"):
    if not rows: return (0,0.0,0.0)
    p=0
    for r in rows:
        w=r["over_won"] if sd=="Over" else (not r["over_won"])
        od=r["over_od"] if sd=="Over" else r["under_od"]
        p+=(od-1) if w else -1
    return (len(rows),p/len(rows)*100,sum(1 for r in rows if (r["over_won"] if sd=="Over" else not r["over_won"]))/len(rows)*100)
print("BASE board OVER   n=%d roi=%+.2f%% hit=%.1f%%"%roi(sub))
print("BASE board UNDER  n=%d roi=%+.2f%% hit=%.1f%%"%roi(sub,"Under"))
ms=[r for r in sub if r["modelS"]]
print("BASE modelS-shape n=%d roi=%+.2f%% hit=%.1f%%"%roi(ms))

bymk=collections.defaultdict(list)
for r in sub: bymk[r["mk"]].append(r["resid"])
sdmk={k:(statistics.pstdev(v) or 1) for k,v in bymk.items()}
for r in sub: r["zres"]=r["resid"]/sdmk[r["mk"]]

FEATS=["tot","spr_abs","spr_signed","mlp","tt_own","tt_opp","tt_diff","impshare","share_gap","tt_line","line_gap"]
GAMELVL={"tot","spr_abs","spr_signed","mlp","tt_own","tt_opp","tt_diff"}

def sp(x,y): 
    a,b=rankdata(x),rankdata(y)
    a=a-a.mean(); b=b-b.mean()
    den=np.sqrt((a*a).sum()*(b*b).sum())
    return float((a*b).sum()/den) if den else 0.0

def blockperm(rows,fn,yname,NP=1000,level="game"):
    x=np.array([r["F"][fn] for r in rows],float)
    y=np.array([float(r[yname]) for r in rows],float)
    obs=sp(x,y)
    keyf=gamekey if level=="game" else (lambda r:r["pl"])
    gk=collections.defaultdict(list)
    for i,r in enumerate(rows): gk[keyf(r)].append(i)
    keys=list(gk); idxs=[np.array(gk[k]) for k in keys]
    blocks=[x[i] for i in idxs]
    cnt=0; px=np.empty_like(x)
    for _ in range(NP):
        order=rng.permutation(len(keys))
        for tgt,srci in enumerate(order):
            b=blocks[srci]; ii=idxs[tgt]
            if len(b)>=len(ii): px[ii]=b[:len(ii)]
            else: px[ii]=np.resize(b,len(ii))
        if abs(sp(px,y))>=abs(obs): cnt+=1
    return obs,(cnt+1)/(NP+1),len(rows),len(keys)

print("\n=== CORRELATION MATRIX  (Pinnacle line as of the prop's own capture instant) ===")
print("universe: every two-sided board quote with a Pinnacle snapshot  n=%d"%len(sub))
print(f"{'feature':<11} {'lvl':<6} {'rho_overwon':>11} {'p':>6} {'rho_zresid':>11} {'p':>6} {'n':>5} {'blk':>5}")
res={}
for fn in FEATS:
    rows=[r for r in sub if r["F"][fn] is not None]
    if len(rows)<50: print(f"{fn:<11} n={len(rows)} too small"); continue
    lvl="game" if fn in GAMELVL else "player"
    a=blockperm(rows,fn,"over_won",1000,lvl); b=blockperm(rows,fn,"zres",1000,lvl)
    res[fn]=(a,b)
    print(f"{fn:<11} {lvl:<6} {a[0]:>11.4f} {a[1]:>6.3f} {b[0]:>11.4f} {b[1]:>6.3f} {a[2]:>5} {a[3]:>5}")

print("\n--- same matrix, MODEL-S-SHAPED subset (mk in pra/pr/pts AND not-raised) ---")
print(f"{'feature':<11} {'rho_overwon':>11} {'p':>6} {'rho_zresid':>11} {'p':>6} {'n':>5} {'blk':>5}")
for fn in FEATS:
    rows=[r for r in ms if r["F"][fn] is not None]
    if len(rows)<50: print(f"{fn:<11} n={len(rows)} too small"); continue
    lvl="game" if fn in GAMELVL else "player"
    a=blockperm(rows,fn,"over_won",1000,lvl); b=blockperm(rows,fn,"zres",1000,lvl)
    print(f"{fn:<11} {a[0]:>11.4f} {a[1]:>6.3f} {b[0]:>11.4f} {b[1]:>6.3f} {a[2]:>5} {a[3]:>5}")

print("\n--- redundancy among game markets (ONE ROW PER GAME) ---")
seen={}
for r in sub:
    k=gamekey(r)
    if k not in seen: seen[k]=r["F"]
G=list(seen.values()); gl=["tot","spr_abs","spr_signed","mlp","tt_own","tt_opp","tt_diff"]
print("n games =",len(G))
print(f"{'':<12}"+" ".join(f"{x:>9}" for x in gl))
for a in gl:
    line=f"{a:<12}"
    for b in gl:
        pairs=[(g[a],g[b]) for g in G if g[a] is not None and g[b] is not None]
        line+=f" {sp([p[0] for p in pairs],[p[1] for p in pairs]):>9.3f}" if len(pairs)>10 else "        na"
    print(line)
dd=[abs((g["tt_own"]+g["tt_opp"])-g["tot"]) for g in G if g["tt_own"] is not None and g["tot"] is not None]
if dd: print(f"|tt_own+tt_opp - tot|      median={statistics.median(dd):.2f} mean={statistics.mean(dd):.2f} max={max(dd):.2f} n={len(dd)}")
dd=[abs((g["tt_opp"]-g["tt_own"])-g["spr_signed"]) for g in G if g["tt_own"] is not None and g["spr_signed"] is not None]
if dd: print(f"|(tt_opp-tt_own)-spr_signed| median={statistics.median(dd):.2f} mean={statistics.mean(dd):.2f} max={max(dd):.2f} n={len(dd)}")

# ---- MECHANISM: do the game markets forecast REAL team output? ----
print("\n--- mechanism: do Pinnacle team_totals forecast realised team points? (one row per team-game) ---")
tg={}
for r in sub:
    k=(r["gt"],r["tm"])
    if k not in tg and r["F"]["tt_own"] is not None and r["teampts_actual"] is not None:
        tg[k]=(r["F"]["tt_own"],r["teampts_actual"],r["F"]["tot"],(r["teampts_actual"]+ (r["opppts_actual"] or 0)))
V=list(tg.values())
print("n team-games",len(V))
x=[v[0] for v in V]; y=[v[1] for v in V]
print("  rho(tt_own, realised team pts) = %.3f"%sp(x,y), " pearson=%.3f"%float(np.corrcoef(x,y)[0,1]))
print("  mean(realised - tt_own) = %+.2f  sd=%.2f"%(statistics.mean([b-a for a,b,_,_ in V]),statistics.pstdev([b-a for a,b,_,_ in V])))
pickle.dump(dict(sub=sub,ms=ms,sdmk=sdmk),open(os.path.join(D,"gm_sub.pkl"),"wb"))
