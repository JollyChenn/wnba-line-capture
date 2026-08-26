# Q1/Q2 LEAD-LAG STRUCTURE (descriptive; no betting yet)
import os
D=os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D,"xm_table.py"),encoding="utf-8").read())
import datetime, statistics, collections, math
H=lambda h: datetime.timedelta(hours=h)

def corr(a,b):
    n=len(a)
    if n<3: return None
    ma,mb=statistics.mean(a),statistics.mean(b)
    sa=math.sqrt(sum((x-ma)**2 for x in a)); sb=math.sqrt(sum((x-mb)**2 for x in b))
    if sa==0 or sb==0: return None
    return sum((a[i]-ma)*(b[i]-mb) for i in range(n))/(sa*sb)
def spear(a,b):
    def rk(v):
        s=sorted(range(len(v)),key=lambda i:v[i]); r=[0]*len(v); i=0
        while i<len(s):
            j=i
            while j+1<len(s) and v[s[j+1]]==v[s[i]]: j+=1
            av=(i+j)/2+1
            for k in range(i,j+1): r[s[k]]=av
            i=j+1
        return r
    return corr(rk(a),rk(b))

HRS=[18,16,14,12,10,9,8,7,6,5,4,3,2,1]
# per-game panel
panel={}
props_by_gid=collections.defaultdict(list)
for (pl,mk,gid) in PROP: props_by_gid[gid].append((pl,mk))
for gid in set(r["gid"] for r in T):
    if gid not in PT: continue
    tp=aware(gmeta[gid][1])
    tot={}; ok=True
    for h in HRS:
        s=at_or_before(PT[gid],tp-H(h))
        tot[h]=s[1] if s else None
    if tot[18] is None: continue
    lines={}; povs={}
    for (pl,mk) in props_by_gid[gid]:
        ser=PROP[(pl,mk,gid)]
        v={}; pv={}
        for h in HRS:
            o=at_or_before(ser["Over"],tp-H(h)); u=at_or_before(ser["Under"],tp-H(h))
            v[h]=o[1] if o else None
            pv[h]=novig(o[2],u[2]) if (o and u and o[1]==u[1]) else None
        if v[18] is None: continue
        lines[(pl,mk)]=v; povs[(pl,mk)]=pv
    if not lines: continue
    panel[gid]=(tot,lines,povs)
print(f"panel games: {len(panel)}   props tracked: {sum(len(v[1]) for v in panel.values())}")
print("")
print("=== A. CUMULATIVE MOVE FROM 18h BEFORE TIP (means across games) ===")
print(f"{'h_to_tip':>8} {'d_total':>9} {'d_propline':>11} {'d_p_over':>9} {'n_games':>8}")
for h in HRS:
    dt=[];dl=[];dp=[]
    for gid,(tot,lines,povs) in panel.items():
        if tot[h] is None: continue
        dt.append(tot[h]-tot[18])
        ls=[v[h]-v[18] for v in lines.values() if v[h] is not None]
        if ls: dl.append(statistics.mean(ls))
        ps=[pv[h]-pv[18] for pv in povs.values() if pv[h] is not None and pv[18] is not None]
        if ps: dp.append(statistics.mean(ps))
    print(f"{h:>8} {statistics.mean(dt):>9.3f} {(statistics.mean(dl) if dl else float('nan')):>11.4f} "
          f"{(statistics.mean(dp) if dp else float('nan')):>9.4f} {len(dt):>8}")
print("")
print("=== B. CROSS-CORRELATION game-level: d_total(window W) vs d_propline(window W+lag) ===")
print("    windows are 6h wide. positive lag = props move AFTER total.")
WIN=[(18,12),(12,6),(9,3),(6,1)]
for (a,b) in WIN:
    for (c_,d_) in WIN:
        xs=[];ys=[]
        for gid,(tot,lines,povs) in panel.items():
            if None in (tot[a],tot[b],): continue
            ls=[v[d_]-v[c_] for v in lines.values() if v[d_] is not None and v[c_] is not None]
            if not ls: continue
            xs.append(tot[b]-tot[a]); ys.append(statistics.mean(ls))
        r=corr(xs,ys)
        if r is None or len(xs)<20: continue
        t=r*math.sqrt((len(xs)-2)/max(1e-9,1-r*r))
        lab=f"tot[{a}->{b}] vs propline[{c_}->{d_}]"
        print(f"  {lab:<40} rho={r:+.3f}  n={len(xs):>3}  t={t:+.2f}")
