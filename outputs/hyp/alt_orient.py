import os,sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from _boot import ROOT, _src
exec(_src)
random.seed(20260826)
def vf(o,u): return (1.0/o)/((1.0/o)+(1.0/u))
rows=load("xbet_board.csv")
inst=collections.defaultdict(lambda: collections.defaultdict(dict))
for b in rows:
    t,o,ln=b.get("captured_utc"),f(b.get("odds")),f(b.get("line"))
    if not (t and o and ln is not None and b.get("market") in ALL_MK): continue
    inst[(_pl(b.get("player")),b.get("market"),t)][ln][b.get("side")]=o
L={}
for (pl,mk,tstr),v in inst.items():
    rung={ln:s for ln,s in v.items() if "Over" in s and "Under" in s}
    if len(rung)<2: continue
    tm=teamof.get(pl)
    if not tm: continue
    t=ts(tstr); g2=game_for(tm,t)
    if not g2: continue
    now=pgrow.get((pl,g2))
    if not now or now["min"]<8: continue
    prior=[x for x in hist.get(pl,[]) if x["tip"]<g2 and x["tm"]==now["tm"]]
    if len(prior)<5: continue
    k=(pl,mk,g2)
    if k in L and L[k]["t"]>=t: continue
    L[k]=dict(pl=pl,mk=mk,gt=g2,t=t,rung=rung,actual=now[mk],
              med=statistics.median([x[mk] for x in prior[-15:]]))
L=list(L.values())
c=collections.Counter()
for r in L:
    ks=sorted(r["rung"])
    main=min(ks,key=lambda x: abs(1.0/r["rung"][x]["Over"]-1.0/r["rung"][x]["Under"]))
    c["main=LOW" if main==ks[0] else "main=HIGH"]+=1
print("MAIN rung (prices closest to even) orientation:", dict(c))
# how far is each rung from her prior median?
lo=[min(r["rung"])-r["med"] for r in L]; hi=[max(r["rung"])-r["med"] for r in L]
print(f"LOW rung  - her 15g median: mean {statistics.mean(lo):+.2f}  median {statistics.median(lo):+.2f}")
print(f"HIGH rung - her 15g median: mean {statistics.mean(hi):+.2f}  median {statistics.median(hi):+.2f}")
print(f"actual    - her 15g median: mean {statistics.mean([r['actual']-r['med'] for r in L]):+.2f}")
# PRICE BAND: how much opinion can the book express in price alone?
q=[]
for (pl,mk,tstr),v in inst.items():
    for ln,s in v.items():
        if "Over" in s and "Under" in s: q.append(vf(s["Over"],s["Under"]))
q.sort()
print(f"\nfull-board vig-free P(over): p05 {q[len(q)//20]:.3f}  p95 {q[19*len(q)//20]:.3f}  span {q[19*len(q)//20]-q[len(q)//20]:.3f}")
print(f"  realised dP/pt on ladders = 0.069 -> the ENTIRE price band = {(q[19*len(q)//20]-q[len(q)//20])/0.069:.2f} points of line.")
