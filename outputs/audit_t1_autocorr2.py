# Part 2: liveness / frozen-quote / estimand-sensitivity attack
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(D)
_src = open(os.path.join(D,"mega_sweep.py"),encoding="utf-8").read().split('print(f"{len(B)} two-sided board quotes')[0]
_src = _src.replace('D = os.path.dirname(os.path.abspath(__file__))','pass')
exec(_src)
D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

L=load("live_lines.csv")
wins=[(g,t[1],t[1]+datetime.timedelta(hours=3),{t[2],t[3]}) for g,t in gmeta.items()]
def abbr(x): x=(x or "").strip(); return FULL.get(x,x)
def mid(s):
    p=s.split(",")
    if len(p)!=2: return None
    a,b=am(p[0]),am(p[1])
    return a/(a+b) if a and b else None
rows=[]
for r in L:
    t=ts(r.get("ts"))
    if not t or str(r.get("alt"))!="0": continue
    tm=[abbr(z) for z in (r.get("teams") or "").split("|")]
    if len(tm)!=2: continue
    for g,tp,en,s in wins:
        if set(tm)==s and tp<=t<=en:
            rows.append(dict(gid=g,tip=tp,t=t,type=r["type"],side=r.get("side") or "",
                             pts=f(r.get("points")),m=mid(r.get("prices") or ""),
                             el=(t-tp).total_seconds()/60)); break
S=collections.defaultdict(list)
for x in sorted(rows,key=lambda z:z['t']):
    if x['m'] is not None: S[(x['gid'],x['type'],x['side'])].append(x)
S={k:v for k,v in S.items() if len(v)>=25}
print("series",len(S),"obs",sum(len(v) for v in S.values()),"games",len(set(k[0] for k in S)))

# 1. LIVENESS: does the total line actually decay in-play? does ML mid actually swing?
print("\n--- LIVENESS per game (main total & moneyline) ---")
print(f"{'game':<12}{'tot n':>6}{'tot first':>10}{'tot last':>10}{'tot rng':>9}{'ML rng':>8}{'ML moves':>10}{'span m':>8}")
for g in sorted(set(k[0] for k in S)):
    tv=[x for k,v in S.items() if k[0]==g and k[1]=="total" for x in v]
    ml=[x for k,v in S.items() if k[0]==g and k[1]=="moneyline" for x in v]
    if not tv or not ml: continue
    tp_=[x['pts'] for x in tv if x['pts'] is not None]
    mm=[x['m'] for x in ml]
    mv=sum(1 for i in range(1,len(ml)) if abs(ml[i]['m']-ml[i-1]['m'])>1e-9)
    span=max(x['el'] for x in tv)-min(x['el'] for x in tv)
    print(f"{g:<12}{len(tv):>6}{tp_[0]:>10.1f}{tp_[-1]:>10.1f}{max(tp_)-min(tp_):>9.1f}"
          f"{max(mm)-min(mm):>8.3f}{mv:>10}{span:>8.0f}")

# 2. frozen-quote concentration by elapsed-minute bucket
print("\n--- change rate by elapsed minute bucket (all main series) ---")
buck=collections.defaultdict(lambda:[0,0])
for k,v in S.items():
    for i in range(1,len(v)):
        b=int(v[i]['el']//15)*15
        buck[b][1]+=1
        if abs(v[i]['m']-v[i-1]['m'])>1e-9 or v[i]['pts']!=v[i-1]['pts']: buck[b][0]+=1
for b in sorted(buck):
    c,n=buck[b]
    print(f"  t+{b:>3}-{b+15:<3} min  changed {c:>5}/{n:<5} = {c/n:.3f}")

# 3. estimand sensitivity of rho and deff: price-mid vs LINE (points) vs raw american
def rho_lag(vs,lag,key):
    num=den=0.0
    for v in vs:
        xs=[x[key] for x in v if x[key] is not None]
        if len(xs)<=lag+2: continue
        m=statistics.mean(xs); d=[x-m for x in xs]
        num+=sum(d[i]*d[i+lag] for i in range(len(d)-lag)); den+=sum(x*x for x in d)
    return num/den if den else float('nan')
def deff(byg,key,B=2000):
    gs=list(byg); allx=[x[key] for g in gs for v in byg[g] for x in v if x[key] is not None]
    N=len(allx); naive=statistics.pstdev(allx)/math.sqrt(N)
    ms=[]
    for _ in range(B):
        s=[]
        for _ in gs:
            g=random.choice(gs); s.extend(x[key] for v in byg[g] for x in v if x[key] is not None)
        ms.append(sum(s)/len(s))
    d=(statistics.pstdev(ms)/naive)**2
    return N,d,N/d
print("\n--- rho / design effect BY ESTIMAND ---")
for key,lab in (("m","vig-free prob"),("pts","line level (points)")):
    print(f"  [{lab}]")
    print(f"   {'market':<12}{'r1':>7}{'r2':>7}{'r5':>7}{'r10':>7}{'r20':>7}{'N':>7}{'deff':>8}{'n_eff':>8}")
    for mk in ("moneyline","spread","team_total","total"):
        vs=[v for k,v in S.items() if k[1]==mk]
        if key=="pts" and mk=="moneyline": print(f"   {mk:<12}   (no line)"); continue
        byg=collections.defaultdict(list)
        for k,v in S.items():
            if k[1]==mk: byg[k[0]].append(v)
        N,d,ne=deff(byg,key)
        print(f"   {mk:<12}"+"".join(f"{rho_lag(vs,l,key):>7.3f}" for l in (1,2,5,10,20))+
              f"{N:>7}{d:>8.1f}{ne:>8.1f}")

# 4. cross-market: LEVEL correlation (their likely method) vs CHANGE correlation (correct)
print("\n--- cross-market: level-corr (mixed units) vs tick-change-corr ---")
def grab(mk,key):
    o=collections.defaultdict(dict)
    for k,v in S.items():
        if k[1]!=mk: continue
        for x in v:
            if x[key] is not None: o[k[0]][x['t']]=x[key]
    return o
def corr(xs,ys):
    if len(xs)<30: return None
    mx,my=statistics.mean(xs),statistics.mean(ys)
    sx=math.sqrt(sum((a-mx)**2 for a in xs)); sy=math.sqrt(sum((b-my)**2 for b in ys))
    return sum((xs[i]-mx)*(ys[i]-my) for i in range(len(xs)))/(sx*sy) if sx and sy else None
pairs=[("spread","pts","moneyline","m"),("spread","m","moneyline","m"),
       ("total","pts","team_total","pts"),("total","m","team_total","m"),
       ("total","pts","spread","pts"),("total","m","spread","m")]
for a,ka,b,kb in pairs:
    A,B_=grab(a,ka),grab(b,kb)
    lx=[];ly=[];dx=[];dy=[]
    for g in set(A)&set(B_):
        T=sorted(set(A[g])&set(B_[g]))
        for i,t in enumerate(T):
            lx.append(A[g][t]); ly.append(B_[g][t])
            if i: dx.append(A[g][T[i]]-A[g][T[i-1]]); dy.append(B_[g][T[i]]-B_[g][T[i-1]])
    cl=corr(lx,ly); cd=corr(dx,dy)
    print(f"  {a}.{ka:<4} vs {b}.{kb:<4}  level {('%.3f'%cl) if cl is not None else 'na':>7}"
          f"   tick-change {('%.3f'%cd) if cd is not None else 'na':>7}   n {len(lx)}")
