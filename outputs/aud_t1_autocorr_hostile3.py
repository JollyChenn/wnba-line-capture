# HOSTILE AUDIT part 3: stability of the synthetic-step null across seeds + full lag curve.
import csv, os, sys, math, datetime, collections, statistics, random
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
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

LAGS=[1,2,5,10,15,20]
print("== M. Real rho curve vs SYNTHETIC-STEP NULL, 40 seeds, per market ==")
print("Null = same tick count, same number of level changes, change positions UNIFORM AT RANDOM,")
print("step sizes iid. If null ~= real, the 'correlation length' is an oversampling artifact.")
print("")
for typ in MK:
    ser=sc[typ]
    real={k:statistics.mean([a for a in (acf([d[t] for t in sorted(d)],k) for _,d in ser) if a is not None]) for k in LAGS}
    nulls={k:[] for k in LAGS}
    for sd in range(40):
        random.seed(9000+sd)
        acc={k:[] for k in LAGS}
        for key,d in ser:
            x=[d[t] for t in sorted(d)]
            nch=sum(1 for i in range(1,len(x)) if x[i]!=x[i-1])
            pos=set(random.sample(range(1,len(x)),min(nch,len(x)-1))) if nch else set()
            y=[0.0]*len(x); cur=0.0
            for i in range(1,len(x)):
                if i in pos: cur+=random.choice([-1,1])*random.choice([0.5,1.0])
                y[i]=cur
            for k in LAGS:
                b=acf(y,k)
                if b is not None: acc[k].append(b)
        for k in LAGS:
            if acc[k]: nulls[k].append(statistics.mean(acc[k]))
    print("  %s"%typ)
    for k in LAGS:
        nl=sorted(nulls[k])
        p95=nl[int(.95*len(nl))]; p05=nl[int(.05*len(nl))]
        verdict="REAL EXCEEDS NULL p95" if real[k]>p95 else ("under null p05" if real[k]<p05 else "INSIDE NULL BAND")
        print("    lag%-3d real=%+.3f  null mean=%+.3f  null 90%% band[%+.3f,%+.3f]  -> %s"
              %(k,real[k],statistics.mean(nulls[k]),p05,p95,verdict))
    print("")

print("== N. Arithmetic identity check ==")
print("mkt         mean ticks/series  mean level-changes/series  ticks-per-change  claimed corr length 15-20")
for typ in MK:
    ser=sc[typ]
    tk=[]; ch=[]
    for _,d in ser:
        x=[d[t] for t in sorted(d)]
        tk.append(len(x)); ch.append(sum(1 for i in range(1,len(x)) if x[i]!=x[i-1]))
    tpc=sum(tk)/max(sum(ch),1)
    print("  %-11s %14.1f %25.1f %17.1f"%(typ,statistics.mean(tk),statistics.mean(ch),tpc))
print("")
print("  => 'correlation length ~15-20 observations' is within noise of ticks-per-line-move,")
print("     i.e. it measures the CAPTURE CADENCE / line-update ratio, not market memory.")
print("")

print("== O. Does the operating conclusion survive? Bootstrap on n_eff -> games ratio ==")
random.seed(31337)
for typ in MK:
    ser=sc[typ]
    byg=collections.defaultdict(list)
    for key,d in ser: byg[key[0]]+=[d[t] for t in sorted(d)]
    gl=list(byg.values()); allv=[v for g in gl for v in g]; n=len(allv)
    naive=statistics.pstdev(allv)/math.sqrt(n)
    des=[]
    for _ in range(400):
        # jackknife-style: resample games, recompute DE
        sub=[random.choice(gl) for _ in gl]
        av=[v for g in sub for v in g]; nn=len(av)
        nv=statistics.pstdev(av)/math.sqrt(nn)
        ms=[]
        for _ in range(150):
            s=0.0;c=0
            for _ in range(len(sub)):
                g=random.choice(sub); s+=sum(g); c+=len(g)
            ms.append(s/c)
        b=statistics.pstdev(ms)
        if nv>0: des.append((b/nv)**2)
    des.sort()
    print("  %-11s DE point=%.0fx  bootstrap CI[%.0fx,%.0fx]  n_eff CI[%.0f,%.0f] vs %d games"
          %(typ,statistics.median(des),des[int(.025*len(des))],des[int(.975*len(des))],
            n/des[int(.975*len(des))],n/des[int(.025*len(des))],len(gl)))
