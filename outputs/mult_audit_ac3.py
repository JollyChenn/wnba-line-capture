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
    t=ts(r["ts"])
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
    a,b=(r["prices"] or ",").split(",")[:2]; return am(a),am(b)
def vf(r):
    pa,pb=am2(r)
    if pa is None or pb is None or pa+pb==0: return None
    return pa/(pa+pb)
def hyb(r):   # line level where it exists, vig-free price for moneyline
    return f(r["points"]) if r["type"]!="moneyline" else vf(r)

LAGS=[1,2,5,10,20]
def acf(sl,pooled=True):
    out={}
    for L in LAGS:
        if pooled:
            num=den=0.0
            for xs in sl:
                if len(xs)<=L+2: continue
                m=statistics.fmean(xs); d=[x-m for x in xs]
                num+=sum(d[i]*d[i+L] for i in range(len(d)-L)); den+=sum(x*x for x in d)
            out[L]=num/den if den else float("nan")
        else:
            rs=[]
            for xs in sl:
                if len(xs)<=L+2: continue
                m=statistics.fmean(xs); d=[x-m for x in xs]
                den=sum(x*x for x in d)
                if den<=0: continue
                rs.append(sum(d[i]*d[i+L] for i in range(len(d)-L))/den)
            out[L]=statistics.fmean(rs) if rs else float("nan")
    return out

print("CLAIM  r1 .87-.90  r2 .74-.79  r5 .47-.50  r10 .13-.19  r20 -.05..-.18")
for lab,vfun in [("hybrid(points|ml=price)",hyb),("vigfree price",vf)]:
    for pooled in (True,False):
        print(f"\n-- {lab}  pooling={'sum-pooled' if pooled else 'avg-of-series'} --")
        for mk in ["total","spread","team_total","moneyline"]:
            sl=[]
            for k,v in KEPT.items():
                if k[1]!=mk: continue
                xs=[vfun(r) for r in v]; xs=[x for x in xs if x is not None]
                if len(xs)>=25: sl.append(xs)
            if not sl: continue
            a=acf(sl,pooled)
            print(f"   {mk:11s} "+" ".join(f"r{L}={a[L]:+.3f}" for L in LAGS))

print("\n=== game-block bootstrap deff, statistic=mean, value=hybrid(points | ml price) ===")
Bn=2000
for mk in ["total","spread","team_total","moneyline"]:
    bg=collections.defaultdict(list)
    for k,v in KEPT.items():
        if k[1]!=mk: continue
        for r in v:
            x=hyb(r)
            if x is not None: bg[k[0]].append(x)
    games=sorted(bg); allx=[x for g in games for x in bg[g]]
    n=len(allx); sd=statistics.pstdev(allx); vi=sd*sd/n
    ms=[]
    for _ in range(Bn):
        s=[random.choice(games) for _ in games]
        ms.append(statistics.fmean([x for g in s for x in bg[g]]))
    vb=statistics.pvariance(ms); de=vb/vi
    print(f"  {mk:11s} obs={n:5d} games={len(games)} deff={de:6.1f}x n_eff={n/de:6.1f}")

print("\n=== cross-market delta corr, value=hybrid ===")
byslot=collections.defaultdict(dict)
for k,v in KEPT.items():
    gid,mk,sd=k
    nm=mk if sd=="" else mk+"_"+sd
    for r in v:
        x=hyb(r)
        if x is not None: byslot[(gid,r["ts"])][nm]=x
def ser(g,nm): return dict(sorted([(t,d[nm]) for (gg,t),d in byslot.items() if gg==g and nm in d]))
def corr(a,b):
    ma,mb=statistics.fmean(a),statistics.fmean(b)
    na=sum((x-ma)**2 for x in a)**.5; nb=sum((y-mb)**2 for y in b)**.5
    return sum((x-ma)*(y-mb) for x,y in zip(a,b))/(na*nb) if na and nb else float("nan")
gids=sorted(set(k[0] for k in KEPT))
for p,q in [("spread","moneyline"),("total","team_total_home"),("total","spread"),
            ("team_total_home","team_total_away"),("spread","team_total_home")]:
    da=[];db=[]
    for g in gids:
        A=ser(g,p);Bq=ser(g,q);c=sorted(set(A)&set(Bq))
        for i in range(1,len(c)):
            da.append(A[c[i]]-A[c[i-1]]); db.append(Bq[c[i]]-Bq[c[i-1]])
    if len(da)>3: print(f"  {p:17s} vs {q:17s} n={len(da):5d} rho={corr(da,db):+.3f}")
