import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
exec(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

G=load("data/games_2026.csv"); wins=[]
for r in G:
    t=ts(r["tip"])
    if t: wins.append((r["game_id"],t,t+datetime.timedelta(minutes=150),r["home"],r["away"]))
def abbrs(s): return [FULL.get(n.strip(),n.strip()) for n in (s or "").split("|")]
main=[]
for r in load("live_lines.csv"):
    if r["alt"]!="0": continue
    t=ts(r["ts"]);
    if not t: continue
    ab=abbrs(r["teams"])
    if len(ab)!=2: continue
    for gid,a,b,h,aw in wins:
        if a<=t<=b and set(ab)=={h,aw}:
            r["_gid"]=gid; r["_t"]=t; main.append(r); break
S=collections.defaultdict(list)
for r in sorted(main,key=lambda x:x["_t"]): S[(r["_gid"],r["type"],r["side"] or "")].append(r)
KEPT={k:v for k,v in S.items() if len(v)>=25}

def am2(r):
    a,b=(r["prices"] or ",").split(",")[:2]
    return am(a),am(b)
def vigfree(r):
    pa,pb=am2(r)
    if pa is None or pb is None or pa+pb==0: return None
    return pa/(pa+pb)

# ---------- 1. DESIGN EFFECT: game-block bootstrap vs iid, per market ----------
print("=== DESIGN EFFECT: 2000-iter game-block bootstrap, statistic = market mean (vig-free prob) ===")
print("claim: total 52x (n_eff 22.5) | spread 56x (20.7) | team_total 60x (37.6) | moneyline 45x (23.0)\n")
B=2000
res={}
for mk in ["total","spread","team_total","moneyline"]:
    bygame=collections.defaultdict(list)
    for k,v in KEPT.items():
        if k[1]!=mk: continue
        for r in v:
            x=vigfree(r)
            if x is not None: bygame[k[0]].append(x)
    games=sorted(bygame); allx=[x for g in games for x in bygame[g]]
    n=len(allx); mu=statistics.fmean(allx); sd=statistics.pstdev(allx)
    var_iid=sd*sd/n
    means=[]
    for _ in range(B):
        samp=[random.choice(games) for _ in games]
        xs=[x for g in samp for x in bygame[g]]
        means.append(statistics.fmean(xs))
    var_bl=statistics.pvariance(means)
    deff=var_bl/var_iid if var_iid else float("nan")
    res[mk]=(n,len(games),deff,n/deff)
    print(f"  {mk:11s} obs={n:5d} games={len(games):2d}  deff={deff:6.1f}x  n_eff={n/deff:6.1f}")

# ---------- 2. AR(1) design effect ----------
print("\n=== AR(1) deflation (1+phi)/(1-phi), pooled within-series lag-1 ===")
for mk in ["total","spread","team_total","moneyline"]:
    num=den=0.0
    for k,v in KEPT.items():
        if k[1]!=mk: continue
        xs=[vigfree(r) for r in v]; xs=[x for x in xs if x is not None]
        if len(xs)<25: continue
        m=statistics.fmean(xs); d=[x-m for x in xs]
        num+=sum(d[i]*d[i+1] for i in range(len(d)-1)); den+=sum(x*x for x in d)
    phi=num/den
    print(f"  {mk:11s} phi={phi:.3f}  AR1 deff={(1+phi)/(1-phi):5.1f}x")

# ---------- 3. CROSS-MARKET correlation of tick-to-tick changes ----------
print("\n=== cross-market corr of tick-to-tick CHANGES (claim: spd/ml -0.917, tot/tt +0.743, tot/spd ~0) ===")
# align by (gid, ts)
byslot=collections.defaultdict(dict)
for k,v in KEPT.items():
    gid,mk,sd=k
    for r in v:
        x=vigfree(r)
        if x is None: continue
        nm = mk if sd=="" else mk+"_"+sd
        byslot[(gid,r["ts"])][nm]=x
def series_of(gid,nm):
    rows=sorted([(t,d[nm]) for (g,t),d in byslot.items() if g==gid and nm in d])
    return rows
def corr(a,b):
    if len(a)<3: return float("nan")
    ma,mb=statistics.fmean(a),statistics.fmean(b)
    na=sum((x-ma)**2 for x in a)**.5; nb=sum((y-mb)**2 for y in b)**.5
    if na==0 or nb==0: return float("nan")
    return sum((x-ma)*(y-mb) for x,y in zip(a,b))/(na*nb)
pairs=[("spread","moneyline"),("total","team_total_home"),("total","spread"),("total","moneyline"),("team_total_home","team_total_away")]
gids=sorted(set(k[0] for k in KEPT))
for p,q in pairs:
    da=[];db=[]
    for g in gids:
        A=dict(series_of(g,p)); Bq=dict(series_of(g,q))
        common=sorted(set(A)&set(Bq))
        for i in range(1,len(common)):
            da.append(A[common[i]]-A[common[i-1]]); db.append(Bq[common[i]]-Bq[common[i-1]])
    print(f"  {p:17s} vs {q:17s} n={len(da):5d} rho_delta={corr(da,db):+.3f}")
