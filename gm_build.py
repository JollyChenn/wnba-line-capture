import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])

def mainrow(rs):
    """pick the row whose two prices are closest to even -> the main (non-alternate) line"""
    best=None; bd=9e9
    for r in rs:
        pr=(r.get("prices") or "").split(",")
        if len(pr)<2: continue
        a,b=am(pr[0]),am(pr[1])
        if a is None or b is None: continue
        d=abs(a-b)
        if d<bd: bd=d; best=r
    return best

# ---------- Pinnacle game markets: full snapshot series per matchup ----------
rows=load("gamelines.csv")
snap=collections.defaultdict(lambda: collections.defaultdict(list))
meta={}
for r in rows:
    mid=r.get("matchup_id"); cap=ts(r.get("captured_utc"))
    if not cap: continue
    snap[(mid,cap)][r.get("type")].append(r)
    tn=(r.get("teams") or "").split("|")
    if len(tn)==2: meta[mid]=(ts((r.get("start") or "")+"Z" if not (r.get("start") or "").endswith("Z") else r.get("start")), tn[0].strip(), tn[1].strip())

# matchup_id -> (home_abbr, away_abbr, tip)  by team-pair + nearest tip
pair_games=collections.defaultdict(list)
for gid,(dt,tp,hm,aw) in gmeta.items(): pair_games[tuple(sorted((hm,aw)))].append((tp,hm,aw,dt))
mid2game={}
for mid,(st,t0,t1) in meta.items():
    a0,a1=FULL.get(t0,""),FULL.get(t1,"")
    if not a0 or not a1 or st is None: continue
    cands=pair_games.get(tuple(sorted((a0,a1))),[])
    best=None;bd=9e9
    for tp,hm,aw,dt in cands:
        d=abs((tp-st).total_seconds())
        if d<bd: bd=d; best=(tp,hm,aw,dt)
    if best and bd<=36*3600: mid2game[mid]=best+(a0,a1)   # (tip,home,away,date,teams0,teams1)
print(f"matchups {len(meta)} joined to games {len(mid2game)}")

# series[(tip,home)] = sorted list of (cap, dict)
series=collections.defaultdict(list)
for (mid,cap),v in snap.items():
    if mid not in mid2game: continue
    tp,hm,aw,dt,t0,t1=mid2game[mid]
    s={}
    mr=mainrow(v.get("total",[]))
    if mr is not None: s["tot"]=f(mr.get("points"))
    mr=mainrow(v.get("spread",[]))
    if mr is not None: s["spr_home"]=f(mr.get("points"))   # home spread (neg = home favoured)
    if v.get("moneyline"):
        pr=(v["moneyline"][0].get("prices") or "").split(",")
        if len(pr)>=2:
            a,b=am(pr[0]),am(pr[1])
            if a is not None and b is not None and a+b>0: s["ml_home"]=a/(a+b)
    tth=mainrow([r for r in v.get("team_total",[]) if r.get("side")=="home"])
    tta=mainrow([r for r in v.get("team_total",[]) if r.get("side")=="away"])
    if tth is not None: s["tt_home"]=f(tth.get("points"))
    if tta is not None: s["tt_away"]=f(tta.get("points"))
    # teams[0] is home per recon; verify against join
    if t0!=hm:
        # flip home/away oriented fields
        if "spr_home" in s: s["spr_home"]=-s["spr_home"]
        if "ml_home" in s: s["ml_home"]=1-s["ml_home"]
        s["tt_home"],s["tt_away"]=s.get("tt_away"),s.get("tt_home")
        if s["tt_home"] is None: s.pop("tt_home")
        if s["tt_away"] is None: s.pop("tt_away")
    if s: series[(tp,hm,aw)].append((cap,s))
for v in series.values(): v.sort(key=lambda x:x[0])
print("games with pinnacle series:",len(series))
def asof(key, when):
    """latest known value of each field at or before `when`"""
    out={}
    for cap,s in series.get(key,[]):
        if cap>when: break
        out.update(s)
    return out

# ---------- team points per game (for historical share) ----------
teampts={}
for g in load("data/games_2026.csv"):
    hs,as_=f(g.get("home_score")),f(g.get("away_score"))
    t=ts(g.get("tip"))
    if hs is None or as_ is None or t is None: continue
    teampts[(g.get("home"),t)]=hs; teampts[(g.get("away"),t)]=as_

# ---------- attach to board ----------
OPPT={}
for gid,(d2,t2,hm,aw) in gmeta.items():
    OPPT[(hm,t2)]=aw; OPPT[(aw,t2)]=hm
HOME={}
for gid,(d2,t2,hm,aw) in gmeta.items(): HOME[(hm,t2)]=True; HOME[(aw,t2)]=False

R=[]
for r in B:
    pl,mk,gt,tm=r["pl"],r["mk"],r["gt"],r["tm"]
    sd=side.get((pl,mk,gt),{})
    if "Over" not in sd: continue
    pt=sd["Over"][0]
    opp=OPPT.get((tm,gt))
    if opp is None: continue
    hm = tm if HOME.get((tm,gt)) else opp
    aw = opp if HOME.get((tm,gt)) else tm
    key=(gt,hm,aw)
    a=asof(key,pt); cl=asof(key,gt)
    def orient(d):
        o={}
        if d.get("tot") is not None: o["tot"]=d["tot"]
        if d.get("spr_home") is not None:
            o["spr"]= d["spr_home"] if tm==hm else -d["spr_home"]   # her team's spread, neg = favoured
        if d.get("ml_home") is not None:
            o["mlp"]= d["ml_home"] if tm==hm else 1-d["ml_home"]
        if d.get("tt_home") is not None and d.get("tt_away") is not None:
            o["tt_own"]= d["tt_home"] if tm==hm else d["tt_away"]
            o["tt_opp"]= d["tt_away"] if tm==hm else d["tt_home"]
        return o
    A=orient(a); C=orient(cl)
    # historical points share (team-filtered, current team only, strictly prior)
    prior=[x for x in hist.get(pl,[]) if x["tip"]<gt and x["tm"]==tm]
    shs=[x["pts"]/teampts[(tm,x["tip"])] for x in prior if teampts.get((tm,x["tip"]))]
    # generalized share for the bet's own market: her market value / team pts
    mshs=[x[mk]/teampts[(tm,x["tip"])] for x in prior if teampts.get((tm,x["tip"]))]
    rr=dict(r); rr["pt"]=pt; rr["opp"]=opp; rr["home"]=HOME.get((tm,gt))
    rr["actual"]=pgrow[(pl,gt)][mk]; rr["resid"]=rr["actual"]-r["line"]
    rr["teampts_actual"]=teampts.get((tm,gt)); rr["opppts_actual"]=teampts.get((opp,gt))
    for k,v in A.items(): rr["a_"+k]=v
    for k,v in C.items(): rr["c_"+k]=v
    rr["nshare"]=len(shs)
    rr["hshare"]=statistics.median(shs) if len(shs)>=5 else None
    rr["hmshare"]=statistics.median(mshs) if len(mshs)>=5 else None
    R.append(rr)
print("board rows with opp/timing:",len(R))
for k in ("a_tot","a_spr","a_mlp","a_tt_own","c_tot","c_tt_own","hshare","hmshare"):
    print(f"   {k:<10} {sum(1 for x in R if x.get(k) is not None):>5}")

import pickle
pickle.dump(R, open(os.path.join(D,"gm_rows.pkl"),"wb"))
print("saved gm_rows.pkl")
