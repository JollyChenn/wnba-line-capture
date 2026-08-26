# gm_scout.py - can we run the sharp-divergence structure on GAME markets?
import csv, os, sys, math, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
# 1xbet game lines
xb=collections.defaultdict(list)
for r in load("xbet_gamelines.csv"):
    t=ts(r.get("captured_utc")); tm=(r.get("teams") or "").split("|")
    if not t or len(tm)!=2: continue
    ab=tuple(sorted(FULL.get(x.strip(),"") for x in tm))
    if "" in ab: continue
    xb[(ab,r.get("type"))].append((t,f(r.get("points")),f(r.get("p1")),f(r.get("p2")),r.get("start")))
for v in xb.values(): v.sort(key=lambda x:x[0])
print(f"1xbet game-line rows grouped: {len(xb)} (teampair,type) keys")
print("  types:", collections.Counter(k[1] for k in xb).most_common())
# match to games with final scores
res={}
for g in load("data/games_2026.csv"):
    hs,as_=f(g.get("home_score")),f(g.get("away_score"))
    t=ts(g.get("tip"))
    if hs is None or as_ is None or not t: continue
    ab=tuple(sorted((g["home"],g["away"])))
    res[(ab,g.get("date"))]=(g["game_id"],t,g["home"],g["away"],hs,as_)
print(f"finished games with scores: {len(res)}")
both=collections.Counter()
for (ab,d),(gid,tip,hm,aw,hs,as_) in res.items():
    p=GM.get((d,ab),{})
    hasP={k for k in ("tot","spr","ml") if k in p}
    hasX=set()
    for ty,key in (("total","tot"),("spread","spr"),("moneyline","ml")):
        v=[x for x in xb.get((ab,ty),[]) if x[0]<tip]
        if v: hasX.add(key)
    for k in ("tot","spr","ml"):
        if k in hasP and k in hasX: both[k]+=1
        elif k in hasP: both[k+"_pinn_only"]+=1
        elif k in hasX: both[k+"_xbet_only"]+=1
print("\nGAMES WITH BOTH BOOKS PRE-GAME:")
for k in ("tot","spr","ml"):
    print(f"  {k:<4} both={both[k]:<4} pinn-only={both[k+'_pinn_only']:<4} xbet-only={both[k+'_xbet_only']}")
