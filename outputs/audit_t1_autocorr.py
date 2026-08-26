# TRACK 1 hostile audit: in-play autocorrelation / design-effect claim
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__))
D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(D)
_src = open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read().split('print(f"{len(B)} two-sided board quotes')[0]
_src = _src.replace('D = os.path.dirname(os.path.abspath(__file__))', 'pass')
exec(_src)
D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L = load("live_lines.csv")
print("gmeta", len(gmeta))
print("live rows", len(L))

# --- build game windows from schedule (no post-game info used) ---
# map "Away Team|Home Team" style teams string -> candidate games by tip proximity
wins = []   # (gid, tip, end, set(team full names))
inv = {v:k for k,v in FULL.items()}
for gid,(dt,tp,hm,aw) in gmeta.items():
    wins.append((gid, tp, tp+datetime.timedelta(hours=3), {hm,aw}))

def abbr(x):
    x=(x or "").strip()
    return FULL.get(x, x)

rows=[]
for r in L:
    t = ts(r.get("ts"))
    if not t: continue
    tms = [abbr(z) for z in (r.get("teams") or "").split("|")]
    if len(tms)!=2: continue
    hit=None
    for gid,tp,en,tset in wins:
        if set(tms)==tset and tp<=t<=en: hit=(gid,tp); break
    if not hit: continue
    rows.append(dict(gid=hit[0], tip=hit[1], t=t, type=r.get("type"), side=r.get("side") or "",
                     pts=f(r.get("points")), pr=r.get("prices") or "", alt=r.get("alt")))
print("in-play rows matched:", len(rows), "games:", len(set(x['gid'] for x in rows)))
main=[x for x in rows if str(x['alt'])=="0"]
print("main(alt=0):", len(main), "games:", len(set(x['gid'] for x in main)),
      "alt=1:", len(rows)-len(main))

def mid(prstr):
    p=prstr.split(",")
    if len(p)!=2: return None
    a,b = am(p[0]), am(p[1])
    if a is None or b is None: return None
    s=a+b
    return a/s if s>0 else None   # vig-free implied prob of first side

# series key = (gid, type, side); value stream ordered by time
S=collections.defaultdict(list)
for x in sorted(main, key=lambda z:z['t']):
    m=mid(x['pr'])
    if m is None: continue
    S[(x['gid'],x['type'],x['side'])].append((x['t'], m, x['pts']))

S={k:v for k,v in S.items() if len(v)>=25}
tot=sum(len(v) for v in S.values())
print("series>=25:", len(S), "obs:", tot, "games:", len(set(k[0] for k in S)))

# --- stale/duplicate diagnostic (leakage-analogue: frozen quotes) ---
dupmid=dupall=n=0
gaps=[]
for k,v in S.items():
    for i in range(1,len(v)):
        n+=1
        if abs(v[i][1]-v[i-1][1])<1e-12: dupmid+=1
        if abs(v[i][1]-v[i-1][1])<1e-12 and v[i][2]==v[i-1][2]: dupall+=1
        gaps.append((v[i][0]-v[i-1][0]).total_seconds()/60)
print(f"consecutive-identical mid: {dupmid}/{n} = {dupmid/n:.3f}   identical mid+points: {dupall/n:.3f}")
print(f"median gap min {statistics.median(gaps):.2f}  mean {statistics.mean(gaps):.2f}")

# --- within-game autocorrelation of the LEVEL (demeaned per series) ---
def rho_lag(series_list, lag, use_diff=False):
    num=den=0.0
    for v in series_list:
        xs=[p for _,p,_ in v]
        if use_diff: xs=[xs[i]-xs[i-1] for i in range(1,len(xs))]
        if len(xs)<=lag+2: continue
        m=statistics.mean(xs)
        d=[x-m for x in xs]
        num+=sum(d[i]*d[i+lag] for i in range(len(d)-lag))
        den+=sum(x*x for x in d)
    return num/den if den else float('nan')

bym=collections.defaultdict(list)
for k,v in S.items(): bym[k[1]].append(v)
print("\n--- rho of LEVEL (per-series demeaned) ---")
print(f"{'market':<12}{'ser':>5}{'obs':>7}{'gm':>4}" + "".join(f"{('r'+str(l)):>8}" for l in (1,2,5,10,20)))
for mk,vs in sorted(bym.items()):
    g=len(set(k[0] for k in S if k[1]==mk))
    print(f"{mk:<12}{len(vs):>5}{sum(len(v) for v in vs):>7}{g:>4}" +
          "".join(f"{rho_lag(vs,l):>8.3f}" for l in (1,2,5,10,20)))
