# STEP 4 GRADED: is the ladder bettable? real posted prices, game-block CI, declared noise ceiling.
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
    t,o,ln = b.get("captured_utc"), f(b.get("odds")), f(b.get("line"))
    if not (t and o and ln is not None and b.get("market") in ALL_MK): continue
    inst[(_pl(b.get("player")), b.get("market"), t)][ln][b.get("side")] = o
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
    vals=[x[mk] for x in prior[-15:]]; sd=statistics.pstdev(vals)
    if sd<=0: continue
    k=(pl,mk,g2)
    if k in L and L[k]["t"]>=t: continue
    L[k]=dict(pl=pl,mk=mk,gt=g2,t=t,rung=rung,actual=now[mk],sd=sd)
L=list(L.values())
medsd=statistics.median(x["sd"] for x in L)
print(f"ladders n={len(L)} games={len(set(x['gt'] for x in L))} medianSD={medsd:.2f}")

# ---- build the 8 declared cells BEFORE looking ----
CELLS=[]
for rungpos in ("LOW","HIGH"):
    for sd_ in ("Over","Under"):
        for vol in ("all","lowvol","highvol"):
            CELLS.append((rungpos,sd_,vol))
print(f"DECLARED GRID: {len(CELLS)} cells (rung position x side x volatility band)")

def bets(rungpos, side_, vol):
    out=[]
    for r in L:
        if vol=="lowvol" and r["sd"]>=medsd: continue
        if vol=="highvol" and r["sd"]<medsd: continue
        ks=sorted(r["rung"]); ln = ks[0] if rungpos=="LOW" else ks[-1]
        od = r["rung"][ln][side_]
        won = (r["actual"]>ln) if side_=="Over" else (r["actual"]<ln)
        push = (r["actual"]==ln)
        out.append(dict(gt=r["gt"], od=od, won=won, push=push, p=vf(r["rung"][ln]["Over"],r["rung"][ln]["Under"]), side=side_))
    return out
def roi(bs):
    bs=[b for b in bs if not b["push"]]
    if not bs: return None,0
    return sum((b["od"]-1) if b["won"] else -1 for b in bs)/len(bs), len(bs)

print("\nOBSERVED (real posted prices, push voided):")
res={}
for c in CELLS:
    bs=bets(*c); r,n=roi(bs)
    if n<20: continue
    hit=sum(1 for b in bs if not b["push"] and b["won"])/n
    res[c]=(r,n,hit,bs)

# ---- NOISE CEILING: null = each rung's over-win prob EQUALS its vig-free posted prob.
# resample outcomes per ladder (one draw per ladder drives BOTH rungs & both sides consistently),
# blocked so a game's ladders move together via the shared draw structure.
def simulate():
    draw={}
    for r in L:
        draw[(r["pl"],r["mk"],r["gt"])]=random.random()
    best=-9
    for c in CELLS:
        rungpos,side_,vol=c
        tot=0.0; n=0
        for r in L:
            if vol=="lowvol" and r["sd"]>=medsd: continue
            if vol=="highvol" and r["sd"]<medsd: continue
            ks=sorted(r["rung"]); ln=ks[0] if rungpos=="LOW" else ks[-1]
            p=vf(r["rung"][ln]["Over"],r["rung"][ln]["Under"])
            u=draw[(r["pl"],r["mk"],r["gt"])]
            ov = u < p          # over hits
            won = ov if side_=="Over" else (not ov)
            od=r["rung"][ln][side_]
            tot += (od-1) if won else -1; n+=1
        if n>=20: best=max(best, tot/n)
    return best
NULL=[simulate() for _ in range(3000)]
NULL.sort()
ceil95=NULL[int(0.95*len(NULL))]
print(f"\nNOISE CEILING (p95 of BEST-of-{len(CELLS)} cell under 'rungs priced at their own vig-free prob'): {100*ceil95:+.2f}%")
print(f"   null best-cell median {100*statistics.median(NULL):+.2f}%   p99 {100*NULL[int(0.99*len(NULL))]:+.2f}%")

def boot(bs, B=4000):
    byg=collections.defaultdict(list)
    for b in bs:
        if not b["push"]: byg[b["gt"]].append(b)
    gl=list(byg)
    out=[]
    for _ in range(B):
        s=[]
        for _ in range(len(gl)): s.extend(byg[random.choice(gl)])
        if s: out.append(sum((x["od"]-1) if x["won"] else -1 for x in s)/len(s))
    out.sort()
    return out[int(0.025*len(out))], out[int(0.975*len(out))]

print(f"\n{'cell':<26}{'n':>5}{'games':>7}{'hit%':>8}{'ROI%':>9}   95% CI (game-block)   clears ceiling")
for c in sorted(res, key=lambda k:-res[k][0]):
    r,n,hit,bs=res[c]
    lo,hi=boot(bs)
    g=len(set(b["gt"] for b in bs))
    print(f"{'/'.join(c):<26}{n:>5}{g:>7}{100*hit:>8.1f}{100*r:>9.2f}   [{100*lo:+7.2f},{100*hi:+7.2f}]   {'YES' if r>ceil95 else 'no'}")
