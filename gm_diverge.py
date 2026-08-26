import os,sys,pickle,math,random,statistics,collections,datetime,csv
import numpy as np
from scipy.stats import rankdata
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
rng=np.random.default_rng(20260826)
D=os.path.dirname(os.path.abspath(__file__))

def load(p):
    fp=os.path.join(D,p)
    return list(csv.DictReader(open(fp,encoding="utf-8",errors="replace"))) if os.path.exists(fp) else []
def f(x):
    try: return float(x)
    except (TypeError,ValueError): return None
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z","+00:00"))
    except Exception: return None
FULL={"Atlanta Dream":"ATL","Chicago Sky":"CHI","Connecticut Sun":"CON","Dallas Wings":"DAL",
      "Golden State Valkyries":"GS","Indiana Fever":"IND","Los Angeles Sparks":"LA",
      "Las Vegas Aces":"LV","Minnesota Lynx":"MIN","New York Liberty":"NY",
      "Phoenix Mercury":"PHX","Portland Fire":"POR","Seattle Storm":"SEA",
      "Toronto Tempo":"TOR","Washington Mystics":"WSH"}
gmeta={}
for g in load("data/games_2026.csv"):
    t=ts(g.get("tip"))
    if t: gmeta[g.get("game_id")]=(g.get("date",""),t,g.get("home"),g.get("away"))

G=pickle.load(open(os.path.join(D,"gm_grid.pkl"),"rb"))
rows=G["rows"]
def gamekey(r): return (r["gt"], r["tm"] if r["home"] else r["opp"], r["opp"] if r["home"] else r["tm"])
def sp(x,y):
    a,b=rankdata(x),rankdata(y); a=a-a.mean(); b=b-b.mean()
    d=np.sqrt((a*a).sum()*(b*b).sum()); return float((a*b).sum()/d) if d else 0.0

xs=collections.defaultdict(list); bad=0
for r in load("xbet_gamelines.csv"):
    tn=(r.get("teams") or "").split("|")
    if len(tn)!=2: continue
    a0,a1=FULL.get(tn[0].strip(),""),FULL.get(tn[1].strip(),"")
    if not a0 or not a1: bad+=1; continue
    cap=ts(r.get("captured_utc")); st=ts(r.get("start")); pts=f(r.get("points"))
    p1,p2=f(r.get("p1")),f(r.get("p2"))
    if not cap or not st: continue
    xs[(a0,a1,st.date())].append((cap,r.get("type"),pts,p1,p2))
print("xbet placeholder/unmapped rows skipped:",bad," distinct xbet game-keys:",len(xs))
key2={}
for gid,(dt,tp,hm,aw) in gmeta.items():
    key2[(hm,aw,tp.date())]=(tp,hm,aw)
    key2[(hm,aw,(tp-datetime.timedelta(hours=6)).date())]=(tp,hm,aw)
X=collections.defaultdict(list); matched=0
for k,v in xs.items():
    if k in key2:
        X[key2[k]].extend(v); matched+=1
    else:
        k2=(k[1],k[0],k[2])
        if k2 in key2:
            tp,hm,aw=key2[k2]
            for cap,ty,pts,p1,p2 in v:
                X[(tp,hm,aw)].append((cap,ty,(-pts if (ty=="spread" and pts is not None) else pts),p2,p1))
            matched+=1
print("xbet game-keys joined:",matched,"-> games",len(X))
for v in X.values(): v.sort(key=lambda z:z[0])
def xasof(key,when):
    out={}
    for cap,ty,pts,p1,p2 in X.get(key,[]):
        if cap>when: break
        if ty=="total" and pts is not None and 130<=pts<=230: out["tot"]=pts
        if ty=="spread" and pts is not None and -30<=pts<=30: out["spr_home"]=pts
        if ty=="moneyline" and p1 and p2:
            a,b=1/p1,1/p2; out["ml_home"]=a/(a+b)
    return out

sub2=[]
for r in rows:
    key=gamekey(r)
    x=xasof(key,r["pt"])
    if "tot" not in x: continue
    pt_spr_home=r["F"]["spr_signed"] if r["home"] else -r["F"]["spr_signed"]
    rr=dict(r); rr["x_tot"]=x["tot"]; rr["d_tot"]=x["tot"]-r["F"]["tot"]; rr["pinn_spr_home"]=pt_spr_home
    if "spr_home" in x:
        rr["x_spr"]=x["spr_home"]; d=x["spr_home"]-pt_spr_home
        rr["d_spr_own"]= d if r["home"] else -d
    sub2.append(rr)
print()
print("### Q4 1xbet-vs-Pinnacle GAME-LINE DIVERGENCE ###")
print("board quotes inside the xbet_gamelines window with both books: n=%d  games=%d"%(
    len(sub2),len(set(gamekey(r) for r in sub2))))
if not sub2: sys.exit()
dt=[r["d_tot"] for r in sub2]
print("  d_tot (xbet - pinn) mean %+.2f median %+.2f sd %.2f  |d|>=1 %.0f%%  |d|>=2 %.0f%%"%(
    statistics.mean(dt),statistics.median(dt),statistics.pstdev(dt),
    100*sum(1 for d in dt if abs(d)>=1)/len(dt),100*sum(1 for d in dt if abs(d)>=2)/len(dt)))