print("")
print("=== C. same, prop side = novig p_over ===")
for (a,b) in WIN:
    for (c_,d_) in WIN:
        xs=[];ys=[]
        for gid,(tot,lines,povs) in panel.items():
            if None in (tot[a],tot[b]): continue
            ps=[pv[d_]-pv[c_] for pv in povs.values() if pv[d_] is not None and pv[c_] is not None]
            if not ps: continue
            xs.append(tot[b]-tot[a]); ys.append(statistics.mean(ps))
        r=corr(xs,ys)
        if r is None or len(xs)<20: continue
        t=r*math.sqrt((len(xs)-2)/max(1e-9,1-r*r))
        print(f"  tot[{a}->{b}] vs p_over[{c_}->{d_}]".ljust(44)+f" rho={r:+.3f}  n={len(xs):>3}  t={t:+.2f}")
print("")
print("=== D. EVENT STUDY: after a Pinnacle total move of >=1.0pt, when do prop lines react? ===")
# find the first big total move in each game after 18h-to-tip
ev=[]
for gid,(tot,lines,povs) in panel.items():
    tp=aware(gmeta[gid][1])
    ser=PT[gid]
    base=None; t0=None
    for c_,p_,pr_ in ser:
        hh=(tp-c_).total_seconds()/3600
        if hh>18 or hh<2: continue
        if base is None: base=p_; continue
        if abs(p_-base)>=1.0:
            t0=c_; d=p_-base; break
    if t0 is None: continue
    for (pl,mk),v in lines.items():
        s=PROP[(pl,mk,gid)]["Over"]
        pre=at_or_before(s,t0)
        if not pre: continue
        for tau in (0,1,2,3,6,12,999):
            w=t0+H(tau) if tau!=999 else tp
            post=at_or_before(s,w)
            if post: ev.append((tau, d, post[1]-pre[1]))
print(f"  events: {len(set())}")
for tau in (0,1,2,3,6,12,999):
    rows=[(d,dl) for (t_,d,dl) in ev if t_==tau]
    if len(rows)<20: continue
    up=[dl for d,dl in rows if d>0]; dn=[dl for d,dl in rows if d<0]
    mvd=sum(1 for d,dl in rows if dl!=0)/len(rows)
    r=corr([d for d,_ in rows],[dl for _,dl in rows])
    print(f"  tau=+{tau if tau!=999 else 'tip':>4}h  n={len(rows):>4}  pct_prop_moved={100*mvd:>5.1f}%  "
          f"mean_dline|tot_up={statistics.mean(up) if up else float('nan'):+.3f}  "
          f"|tot_dn={statistics.mean(dn) if dn else float('nan'):+.3f}  rho={r if r is not None else float('nan'):+.3f}")
print("")
print("=== E. reverse event study: after a PROP line move, does the total follow? ===")
ev2=[]
for gid,(tot,lines,povs) in panel.items():
    tp=aware(gmeta[gid][1])
    for (pl,mk),v in lines.items():
        s=PROP[(pl,mk,gid)]["Over"]
        base=None;t0=None;dd=0
        for c_,ln,od in s:
            hh=(tp-c_).total_seconds()/3600
            if hh>18 or hh<2: continue
            if base is None: base=ln; continue
            if abs(ln-base)>=1.0: t0=c_; dd=ln-base; break
        if t0 is None: continue
        pre=at_or_before(PT[gid],t0)
        if not pre: continue
        for tau in (0,1,2,3,6,999):
            w=t0+H(tau) if tau!=999 else tp
            post=at_or_before(PT[gid],w)
            if post: ev2.append((tau,dd,post[1]-pre[1]))
for tau in (0,1,2,3,6,999):
    rows=[(d,dl) for (t_,d,dl) in ev2 if t_==tau]
    if len(rows)<20: continue
    r=corr([d for d,_ in rows],[dl for _,dl in rows])
    up=[dl for d,dl in rows if d>0]; dn=[dl for d,dl in rows if d<0]
    print(f"  tau=+{tau if tau!=999 else 'tip':>4}h  n={len(rows):>4}  mean_dtot|prop_up={statistics.mean(up) if up else float('nan'):+.3f}  "
          f"|prop_dn={statistics.mean(dn) if dn else float('nan'):+.3f}  rho={r if r is not None else float('nan'):+.3f}")
