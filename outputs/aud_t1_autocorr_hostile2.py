# HOSTILE AUDIT part 2: game-block CI on rho itself; resolvability of "correlation length 15-20".
import csv, os, sys, math, datetime, collections, statistics, random
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(4242)
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"aud_t1_autocorr_hostile.py"),
     encoding="utf-8").read().split('print("== A. Scope reproduction ==")')[0])

MK=["total","spread","team_total","moneyline"]
sc={t:[(k,v) for k,v in series.items() if k[1]==t and len(v)>=25] for t in MK}

def acf(x,k):
    n=len(x)
    if n<=k+3: return None
    m=statistics.mean(x); den=sum((v-m)**2 for v in x)
    if den<=0: return None
    return sum((x[i]-m)*(x[i+k]-m) for i in range(n-k))/den

LAGS=[1,2,3,5,8,10,12,15,20,25,30]
print("== I. GAME-BLOCK BOOTSTRAP 95%% CI ON rho(k) ITSELF (2000 iters) ==")
print("If the CI on rho(10)/rho(20) spans zero, 'correlation length ~15-20 obs' is not resolved.")
BB=2000
cross_all=collections.defaultdict(list)
for typ in MK:
    # per-game mean acf at each lag
    pg=collections.defaultdict(dict)   # gid -> lag -> value
    for key,d in sc[typ]:
        x=[d[t] for t in sorted(d)]
        for k in LAGS:
            a=acf(x,k)
            if a is not None: pg[key[0]].setdefault(k,[]).append(a)
    games=sorted(pg)
    gm={g:{k:statistics.mean(v) for k,v in pg[g].items()} for g in games}
    print("  %s (ngames=%d)"%(typ,len(games)))
    for k in LAGS:
        have=[g for g in games if k in gm[g]]
        if len(have)<5: continue
        pt=statistics.mean([gm[g][k] for g in have])
        bs=[]
        for _ in range(BB):
            s=[gm[random.choice(have)][k] for _ in have]
            bs.append(statistics.mean(s))
        bs.sort()
        lo,hi=bs[int(.025*BB)],bs[int(.975*BB)]
        flag="  <-- CI SPANS ZERO" if lo<0<hi else ""
        print("    lag%-3d ng=%2d rho=%+.3f  CI[%+.3f,%+.3f]%s"%(k,len(have),pt,lo,hi,flag))
    # bootstrap distribution of the ZERO-CROSSING lag
    xs=[]
    for _ in range(BB):
        samp=[random.choice(games) for _ in games]
        cur=None
        for k in LAGS:
            vv=[gm[g][k] for g in samp if k in gm[g]]
            if not vv: continue
            if statistics.mean(vv)<=0: cur=k; break
        xs.append(cur if cur is not None else 99)
    xs.sort()
    fin=[v for v in xs if v!=99]
    print("    zero-crossing lag: median=%s  CI[%s,%s]  (never crosses by lag30 in %.0f%% of resamples)"
          %(xs[len(xs)//2],xs[int(.025*BB)],xs[int(.975*BB)],100*(len(xs)-len(fin))/len(xs)))
print("")

print("== J. Is rho(1)=0.88 a finding, or just 'the line rarely moves'? ==")
print("mkt        ticks  %%ticks with NO change  distinct levels/game  moves/game")
for typ in MK:
    nt=0; same=0; lev=[]; mv=[]
    for key,d in sc[typ]:
        x=[d[t] for t in sorted(d)]
        c=sum(1 for i in range(1,len(x)) if x[i]==x[i-1])
        nt+=len(x)-1; same+=c
        lev.append(len(set(x))); mv.append(len(x)-1-c)
    print("%-10s %6d  %18.1f%%  %18.1f  %10.1f"%(typ,nt,100*same/nt,statistics.mean(lev),statistics.mean(mv)))
print("")
print("Interpretation: for a step series that is constant on ~X%% of ticks, rho(1) is mechanically")
print("near 1 regardless of any market dynamics. Confirm with a null: shuffle the ORDER of the")
print("distinct levels within each game but keep the run-length structure -> rho should stay high.")
print("")

print("== K. NULL CEILING for rho: random-walk / step-process with the same run lengths ==")
print("Generate, per game-market, a synthetic series with the SAME number of ticks and the SAME")
print("number of level changes, changes placed uniformly at random, level steps iid +/-0.5/1.0.")
for typ in MK:
    real=[]; null=[]
    for key,d in sc[typ]:
        x=[d[t] for t in sorted(d)]
        a=acf(x,10)
        if a is not None: real.append(a)
        nch=sum(1 for i in range(1,len(x)) if x[i]!=x[i-1])
        pos=sorted(random.sample(range(1,len(x)),min(nch,len(x)-1))) if nch else []
        y=[0.0]*len(x); cur=0.0
        for i in range(1,len(x)):
            if i in pos: cur+=random.choice([-1,1])*random.choice([0.5,1.0])
            y[i]=cur
        b=acf(y,10)
        if b is not None: null.append(b)
    if real and null:
        print("  %-10s real rho(10)=%+.3f   synthetic-step null rho(10)=%+.3f"%(typ,statistics.mean(real),statistics.mean(null)))
print("")

print("== L. What the audit's own headline numbers rest on ==")
print("  main-line in-play obs matched:      6,097   (claim text says '24,645 in-play obs' - that")
print("                                              figure INCLUDES alt=1 and is NOT the analysis set)")
print("  obs entering the rho/DE analysis:   5,642")
print("  independent games carrying it:         20   (7 of the 27 in-play games contribute nothing)")
print("  series (game x market x side):        100   but only ~2 orthogonal families per game")
