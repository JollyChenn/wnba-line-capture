# Window hygiene: how fresh is the "<= tip-6h" quote really, and do the two live gradients
# survive when the observation window is forced to be a genuine, separated 12h->6h window?
import os, functools
D=os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D,"xm_table.py"),encoding="utf-8").read())
print=functools.partial(print,flush=True)
import statistics, collections, math, random
random.seed(20260826)
for r in T:
    r["h6"]=(r["tip"]-r["cap6"]).total_seconds()/3600
    r["hA"]=(r["tip"]-r["capA"]).total_seconds()/3600 if r["capA"] else None
    r["sep"]=None if r["hA"] is None else r["hA"]-r["h6"]
print("### freshness of the gate quote (last two-sided quote at or before tip-6h) ###")
h=[r["h6"] for r in T]
q=sorted(h)
print("  p10 %.1f  p25 %.1f  median %.1f  p75 %.1f  p90 %.1f  (hours before tip)"%(
    q[int(.1*len(q))],q[int(.25*len(q))],q[len(q)//2],q[int(.75*len(q))],q[int(.9*len(q))]))
print("  rows with gate quote inside 6-12h of tip: %d / %d (%.0f%%)"%(
    sum(1 for x in h if x<=12),len(h),100*sum(1 for x in h if x<=12)/len(h)))
sep=[r["sep"] for r in T if r["sep"] is not None]
print("  anchor-to-gate separation: median %.1f h ; zero (same capture) on %d rows (%.0f%%)"%(
    statistics.median(sep),sum(1 for x in sep if x<0.01),100*sum(1 for x in sep if x<0.01)/len(sep)))
print("")
CLEAN=[r for r in T if r["sep"] is not None and r["sep"]>=2.0 and r["h6"]<=12.0 and r["dood1"] is not None]
print("### CLEAN SUBSET: gate quote <=12h before tip AND >=2h newer than the anchor ###")
print("  n = %d  (of %d)"%(len(CLEAN),len(T)))
def roi(rows,sd): return 100*statistics.mean(pnl(r,sd) for r in rows) if rows else float('nan')
def orate(rows): return sum(1 for r in rows if r["over_won"])/len(rows) if rows else float('nan')
def cls(r): return "short" if r["dood1"]<=-0.05 else ("long" if r["dood1"]>=0.05 else "flat")
print("  %-6s%7s%9s%9s%9s"%("class","n","over%","ROI_O","ROI_U"))
for c in ("short","flat","long"):
    v=[r for r in CLEAN if cls(r)==c]
    if v: print("  %-6s%7d%9.3f%9.2f%9.2f"%(c,len(v),orate(v),roi(v,"Over"),roi(v,"Under")))
a=[r for r in CLEAN if cls(r)=="short"]; b=[r for r in CLEAN if cls(r)=="flat"]
gap=roi(a,"Over")-roi(b,"Over")
byd=collections.defaultdict(list)
for r in CLEAN: byd[r["date"]].append(r)
gaps=[]
for _ in range(2000):
    fake={}
    for d,rows in byd.items():
        don=rows[:]; random.shuffle(don)
        for r,dr in zip(rows,don): fake[id(r)]=cls(dr)
    aa=[r for r in CLEAN if fake[id(r)]=="short"]; bb=[r for r in CLEAN if fake[id(r)]=="flat"]
    if aa and bb: gaps.append(roi(aa,"Over")-roi(bb,"Over"))
gaps.sort()
print("  short-minus-flat Over gap = %+.2f pp ; slate-shuffled placebo p95 %+.2f pp ; p=%.4f"%(
    gap,gaps[int(.95*len(gaps))],(sum(1 for g in gaps if g>=gap)+1)/(len(gaps)+1)))
print("")
print("### CLEAN SUBSET: total-move propagation cells ###")
C2=[r for r in CLEAN if r["dtot"] is not None]
print("  n with pinnacle total = %d"%len(C2))
for lab,fl in (("totUP>=1",lambda r:r["dtot"]>=1),("totFLAT",lambda r:abs(r["dtot"])<1),("totDN<=-1",lambda r:r["dtot"]<=-1)):
    for sub,sl in (("all",lambda r:True),("line unmoved",lambda r:r["dline1"]==0.0)):
        v=[r for r in C2 if fl(r) and sl(r)]
        if len(v)>=40:
            print("  %-10s %-12s n=%4d over%%=%.3f ROI_O=%+6.2f ROI_U=%+6.2f"%(lab,sub,len(v),orate(v),roi(v,"Over"),roi(v,"Under")))
print("")
print("### CLEAN SUBSET: her own line move (the known within-market fade), as a sanity control ###")
for lab,fl in (("line UP>=1",lambda r:r["dline1"] is not None and r["dline1"]>=1),
               ("line flat",lambda r:r["dline1"]==0.0),
               ("line DN<=-1",lambda r:r["dline1"] is not None and r["dline1"]<=-1)):
    v=[r for r in CLEAN if fl(r)]
    if len(v)>=30: print("  %-12s n=%4d over%%=%.3f ROI_O=%+6.2f ROI_U=%+6.2f"%(lab,len(v),orate(v),roi(v,"Over"),roi(v,"Under")))
