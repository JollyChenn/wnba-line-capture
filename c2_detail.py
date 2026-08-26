# c2_detail.py - everything the report needs about the one cell that cleared its ceiling.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
gof={}
for gid,(d2,t2,hm,aw) in gmeta.items(): gof[(hm,t2)]=gid; gof[(aw,t2)]=gid
pin=collections.defaultdict(list)
for src,col in (("pinn_snapshots.csv","pinn_line"),("bets_log.csv","pinn"),("pinn_board.csv","pinn_line")):
    for r in load(src):
        t,ln=ts(r.get("captured_utc")),f(r.get(col))
        pl,mk=(r.get("player") or "").strip(),r.get("market")
        if t and ln is not None and pl and mk: pin[(_pl(pl),mk)].append((t,ln))
for v in pin.values(): v.sort()
def sharp_at(pl,mk,gt,h):
    cut=gt-datetime.timedelta(hours=h)
    g=[x for x in pin.get((pl,mk),[]) if x[0]<=cut and (gt-x[0]).total_seconds()<30*3600]
    return g[-1][1] if g else None
R=[]
for (pl,mk,gt),sdq in side.items():
    if "Over" not in sdq or "Under" not in sdq: continue
    if abs(sdq["Over"][1]-sdq["Under"][1])>0.01: continue
    now=pgrow.get((pl,gt)); tm=teamof.get(pl)
    if not now or mk not in now or not tm: continue
    ln=sdq["Over"][1]
    if now[mk]==ln: continue
    sp=sharp_at(pl,mk,gt,6)
    if sp is None or sp-ln<1.0: continue
    R.append(dict(pl=pl,mk=mk,gid=gof[(tm,gt)],date=gmeta[gof[(tm,gt)]][0],
                  od=sdq["Over"][2],won=now[mk]>ln,ret=((sdq["Over"][2]-1) if now[mk]>ln else -1.0)))
R.sort(key=lambda r:r["date"])
n=len(R); w=sum(1 for r in R if r["won"]); u=sum(r["ret"] for r in R)
print(f"C2 n={n} games={len({r['gid'] for r in R})} players={len({r['pl'] for r in R})} "
      f"{w}-{n-w} {100*w/n:.1f}% {u:+.2f}u ROI {100*u/n:+.1f}%")
print(f"  mean odds {statistics.mean(r['od'] for r in R):.3f}  breakeven {100/statistics.mean(r['od'] for r in R):.1f}%")
eq=peak=dd=0.0
for r in R:
    eq+=r["ret"]; peak=max(peak,eq); dd=min(dd,eq-peak)
print(f"  max drawdown {dd:+.2f}u  final {eq:+.2f}u")
mk=collections.Counter(r["mk"] for r in R); print(f"  by market: {dict(mk)}")
d=sorted({r["date"] for r in R}); k=len(d)//3
for i,(a,b) in enumerate([(d[0],d[k]),(d[k],d[2*k]),(d[2*k],d[-1])],1):
    g=[r for r in R if a<=r["date"]<=b]
    if g: print(f"  fold {i} {a}..{b}: n={len(g)} ROI {100*sum(x['ret'] for x in g)/len(g):+.1f}%")
for slip in (0.0,0.01,0.02,0.03):
    v=sum(((r["od"]-slip)-1) if r["won"] else -1.0 for r in R)/n
    print(f"  slippage {slip:.2f}: ROI {100*v:+.1f}%")
top=collections.Counter(r["pl"] for r in R).most_common(3)
print(f"  top players: {top}")
for p,_ in top:
    g=[r for r in R if r["pl"]!=p]
    print(f"    drop {p}: n={len(g)} ROI {100*sum(x['ret'] for x in g)/len(g):+.1f}%")
