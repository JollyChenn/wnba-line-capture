import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])

print("games in gmeta:", len(gmeta))
# 1. Pinnacle total series per game
tot_series = collections.defaultdict(list)
spr_series = collections.defaultdict(list)
ml_series  = collections.defaultdict(list)
def keyfor(teams, start):
    tm = (teams or "").split("|")
    if len(tm)!=2: return None
    ab = tuple(sorted(FULL.get(t.strip(),"") for t in tm))
    if "" in ab: return None
    return ((start or "")[:10], ab)
for r in load("gamelines.csv"):
    k = keyfor(r.get("teams"), r.get("start"))
    if not k: continue
    cap = ts(r.get("captured_utc")); pts = f(r.get("points"))
    if not cap: continue
    t_ = r.get("type"); pr = (r.get("prices") or "").split(",")
    if t_=="total" and pts is not None: tot_series[k].append((cap,pts, am(pr[0]) if pr and pr[0] else None))
    elif t_=="spread" and pts is not None: spr_series[k].append((cap,pts, am(pr[0]) if pr and pr[0] else None))
    elif t_=="moneyline":
        h = am(pr[0]) if pr and pr[0] else None
        if h is not None: ml_series[k].append((cap,h,None))
print("pinn total games:", len(tot_series), " spread games:", len(spr_series), " ml games:", len(ml_series))
n = [len(v) for v in tot_series.values()]
print("captures per game total: median", statistics.median(n), "mean", round(statistics.mean(n),1), "min",min(n),"max",max(n))

# map gmeta games to key
g2k = {}
for gid,(dt,tp,hm,aw) in gmeta.items():
    g2k[gid] = (dt[:4]+"-"+dt[4:6]+"-"+dt[6:8] if len(dt)==8 else dt, tuple(sorted((hm,aw))))
sample = list(g2k.values())[:5]
print("sample g2k", sample)
print("sample tot key", list(tot_series)[:3])
hit = sum(1 for k in g2k.values() if k in tot_series)
print("gmeta games with pinn total series:", hit, "/", len(g2k))
