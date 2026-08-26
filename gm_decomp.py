import os,sys,pickle,math,random,statistics,collections
import numpy as np
from scipy.stats import rankdata
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
rng=np.random.default_rng(20260826)
D=os.path.dirname(os.path.abspath(__file__))
S=pickle.load(open(os.path.join(D,"gm_sub2.pkl"),"rb")); sub=S["sub"]; ms=S["ms"]
def gamekey(r): return (r["gt"], r["tm"] if r["home"] else r["opp"], r["opp"] if r["home"] else r["tm"])
def sp(x,y):
    a,b=rankdata(x),rankdata(y); a=a-a.mean(); b=b-b.mean()
    d=np.sqrt((a*a).sum()*(b*b).sum()); return float((a*b).sum()/d) if d else 0.0
def blockperm(rows,xf,yf,NP=2000,level="player"):
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
    return obs,(cnt+1)/(NP+1)

# --- step 0: is the mega_sweep 'tot' field the same number as the clean main-line total? ---
both=[r for r in sub if r.get("tot") is not None and r["F"]["tot"] is not None]
dif=[r["tot"]-r["F"]["tot"] for r in both]
print("mega_sweep tot vs clean as-of main total: n=%d  mean diff %+.2f  median %+.2f  |diff|>1 on %.1f%%"%(
    len(both),statistics.mean(dif),statistics.median(dif),100*sum(1 for d in dif if abs(d)>1)/len(dif)))
g57=set(gamekey(r) for r in both)
same=[r for r in sub if gamekey(r) in g57]
print("clean tot restricted to the SAME %d games: rho=%+.4f  (mega_sweep field on those games rho=%+.4f)"%(
    len(g57), sp([r["F"]["tot"] for r in same],[float(r["over_won"]) for r in same]),
    sp([r["tot"] for r in both],[float(r["over_won"]) for r in both])))

# --- team mean posted team total, per team (leak-free enough: it is a level, not tonight) ---
tt_by_team=collections.defaultdict(list)
seen=set()
for r in sub:
    k=(r["gt"],r["tm"])
    if k in seen or r["F"]["tt_own"] is None: continue
    seen.add(k); tt_by_team[r["tm"]].append(r["F"]["tt_own"])
teammean={t:statistics.mean(v) for t,v in tt_by_team.items()}
CONST=statistics.mean([v for vs in tt_by_team.values() for v in vs])
print("league mean posted team_total = %.2f"%CONST)

rows=[r for r in sub if r["F"]["line_gap"] is not None and r["medgap"] is not None]
for r in rows:
    hm=r["hmshare"]; tt=r["F"]["tt_own"]; tm_mean=teammean[r["tm"]]
    r["lg_full"]=tt*hm-r["line"]           # uses tonight's team total
    r["lg_const"]=CONST*hm-r["line"]       # SAME estimator, constant scale (no game info at all)
    r["lg_team"]=tm_mean*hm-r["line"]      # team level only, still no tonight info
    r["tt_dev"]=tt-tm_mean                 # tonight-specific component
    r["lg_delta"]=(tt-tm_mean)*hm          # what the team total ADDS to the projection

print("\n### D. DECOMPOSITION - does TONIGHT'S team_total add anything to the share projection? ###")
print(f"{'estimator':<38} {'rho_zres':>9} {'p':>7} {'rho_overwon':>12} {'p':>7}")
for nm in ["medgap","lg_full","lg_const","lg_team","lg_delta","tt_dev"]:
    xf=(lambda k: (lambda r: r[k]))(nm)
    a=blockperm(rows,xf,lambda r:r["zres"],2000,"player")
    b=blockperm(rows,xf,lambda r:r["over_won"],2000,"player")
    print(f"{nm:<38} {a[0]:>+9.4f} {a[1]:>7.4f} {b[0]:>+12.4f} {b[1]:>7.4f}")
def partial(rows,akey,bkey,ykey,lvl="player"):
    a=rankdata([r[akey] for r in rows]); b=rankdata([r[bkey] for r in rows])
    a=a-a.mean(); b=b-b.mean(); beta=(a*b).sum()/(a*a).sum(); res=b-beta*a
    for r,v in zip(rows,res): r["_p"]=float(v)
    return blockperm(rows,lambda r:r["_p"],lambda r:r[ykey],2000,lvl)
print("\n  partial rho(lg_full | lg_const, zres)  = %+.4f p=%.4f   <- is tonight's total adding value?"%partial(rows,"lg_const","lg_full","zres"))
print("  partial rho(lg_const | lg_full, zres)  = %+.4f p=%.4f"%partial(rows,"lg_full","lg_const","zres"))
print("  rho(lg_full, lg_const) = %+.3f"%sp([r["lg_full"] for r in rows],[r["lg_const"] for r in rows]))
print("  partial rho(lg_const | medgap, zres)   = %+.4f p=%.4f"%partial(rows,"medgap","lg_const","zres"))
print("  partial rho(medgap | lg_const, zres)   = %+.4f p=%.4f"%partial(rows,"lg_const","medgap","zres"))
pickle.dump(dict(sub=sub,ms=ms,rows=rows,CONST=CONST,teammean=teammean),open(os.path.join(D,"gm_sub3.pkl"),"wb"))