ds=[r["d_spr_own"] for r in sub2 if "d_spr_own" in r]
if ds: print("  d_spr_own mean %+.2f sd %.2f n=%d"%(statistics.mean(ds),statistics.pstdev(ds),len(ds)))
tg={}
for r in sub2:
    k=gamekey(r)
    if k not in tg and r["teampts_actual"] is not None and r["opppts_actual"] is not None:
        tg[k]=(r["F"]["tot"],r["x_tot"],r["teampts_actual"]+r["opppts_actual"])
V=list(tg.values())
if len(V)>=8:
    ep=statistics.mean(abs(a-c) for a,b,c in V); ex=statistics.mean(abs(b-c) for a,b,c in V)
    div=[(a,b,c) for a,b,c in V if abs(b-a)>=0.5]
    hip=sum(1 for a,b,c in div if (b>a)==(c>a))
    print("  GAME SANITY n=%d games: MAE(pinn)=%.2f MAE(xbet)=%.2f ; on %d diverging games the realised total went xbet's way %d"%(
        len(V),ep,ex,len(div),hip))
def blockperm(rr,xf,yf,NP=2000):
    x=np.array([xf(r) for r in rr],float); y=np.array([float(yf(r)) for r in rr],float)
    obs=sp(x,y)
    g=collections.defaultdict(list)
    for i,r in enumerate(rr): g[gamekey(r)].append(i)
    keys=list(g); idxs=[np.array(g[k]) for k in keys]; blocks=[x[i] for i in idxs]
    cnt=0; px=np.empty_like(x)
    for _ in range(NP):
        o=rng.permutation(len(keys))
        for t,s_ in enumerate(o):
            b=blocks[s_]; ii=idxs[t]
            px[ii]=b[:len(ii)] if len(b)>=len(ii) else np.resize(b,len(ii))
        if abs(sp(px,y))>=abs(obs): cnt+=1
    return obs,(cnt+1)/(NP+1),len(keys)
MK=("pra","pr","pts")
for nm,f_,rr in [("d_tot",lambda r:r["d_tot"],sub2),("|d_tot|",lambda r:abs(r["d_tot"]),sub2),
                 ("d_spr_own",lambda r:r["d_spr_own"],[r for r in sub2 if "d_spr_own" in r])]:
    if len(rr)<50: continue
    a=blockperm(rr,f_,lambda r:r["over_won"]); b=blockperm(rr,f_,lambda r:r["zres"])
    print("  rho(%-9s, over_won)=%+.4f p=%.3f   rho(...,zresid)=%+.4f p=%.3f   n=%d games=%d"%(nm,a[0],a[1],b[0],b[1],len(rr),a[2]))

UNIV={"board_OVER":(lambda r:True,"Over"),"board_UNDER":(lambda r:True,"Under"),
      "modelS_OVER":(lambda r: r["mk"] in MK and r.get("starred") is True,"Over")}
DF=["d_tot","abs_d_tot","d_spr_own"]
base={}
for r in sub2:
    g=gamekey(r)
    if g not in base:
        base[g]=(r["d_tot"], (r["x_spr"]-r["pinn_spr_home"]) if "x_spr" in r else None)
def dfeat(r,fn,dmap):
    v=dmap[gamekey(r)]
    if fn=="d_tot": return v[0]
    if fn=="abs_d_tot": return abs(v[0])
    if v[1] is None: return None
    return v[1] if r["home"] else -v[1]
def cellset(dmap):
    out={}
    for un,(filt,sd) in UNIV.items():
        idx=[r for r in sub2 if filt(r)]
        for fn in DF:
            rr=[r for r in idx if dfeat(r,fn,dmap) is not None]
            if len(rr)<90: continue
            vals=sorted(dfeat(r,fn,dmap) for r in rr); n=len(vals)
            q1,q2=vals[n//3],vals[2*n//3]
            bk=collections.defaultdict(list)
            for r in rr:
                v=dfeat(r,fn,dmap); bk[0 if v<=q1 else (1 if v<=q2 else 2)].append(r)
            for b,ii in bk.items():
                if len(ii)<40: continue
                p=0
                for r in ii:
                    w=r["over_won"] if sd=="Over" else (not r["over_won"])
                    od=r["over_od"] if sd=="Over" else r["under_od"]
                    p+=(od-1) if w else -1
                out[(un,fn,b)]=(len(ii),p/len(ii)*100)
    return out
realc=cellset(base)
NP=500; bb=[]
ks=list(base); vs=[base[k] for k in ks]
for _ in range(NP):
    o=rng.permutation(len(ks))
    dm={ks[t]:vs[s] for t,s in enumerate(o)}
    c=cellset(dm)
    if c: bb.append(max(v[1] for v in c.values()))
bb.sort(); ceil=bb[int(0.95*len(bb))] if bb else None
print()
print("  DIVERGENCE GRID: %d cells  noise ceiling (game-relabel, %d perms) p95 best-cell ROI = %+.2f%%"%(len(realc),len(bb),ceil))
for k in sorted(realc,key=lambda k:-realc[k][1]):
    n,v=realc[k]
    print("   %-12s %-10s bin%d n=%4d ROI=%+7.2f%%  %s"%(k[0],k[1],k[2],n,v,"BEATS" if v>ceil else ""))
