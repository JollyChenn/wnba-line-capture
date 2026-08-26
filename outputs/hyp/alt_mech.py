# MECHANISM ON RAW PRODUCTION: is the ladder's priced probability step smaller than the realised one?
import os,sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from _boot import ROOT, _src
exec(_src)
random.seed(20260826)
def vf(o,u): return (1.0/o)/((1.0/o)+(1.0/u))
rows = load("xbet_board.csv")
inst = collections.defaultdict(lambda: collections.defaultdict(dict))
for b in rows:
    t,o,ln=b.get("captured_utc"),f(b.get("odds")),f(b.get("line"))
    if not (t and o and ln is not None and b.get("market") in ALL_MK): continue
    inst[(_pl(b.get("player")),b.get("market"),t)][ln][b.get("side")]=o
L={}; ALLQ=[]
for (pl,mk,tstr),v in inst.items():
    tm=teamof.get(pl)
    if not tm: continue
    t=ts(tstr); g2=game_for(tm,t)
    if not g2: continue
    now=pgrow.get((pl,g2))
    if not now or now["min"]<8: continue
    rung={ln:s for ln,s in v.items() if "Over" in s and "Under" in s}
    if not rung: continue
    for ln,s in rung.items():
        if now[mk]!=ln: ALLQ.append((g2, now[mk]>ln, s["Over"], s["Under"]))
    if len(rung)<2: continue
    prior=[x for x in hist.get(pl,[]) if x["tip"]<g2 and x["tm"]==now["tm"]]
    if len(prior)<5: continue
    vals=[x[mk] for x in prior[-15:]]; sd=statistics.pstdev(vals)
    if sd<=0: continue
    k=(pl,mk,g2)
    if k in L and L[k]["t"]>=t: continue
    L[k]=dict(pl=pl,mk=mk,gt=g2,t=t,rung=rung,actual=now[mk],sd=sd)
L=list(L.values())

# BASE RATE control: over hit rate on the WHOLE two-sided board
ov=sum(1 for g,w,a,b in ALLQ if w)/len(ALLQ)
print(f"BASE RATE control: over hit rate on the full two-sided board = {100*ov:.1f}%  (n={len(ALLQ)} quotes)")

pairs=[]
for r in L:
    ks=sorted(r["rung"]); a,b2=ks[0],ks[-1]; d=b2-a
    if d<=0: continue
    if r["actual"]==a or r["actual"]==b2: pass
    pa_=vf(r["rung"][a]["Over"],r["rung"][a]["Under"]); pb_=vf(r["rung"][b2]["Over"],r["rung"][b2]["Under"])
    pairs.append(dict(gt=r["gt"], d=d, priced=(pa_-pb_)/d,
                      realised=((1 if r["actual"]>a else 0)-(1 if r["actual"]>b2 else 0))/d,
                      sd=r["sd"], mk=r["mk"]))
print(f"\nMECHANISM: within-ladder step, n={len(pairs)} ladders, {len(set(p['gt'] for p in pairs))} games")
pr=statistics.mean(p["priced"] for p in pairs); re_=statistics.mean(p["realised"] for p in pairs)
print(f"  PRICED   dP(over)/pt (book vig-free) = {pr:+.4f}")
print(f"  REALISED dP(over)/pt (actual boxes)  = {re_:+.4f}")
print(f"  compression ratio priced/realised    = {pr/re_:.3f}")
# game-block bootstrap of the DIFFERENCE
byg=collections.defaultdict(list)
for p in pairs: byg[p["gt"]].append(p)
gl=list(byg); B=6000; ds=[]
for _ in range(B):
    s=[]
    for _ in range(len(gl)): s.extend(byg[random.choice(gl)])
    ds.append(statistics.mean(x["realised"] for x in s)-statistics.mean(x["priced"] for x in s))
ds.sort()
print(f"  realised MINUS priced = {re_-pr:+.4f}/pt   95% CI [{ds[int(.025*B)]:+.4f},{ds[int(.975*B)]:+.4f}]"
      f"   p(two-sided, boot) = {2*min(sum(1 for x in ds if x<=0),sum(1 for x in ds if x>=0))/B:.4f}")
print(f"  -> value leaking per side per point = {(re_-pr)/2:+.4f} = {100*(re_-pr)/2:.2f}pp;  vig per side = {(1.078-1)/2*100:.2f}pp")

print("\n  by her volatility (median split sd=%.2f):"%statistics.median([p["sd"] for p in pairs]))
m=statistics.median([p["sd"] for p in pairs])
for lab,sel in (("low vol",[p for p in pairs if p["sd"]<m]),("high vol",[p for p in pairs if p["sd"]>=m])):
    pr2=statistics.mean(p["priced"] for p in sel); re2=statistics.mean(p["realised"] for p in sel)
    print(f"    {lab:<9} n={len(sel):>4} priced {pr2:+.4f} realised {re2:+.4f} gap {re2-pr2:+.4f}")

# PAIRED main-vs-alt ROI difference (the brief's actual question)
print("\nPAIRED: OVER at the LOW rung minus OVER at the HIGH rung (same ladder, real prices)")
diffs=collections.defaultdict(list)
for r in L:
    ks=sorted(r["rung"]); a,b2=ks[0],ks[-1]
    if r["actual"]==a or r["actual"]==b2: continue
    ra=(r["rung"][a]["Over"]-1) if r["actual"]>a else -1
    rb=(r["rung"][b2]["Over"]-1) if r["actual"]>b2 else -1
    diffs[r["gt"]].append(ra-rb)
gl=list(diffs); flat=[x for v in diffs.values() for x in v]
obs=statistics.mean(flat); bs=[]
for _ in range(6000):
    s=[]
    for _ in range(len(gl)): s.extend(diffs[random.choice(gl)])
    bs.append(statistics.mean(s))
bs.sort()
print(f"  n={len(flat)} ladders, {len(gl)} games:  mean paired ROI difference {100*obs:+.2f}%"
      f"  95% CI [{100*bs[150]:+.2f},{100*bs[5849]:+.2f}]")
print("  (positive = the MAIN/lower rung outperforms the deeper alternate -> brief's claim INVERTED)")
