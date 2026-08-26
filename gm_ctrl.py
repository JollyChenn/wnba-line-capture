import os,sys,pickle,math,statistics,collections,datetime,csv
import numpy as np
from scipy.stats import rankdata
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
rng=np.random.default_rng(20260826)
D=os.path.dirname(os.path.abspath(__file__))
S3=pickle.load(open(os.path.join(D,"gm_sub3.pkl"),"rb")); rows=S3["rows"]; CONST=S3["CONST"]
def sp(x,y):
    a,b=rankdata(x),rankdata(y); a=a-a.mean(); b=b-b.mean()
    d=np.sqrt((a*a).sum()*(b*b).sum()); return float((a*b).sum()/d) if d else 0.0
def pblock(rr,xf,yf,NP=2000):
    x=np.array([xf(r) for r in rr],float); y=np.array([float(yf(r)) for r in rr],float)
    obs=sp(x,y); g=collections.defaultdict(list)
    for i,r in enumerate(rr): g[r["pl"]].append(i)
    ks=list(g); idxs=[np.array(g[k]) for k in ks]; bl=[x[i] for i in idxs]
    cnt=0; px=np.empty_like(x)
    for _ in range(NP):
        o=rng.permutation(len(ks))
        for t,s_ in enumerate(o):
            b=bl[s_]; ii=idxs[t]
            px[ii]=b[:len(ii)] if len(b)>=len(ii) else np.resize(b,len(ii))
        if abs(sp(px,y))>=abs(obs): cnt+=1
    return obs,(cnt+1)/(NP+1)
# med over ALL prior current-team games (same window as hmshare) - isolates window vs share
import csv as _c
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z","+00:00"))
    except Exception: return None
gmeta={}
for g in _c.DictReader(open(os.path.join(D,"data/games_2026.csv"),encoding="utf-8")):
    t=ts(g.get("tip"))
    if t: gmeta[g["game_id"]]=(g["date"],t,g["home"],g["away"])
pg={}
for r in _c.DictReader(open(os.path.join(D,"data/box_2026.csv"),encoding="utf-8",errors="replace")):
    if r["game_id"] not in gmeta: continue
    dt,tp,hm,aw=gmeta[r["game_id"]]
    p=float(r["pts"] or 0); rb=float(r["reb"] or 0); a=float(r["ast"] or 0)
    pg[(r["player"].lower(),tp)]=dict(tm=r["team"],tip=tp,pts=p,reb=rb,ast=a,pra=p+rb+a,pr=p+rb,pa=p+a,ra=rb+a)
hist=collections.defaultdict(list)
for (pl,tp),v in pg.items(): hist[pl].append(v)
for v in hist.values(): v.sort(key=lambda x:x["tip"])
ok=[]
for r in rows:
    prior=[x for x in hist.get(r["pl"],[]) if x["tip"]<r["gt"] and x["tm"]==r["tm"]]
    if len(prior)<5: continue
    r["med_all"]=statistics.median(x[r["mk"]] for x in prior)-r["line"]
    ok.append(r)
print("control rows:",len(ok))
for nm in ["medgap","med_all","lg_const","lg_full","lg_delta"]:
    o,p=pblock(ok,(lambda k:(lambda r:r[k]))(nm),lambda r:r["zres"])
    print("  rho(%-9s, zresid) = %+.4f p=%.4f"%(nm,o,p))
def partial(rr,ak,bk,yk):
    a=rankdata([r[ak] for r in rr]); b=rankdata([r[bk] for r in rr])
    a=a-a.mean(); b=b-b.mean(); be=(a*b).sum()/(a*a).sum(); res=b-be*a
    for r,v in zip(rr,res): r["_p"]=float(v)
    return pblock(rr,lambda r:r["_p"],lambda r:r[yk])
print("  partial rho(lg_const | med_all, zres) = %+.4f p=%.4f  <- does the SHARE form add over a same-window plain median?"%partial(ok,"med_all","lg_const","zres"))
print("  partial rho(med_all | lg_const, zres) = %+.4f p=%.4f"%partial(ok,"lg_const","med_all","zres"))
print("  rho(med_all, lg_const) = %+.3f"%sp([r["med_all"] for r in ok],[r["lg_const"] for r in ok]))
