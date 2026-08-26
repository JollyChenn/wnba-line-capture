# Robustness / artifact hunt on the one live gradient: 1xbet OVER-PRICE drift 12h->6h.
import os, functools
D=os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D,"xm_table.py"),encoding="utf-8").read())
print=functools.partial(print,flush=True)
import statistics, collections, math, random
random.seed(20260826)
S=[r for r in T if r["dood1"] is not None]
def cls(r): return "short" if r["dood1"]<=-0.05 else ("long" if r["dood1"]>=0.05 else "flat")
for r in S: r["dc"]=cls(r)
def roi(rows,sd): return 100*statistics.mean(pnl(r,sd) for r in rows) if rows else float('nan')
def orate(rows): return sum(1 for r in rows if r["over_won"])/len(rows) if rows else float('nan')

print("### balance check: is 'short' a different population? ###")
print("%-6s%7s%9s%9s%9s%9s%9s"%("class","n","meanline","mean_ood","over%","ROI_O","ROI_U"))
for c in ("short","flat","long"):
    v=[r for r in S if r["dc"]==c]
    print("%-6s%7d%9.2f%9.3f%9.3f%9.2f%9.2f"%(c,len(v),statistics.mean(r["line"] for r in v),
        statistics.mean(r["ood"] for r in v),orate(v),roi(v,"Over"),roi(v,"Under")))
print("")
print("market mix by class (%):")
mk=sorted(set(r["mk"] for r in S))
print("%-6s"%""+"".join("%7s"%m for m in mk))
for c in ("short","flat","long"):
    v=[r for r in S if r["dc"]==c]
    print("%-6s"%c+"".join("%7.1f"%(100*sum(1 for r in v if r["mk"]==m)/len(v)) for m in mk))
print("")
print("### within-market ROI of the Over, by drift class ###")
print("%-6s%22s%22s%22s"%("mkt","short  n / ROI / over%","flat   n / ROI / over%","long   n / ROI / over%"))
for m in mk:
    line="%-6s"%m
    for c in ("short","flat","long"):
        v=[r for r in S if r["mk"]==m and r["dc"]==c]
        line+="%8d %+7.1f %5.3f"%(len(v),roi(v,"Over"),orate(v)) if v else "%22s"%"-"
    print(line)
print("")
print("### time split (out-of-sample halves) ###")
dates=sorted(set(r["date"] for r in S)); cut=dates[len(dates)//2]
for lab,fl in (("first half (<%s)"%cut,lambda r:r["date"]<cut),("second half (>=%s)"%cut,lambda r:r["date"]>=cut)):
    a=[r for r in S if fl(r) and r["dc"]=="short"]; b=[r for r in S if fl(r) and r["dc"]=="flat"]
    print("  %-22s short n=%4d ROI=%+6.2f over%%=%.3f | flat n=%4d ROI=%+6.2f over%%=%.3f | gap=%+6.2f pp"%(
        lab,len(a),roi(a,"Over"),orate(a),len(b),roi(b,"Over"),orate(b),roi(a,"Over")-roi(b,"Over")))
print("")
print("### is the drift signal just the LINE move in disguise? ###")
for dl,lab in ((0.0,"line unmoved"),):
    v=[r for r in S if r["dline1"]==dl]
    for c in ("short","flat","long"):
        w=[r for r in v if r["dc"]==c]
        print("  %-13s %-6s n=%4d ROI_O=%+6.2f over%%=%.3f"%(lab,c,len(w),roi(w,"Over"),orate(w)))
v=[r for r in S if r["dline1"] is not None and r["dline1"]!=0.0]
for c in ("short","flat","long"):
    w=[r for r in v if r["dc"]==c]
    if w: print("  %-13s %-6s n=%4d ROI_O=%+6.2f over%%=%.3f"%("line MOVED",c,len(w),roi(w,"Over"),orate(w)))
print("")
print("### magnitude gradient (is it monotone?) ###")
b=[(-99,-0.15),(-0.15,-0.08),(-0.08,-0.05),(-0.05,-0.02),(-0.02,0.02),(0.02,0.05),(0.05,0.08),(0.08,0.15),(0.15,99)]
for lo,hi in b:
    w=[r for r in S if lo<r["dood1"]<=hi]
    if len(w)>=40:
        print("  d_odds in (%+.2f,%+.2f]  n=%4d  over%%=%.3f  ROI_O=%+6.2f"%(lo,hi,len(w),orate(w),roi(w,"Over")))
print("")
print("### does the anchor age matter? (how stale is the 12h quote) ###")
for r in S:
    r["age"]=(r["tip"]-r["capA"]).total_seconds()/3600 if r["capA"] else None
print("  anchor quote median h-before-tip: %.1f ; gate quote median h-before-tip: %.1f"%(
    statistics.median([(r["tip"]-r["capA"]).total_seconds()/3600 for r in S if r["capA"]]),
    statistics.median([(r["tip"]-r["cap6"]).total_seconds()/3600 for r in S])))
print("")
print("### PLACEBO: drift measured on a random OTHER prop of the same slate ###")
byd=collections.defaultdict(list)
for r in S: byd[r["date"]].append(r)
gaps=[]
for _ in range(400):
    fake={}
    for d,rows in byd.items():
        don=rows[:]; random.shuffle(don)
        for r,dr in zip(rows,don): fake[id(r)]=dr["dc"]
    a=[r for r in S if fake[id(r)]=="short"]; b_=[r for r in S if fake[id(r)]=="flat"]
    gaps.append(roi(a,"Over")-roi(b_,"Over"))
gaps.sort()
real_gap=roi([r for r in S if r["dc"]=="short"],"Over")-roi([r for r in S if r["dc"]=="flat"],"Over")
print("  real short-minus-flat gap = %+.2f pp ; slate-shuffled placebo p95 = %+.2f pp ; p = %.4f"%(
    real_gap,gaps[int(.95*len(gaps))],(sum(1 for g in gaps if g>=real_gap)+1)/(len(gaps)+1)))
