import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT); os.chdir(ROOT)
__file__ = os.path.join(ROOT, "mega_sweep.py")
exec(open(os.path.join(ROOT, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])

# ---------- build player series ordered by tip ----------
def series(minG):
    S={}
    for pl, rows in hist.items():
        r=sorted(rows, key=lambda x:x["tip"])
        if len(r)>=minG: S[pl]=r
    return S

def stat_lag(S, k=1, demean=True, use_med=True, key="pts"):
    """pooled lag-k slope/corr of residual, optionally demeaned within player"""
    xs=[];ys=[];bl=[]
    for pl,r in S.items():
        v=[x[key] for x in r]
        base=statistics.median(v) if use_med else 0.0
        res=[a-base for a in v]
        if demean:
            m=sum(res)/len(res); res=[a-m for a in res]
        for i in range(len(res)-k):
            xs.append(res[i]); ys.append(res[i+k]); bl.append(pl)
    return xs,ys,bl

def slope_corr(xs,ys):
    n=len(xs); mx=sum(xs)/n; my=sum(ys)/n
    sxy=sum((a-mx)*(b-my) for a,b in zip(xs,ys))
    sxx=sum((a-mx)**2 for a in xs); syy=sum((b-my)**2 for b in ys)
    return sxy/sxx, sxy/math.sqrt(sxx*syy)

print("=== A. REPLICATION SEARCH (which spec gives n=1928 / 159 players / r=+0.190?) ===")
for minG in (2,3,4,5,6,8,10):
    S=series(minG)
    xs,ys,bl=stat_lag(S,1,True,True)
    if not xs: continue
    sl,co=slope_corr(xs,ys)
    xu,yu,_=stat_lag(S,1,False,True)
    slu,cou=slope_corr(xu,yu)
    print(f"  minGames>={minG:2d}  players={len(S):3d}  n={len(xs):4d}  demeaned slope={sl:+.4f} r={co:+.4f} | undemeaned slope={slu:+.4f} r={cou:+.4f}")

# ================== B. THE HALVES SUBSET (what the claim actually used) ==================
HV=list(csv.DictReader(open(os.path.join(ROOT,"data","halves_2026.csv"),encoding="utf-8",errors="replace")))
print(f"\n=== B. halves_2026.csv: rows={len(HV)} games={len(set(r['game_id'] for r in HV))} players={len(set(r['player'] for r in HV))}")
dup=collections.Counter((r["player"],r["game_id"]) for r in HV)
print("   duplicate player-game rows:", sum(1 for k,v in dup.items() if v>1))
# consistency with box
bx={}
for r in load("data/box_2026.csv"):
    bx[( _pl(r["player"]), r["game_id"])]=f(r["pts"])
mis=[(k,v,bx.get(k)) for k,v in ((( _pl(r["player"]),r["game_id"]), f(r["pts"])) for r in HV) if bx.get(k) is not None and abs(bx[k]-v)>0.01]
print(f"   halves pts != box pts on {len(mis)} rows ; halves rows with no box match: "
      f"{sum(1 for r in HV if (_pl(r['player']),r['game_id']) not in bx)}")

def hv_series(minG, field="pts"):
    S=collections.defaultdict(list)
    for r in HV:
        pl=_pl(r["player"]) or r["player"].lower()
        g=r["game_id"]; d=gmeta.get(g,("",r["date"],"",""))
        tip = gmeta[g][1] if g in gmeta else r["date"]
        S[pl].append((tip, f(r[field])))
    out={}
    for pl,v in S.items():
        v=sorted(v)
        if len(v)>=minG: out[pl]=[x[1] for x in v]
    return out

def lagstat(SD,k=1,demean=True):
    xs=[];ys=[];bl=[]
    for pl,v in SD.items():
        base=statistics.median(v); res=[a-base for a in v]
        if demean:
            m=sum(res)/len(res); res=[a-m for a in res]
        for i in range(len(res)-k):
            xs.append(res[i]);ys.append(res[i+k]);bl.append(pl)
    return xs,ys,bl

print("\n   lag-1 on halves-file game pts:")
for minG in (2,3,4,5,6):
    SD=hv_series(minG)
    xs,ys,bl=lagstat(SD,1,True)
    if len(xs)<10: continue
    sl,co=slope_corr(xs,ys)
    xu,yu,_=lagstat(SD,1,False)
    slu,cou=slope_corr(xu,yu)
    print(f"     minG>={minG}: players={len(SD)} n={len(xs)} demeaned slope={sl:+.4f} r={co:+.4f} | undemeaned {slu:+.4f}/{cou:+.4f}")
