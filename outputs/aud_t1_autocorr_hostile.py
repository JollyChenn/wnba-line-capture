# HOSTILE AUDIT of the in-play autocorrelation / n_eff claim (brief s.44). READ-ONLY.
import csv, os, sys, math, datetime, collections, statistics, random
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(777)
R = r"C:\Users\Axioo\wnba-line-capture"
def L(p): return list(csv.DictReader(open(os.path.join(R,p),encoding="utf-8",errors="replace")))
def f(x):
    try: return float(x)
    except (TypeError,ValueError): return None
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z","+00:00"))
    except Exception: return None
def am(p):
    v=f(p)
    return None if v is None else ((-v)/((-v)+100) if v<0 else 100/(v+100))
FULL={"Atlanta Dream":"ATL","Chicago Sky":"CHI","Connecticut Sun":"CON","Dallas Wings":"DAL",
 "Golden State Valkyries":"GS","Indiana Fever":"IND","Los Angeles Sparks":"LA","Las Vegas Aces":"LV",
 "Minnesota Lynx":"MIN","New York Liberty":"NY","Phoenix Mercury":"PHX","Portland Fire":"POR",
 "Seattle Storm":"SEA","Toronto Tempo":"TOR","Washington Mystics":"WSH"}
G=L("data/games_2026.csv")
pair2=collections.defaultdict(list)
for g in G:
    t=ts(g.get("tip"))
    if t: pair2[frozenset((g["home"],g["away"]))].append((t,g["game_id"]))
for k in pair2: pair2[k].sort()

WIN=float(os.environ.get("WIN","4"))*3600
series=collections.defaultdict(dict)
raw=0
for r in L("live_lines.csv"):
    if r.get("alt")!="0": continue
    t=ts(r["ts"]); tm=(r.get("teams") or "").split("|")
    if not t or len(tm)!=2: continue
    key=frozenset(FULL.get(x.strip(),x.strip()) for x in tm)
    best=None
    for tp,gid in pair2.get(key,[]):
        if 0<=(t-tp).total_seconds()<=WIN: best=(tp,gid); break
    if not best: continue
    tp,gid=best
    pr=(r.get("prices") or "").split(",")
    if len(pr)!=2: continue
    if r["type"]=="moneyline":
        a,b=am(pr[0]),am(pr[1])
        if a is None or b is None or (a+b)<=0: continue
        val=a/(a+b)
    else:
        val=f(r.get("points"))
        if val is None: continue
    series[(gid,r["type"],r.get("side",""))][t]=val; raw+=1

def acf(x,k):
    n=len(x)
    if n<=k+3: return None
    m=statistics.mean(x); den=sum((v-m)**2 for v in x)
    if den<=0: return None
    return sum((x[i]-m)*(x[i+k]-m) for i in range(n-k))/den

MK=["total","spread","team_total","moneyline"]
print("== A. Scope reproduction ==")
print("raw in-play alt=0 rows matched to a game: %d ; games: %d" % (raw,len(set(k[0] for k in series))))
sc={}
for typ in MK:
    sc[typ]=[(k,v) for k,v in series.items() if k[1]==typ and len(v)>=25]
tot_obs=sum(len(v) for typ in MK for _,v in sc[typ])
tot_g=len(set(k[0] for typ in MK for k,_ in sc[typ]))
print("series>=25obs: obs=%d games=%d  (claim: 5,642 obs / 20 games)"%(tot_obs,tot_g))
drop0=0; keep=0
for typ in MK:
    for k,d in sc[typ]:
        x=[d[t] for t in sorted(d)]
        if statistics.pstdev(x)==0: drop0+=1
        else: keep+=1
print("series with ZERO variance (silently excluded from rho): %d of %d"%(drop0,drop0+keep))

gaps=[]
for typ in MK:
    for k,d in sc[typ]:
        t=sorted(d); gaps+=[(t[i]-t[i-1]).total_seconds()/60 for i in range(1,len(t))]
gaps.sort()
print("obs gap min: median %.2f  p90 %.2f  mean %.2f"%(statistics.median(gaps),gaps[int(.9*len(gaps))],statistics.mean(gaps)))
print("=> lag-20 obs ~= %.1f min median wall clock (claim says 20-25 min)"%(20*statistics.median(gaps)))
print("")

print("== B. Independent recomputation of rho(k) ==")
print("mkt        nser  medobs  totobs   rho1    rho2    rho5   rho10   rho20")
ROWS={}
for typ in MK:
    ser=sc[typ]; lag={}
    for k in (1,2,5,10,20):
        vals=[]
        for key,d in ser:
            a=acf([d[t] for t in sorted(d)],k)
            if a is not None: vals.append((key[0],a))
        lag[k]=vals
    lens=[len(d) for _,d in ser]
    ROWS[typ]=(ser,lag,lens)
    m=lambda k: statistics.mean([v for _,v in lag[k]]) if lag[k] else float("nan")
    print("%-10s %4d %7.0f %7d  %6.3f  %6.3f  %6.3f  %6.3f  %6.3f"%(typ,len(ser),statistics.median(lens),sum(lens),m(1),m(2),m(5),m(10),m(20)))
print("")

