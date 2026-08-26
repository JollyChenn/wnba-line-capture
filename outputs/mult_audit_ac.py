import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---- build game windows from games_2026.csv ----
G = load("data/games_2026.csv")
wins=[]
for r in G:
    t = ts(r["tip"])
    if not t: continue
    wins.append((r["game_id"], t, t+datetime.timedelta(minutes=150), r["home"], r["away"]))
print("games in schedule:", len(wins))

LL = load("live_lines.csv")
print("live_lines rows:", len(LL))

# map teams string -> abbrs
def abbrs(teamstr):
    out=[]
    for nm in (teamstr or "").split("|"):
        out.append(FULL.get(nm.strip(), nm.strip()))
    return out

inplay=[]
altc=collections.Counter()
for r in LL:
    t = ts(r["ts"])
    if not t: continue
    ab = abbrs(r["teams"])
    if len(ab)!=2: continue
    hit=None
    for gid,a,b,h,aw in wins:
        if a<=t<=b and set(ab)=={h,aw}:
            hit=gid; break
    if hit:
        r["_gid"]=hit; r["_t"]=t
        inplay.append(r); altc[r["alt"]]+=1
print("in-play rows:", len(inplay), "alt split:", dict(altc))
print("distinct in-play games:", len(set(r["_gid"] for r in inplay)))
main=[r for r in inplay if r["alt"]=="0"]
print("main-line in-play rows:", len(main), "games:", len(set(r["_gid"] for r in main)))
print("by market:", collections.Counter(r["type"] for r in main))

print("\n--- side values per market (main, in-play) ---")
for mk in ["moneyline","spread","total","team_total"]:
    print(mk, collections.Counter((r["side"] or "") for r in main if r["type"]==mk))

# candidate series keys
def keys(r):
    return (r["_gid"], r["type"], r["side"] or "")
S=collections.defaultdict(list)
for r in sorted(main, key=lambda x:x["_t"]):
    S[keys(r)].append(r)
print("\nseries (gid,market,side):", len(S))
for mn in (1,25):
    kept={k:v for k,v in S.items() if len(v)>=mn}
    print(f"  min_obs>={mn}: series={len(kept)} obs={sum(len(v) for v in kept.values())} games={len(set(k[0] for k in kept))}")
ln=[len(v) for v in S.values()]
print("  series length quantiles:", sorted(ln)[:5], "med", statistics.median(ln), "max", max(ln))

def probs(r):
    a,b = (r["prices"] or ",").split(",")[:2]
    pa,pb = am(a), am(b)
    return pa,pb

def val(r, mode):
    if mode=="points":
        return f(r["points"])
    pa,pb = probs(r)
    if pa is None: return None
    if mode=="p1": return pa
    if mode=="vigfree":
        if pb is None: return None
        s=pa+pb
        return pa/s if s else None
    if mode=="composite":
        pt=f(r["points"])
        if pt is None or pb is None: return None
        s=pa+pb
        return pt + 0.0 if s==0 else pt + (pa/s-0.5)*4.0
    return None

KEPT={k:v for k,v in S.items() if len(v)>=25}
print("\nkept obs by market:", collections.Counter(k[1] for k in KEPT for _ in KEPT[k]))

def acf_pooled(series_list, lags):
    out={}
    for L in lags:
        num=0.0; den=0.0
        for xs in series_list:
            if len(xs)<=L+2: continue
            m=statistics.fmean(xs)
            d=[x-m for x in xs]
            num+=sum(d[i]*d[i+L] for i in range(len(d)-L))
            den+=sum(x*x for x in d)
        out[L]= num/den if den else float("nan")
    return out

LAGS=[1,2,5,10,20]
print("\n=== ACF by market, several value definitions (within-series demean, pooled) ===")
for mode in ["points","p1","vigfree","composite"]:
    print(f"\n-- value = {mode} --")
    for mk in ["total","spread","team_total","moneyline"]:
        sl=[]
        for k,v in KEPT.items():
            if k[1]!=mk: continue
            xs=[val(r,mode) for r in v]
            xs=[x for x in xs if x is not None]
            if len(xs)>=25: sl.append(xs)
        if not sl: 
            print(f"   {mk:11s} n/a"); continue
        a=acf_pooled(sl,LAGS)
        print(f"   {mk:11s} series={len(sl):3d} obs={sum(len(x) for x in sl):5d} " +
              " ".join(f"r{L}={a[L]:+.3f}" for L in LAGS))