print("\n--- rho of FIRST DIFFERENCES (tick changes) ---")
for mk,vs in sorted(bym.items()):
    print(f"{mk:<12}" + "".join(f"{rho_lag(vs,l,True):>8.3f}" for l in (1,2,5,10,20)))

# --- design effect: game-block bootstrap vs naive iid, for pooled mean of level ---
def deff(vs_by_game, B=2000):
    games=list(vs_by_game.keys())
    allx=[p for g in games for v in vs_by_game[g] for _,p,_ in v]
    N=len(allx)
    if N<10: return None
    naive=statistics.pstdev(allx)/math.sqrt(N)
    ms=[]
    for _ in range(B):
        s=[]; 
        for _ in games:
            g=random.choice(games)
            s.extend(p for v in vs_by_game[g] for _,p,_ in v)
        if s: ms.append(sum(s)/len(s))
    bs=statistics.pstdev(ms)
    return N, naive, bs, (bs/naive)**2, N/((bs/naive)**2)

print("\n--- design effect (game-block bootstrap, pooled mean of level) ---")
print(f"{'market':<12}{'N':>7}{'games':>7}{'deff':>9}{'n_eff':>9}{'AR1_deff':>10}")
for mk in sorted(bym):
    byg=collections.defaultdict(list)
    for k,v in S.items():
        if k[1]==mk: byg[k[0]].append(v)
    r=deff(byg)
    r1=rho_lag(bym[mk],1)
    ar=(1+r1)/(1-r1)
    print(f"{mk:<12}{r[0]:>7}{len(byg):>7}{r[3]:>9.1f}{r[4]:>9.1f}{ar:>10.1f}")

# --- CONTROL: does the block bootstrap manufacture a design effect on iid data? ---
print("\n--- CONTROL: synthetic, same shapes ---")
for label, gameeff, within_ar in (("iid no game effect",0.0,0.0),
                                  ("game effect only, iid within",1.0,0.0),
                                  ("AR1 .9 within, no game effect",0.0,0.9)):
    byg=collections.defaultdict(list)
    for k,v in S.items():
        if k[1]!="total": continue
        byg[k[0]].append(v)
    syn=collections.defaultdict(list)
    for g,vs in byg.items():
        ge=random.gauss(0,1)*gameeff
        for v in vs:
            x=0.0; out=[]
            for (t,_,pt) in v:
                x=within_ar*x+random.gauss(0,1)*math.sqrt(1-within_ar**2)
                out.append((t, ge+x, pt))
            syn[g].append(out)
    r=deff(syn)
    print(f"{label:<32} deff {r[3]:>7.1f}  n_eff {r[4]:>7.1f}  (games {len(syn)})")

# --- cross-market correlation of tick changes, within game, aligned by timestamp ---
print("\n--- cross-market corr of tick-to-tick changes ---")
def series_map(mk):
    out=collections.defaultdict(dict)
    for k,v in S.items():
        if k[1]!=mk: continue
        for t,p,_ in v: out[k[0]][t]=p
    return out
maps={mk:series_map(mk) for mk in bym}
def xcorr(a,b):
    xs=[];ys=[]
    for g in set(maps[a])&set(maps[b]):
        ts_=sorted(set(maps[a][g])&set(maps[b][g]))
        for i in range(1,len(ts_)):
            xs.append(maps[a][g][ts_[i]]-maps[a][g][ts_[i-1]])
            ys.append(maps[b][g][ts_[i]]-maps[b][g][ts_[i-1]])
    if len(xs)<30: return None,len(xs)
    mx,my=statistics.mean(xs),statistics.mean(ys)
    sx=math.sqrt(sum((x-mx)**2 for x in xs)); sy=math.sqrt(sum((y-my)**2 for y in ys))
    if sx==0 or sy==0: return None,len(xs)
    return sum((xs[i]-mx)*(ys[i]-my) for i in range(len(xs)))/(sx*sy), len(xs)
mks=sorted(bym)
for i in range(len(mks)):
    for j in range(i+1,len(mks)):
        c,nn=xcorr(mks[i],mks[j])
        print(f"{mks[i]:>12} vs {mks[j]:<12} rho {('%.3f'%c) if c is not None else 'na':>8}  n {nn}")