print("== C. Concentration: drop top-2 / bottom-2 contributing GAMES ==")
for typ in MK:
    ser,lag,_=ROWS[typ]
    for k in (1,10):
        byg=collections.defaultdict(list)
        for gid,a in lag[k]: byg[gid].append(a)
        gm={g:statistics.mean(v) for g,v in byg.items()}
        if len(gm)<5: continue
        full=statistics.mean(list(gm.values()))
        order=sorted(gm,key=lambda g:-gm[g])
        rest=[v for g,v in gm.items() if g not in order[:2]]
        rest2=[v for g,v in gm.items() if g not in order[-2:]]
        print("  %-10s lag%-2d ngames=%2d full=%+.3f droptop2=%+.3f dropbot2=%+.3f range[%.3f,%.3f]"
              %(typ,k,len(gm),full,statistics.mean(rest),statistics.mean(rest2),min(gm.values()),max(gm.values())))
print("")

print("== D. Game-block bootstrap design effect (4000 iters, fresh seed 777) ==")
BB=4000
print("mkt        games   naiveSE   bootSE     DE   n_eff    ICC  DE_pred")
DEs={}
for typ in MK:
    ser=sc[typ]
    byg=collections.defaultdict(list)
    for key,d in ser: byg[key[0]]+=[d[t] for t in sorted(d)]
    gl=list(byg.values()); allv=[v for g in gl for v in g]; n=len(allv)
    naive=statistics.pstdev(allv)/math.sqrt(n)
    means=[]
    for _ in range(BB):
        s=0.0;c=0
        for _ in range(len(gl)):
            g=random.choice(gl); s+=sum(g); c+=len(g)
        means.append(s/c)
    boot=statistics.pstdev(means)
    de=(boot/naive)**2 if naive>0 else float("nan")
    DEs[typ]=de
    gmean={i:statistics.mean(g) for i,g in enumerate(gl)}
    grand=statistics.mean(allv)
    ssb=sum(len(g)*(statistics.mean(g)-grand)**2 for g in gl)
    ssw=sum((v-statistics.mean(g))**2 for g in gl for v in g)
    kbar=n/len(gl); msb=ssb/(len(gl)-1); msw=ssw/(n-len(gl))
    icc=max(0.0,(msb-msw)/(msb+(kbar-1)*msw))
    print("%-10s %5d  %8.4f  %8.4f  %5.0fx %6.1f  %.3f  %5.0fx"%(typ,len(gl),naive,boot,de,n/de,icc,1+(kbar-1)*icc))
print("")

print("== E. IS THE DESIGN EFFECT A PROPERTY OF THE FEED OR OF THE ESTIMAND? ==")
print("Same game-block bootstrap on a WITHIN-game quantity (mean tick-to-tick change).")
print("mkt        games   naiveSE   bootSE     DE   n_eff")
for typ in MK:
    ser=sc[typ]
    byg=collections.defaultdict(list)
    for key,d in ser:
        t=sorted(d); byg[key[0]]+=[d[t[i]]-d[t[i-1]] for i in range(1,len(t))]
    gl=[g for g in byg.values() if g]; allv=[v for g in gl for v in g]; n=len(allv)
    if n<10: continue
    sd=statistics.pstdev(allv)
    if sd==0: continue
    naive=sd/math.sqrt(n); means=[]
    for _ in range(BB):
        s=0.0;c=0
        for _ in range(len(gl)):
            g=random.choice(gl); s+=sum(g); c+=len(g)
        means.append(s/c)
    boot=statistics.pstdev(means); de=(boot/naive)**2
    print("%-10s %5d  %8.5f  %8.5f  %5.1fx %6.1f"%(typ,len(gl),naive,boot,de,n/de))
print("")

print("== F. Minimum detectable effect at this n ==")
for ng in (20,27):
    print("  games=%d: 2-sample split -> |d| >= %.2f SD ; one-sample vs 0 -> |d| >= %.2f SD (80%% power)"
          %(ng,2.80*math.sqrt(2.0/(ng/2.0)),2.80/math.sqrt(ng)))
print("  ROI framing, per-game SD ~0.95u at 1u flat:")
for ng in (20,27,75,150):
    print("    n=%3d games -> MDE on mean ROI = %+.1f%%"%(ng,100*2.80*0.95/math.sqrt(ng)))
print("")

print("== G. Cross-market tick-change correlation (independent recompute) ==")
def diffs(d):
    t=sorted(d); return {t[i]: d[t[i]]-d[t[i-1]] for i in range(1,len(t))}
for a,b in [("spread","moneyline"),("total","team_total"),("total","spread"),("total","moneyline")]:
    cs=[]
    for gid in set(k[0] for k in series):
        A=[v for k,v in series.items() if k[0]==gid and k[1]==a and len(v)>=25]
        B=[v for k,v in series.items() if k[0]==gid and k[1]==b and len(v)>=25]
        if not A or not B: continue
        da=diffs(A[0]); db=diffs(B[0]); com=sorted(set(da)&set(db))
        if len(com)<20: continue
        x=[da[t] for t in com]; y=[db[t] for t in com]
        mx,my=statistics.mean(x),statistics.mean(y)
        sx=math.sqrt(sum((v-mx)**2 for v in x)); sy=math.sqrt(sum((v-my)**2 for v in y))
        if sx<=0 or sy<=0: continue
        cs.append(sum((x[i]-mx)*(y[i]-my) for i in range(len(x)))/(sx*sy))
    if cs:
        cs.sort()
        print("  %-11s vs %-11s ng=%2d mean=%+.3f med=%+.3f min=%+.3f max=%+.3f"
              %(a,b,len(cs),statistics.mean(cs),statistics.median(cs),cs[0],cs[-1]))
print("")

print("== H. Sensitivity to the >=25 obs cutoff ==")
for cut in (10,25,50,100):
    o=0; g=set()
    for k,d in series.items():
        if len(d)>=cut: o+=len(d); g.add(k[0])
    print("  cutoff>=%3d obs: obs=%6d games=%2d"%(cut,o,len(g)))
