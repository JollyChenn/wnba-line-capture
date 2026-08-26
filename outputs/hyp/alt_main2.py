import os,sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from _boot import ROOT, _src
exec(_src)
random.seed(20260826)

rows = load("xbet_board.csv")
inst = collections.defaultdict(lambda: collections.defaultdict(dict))
for b in rows:
    t, o, ln = b.get("captured_utc"), f(b.get("odds")), f(b.get("line"))
    if not (t and o and ln is not None and b.get("market") in ALL_MK): continue
    inst[(_pl(b.get("player")), b.get("market"), t)][ln][b.get("side")] = o
def vf(oo, ou):
    po, pu = 1.0/oo, 1.0/ou
    return po/(po+pu)
def NCDF(z): return 0.5*(1+math.erf(z/math.sqrt(2)))
def NPDF(z): return math.exp(-0.5*z*z)/math.sqrt(2*math.pi)

LAD = []
for (pl, mk, tstr), v in inst.items():
    rung = {ln: s for ln, s in v.items() if "Over" in s and "Under" in s}
    if not rung: continue
    tm = teamof.get(pl)
    if not tm: continue
    t = ts(tstr); g2 = game_for(tm, t)
    if not g2: continue
    now = pgrow.get((pl, g2))
    if not now or now["min"] < 8: continue
    prior = [x for x in hist.get(pl, []) if x["tip"] < g2 and x["tm"] == now["tm"]]
    if len(prior) < 5: continue
    vals = [x[mk] for x in prior[-15:]]
    sd = statistics.pstdev(vals) if len(vals) > 1 else 0.0
    LAD.append(dict(pl=pl, mk=mk, gt=g2, t=t, rung=rung, actual=now[mk],
                    hrs=(g2-t).total_seconds()/3600.0, mu=statistics.mean(vals), sd=sd, vals=vals))

# =====================================================================
print("="*78); print("STEP 3 FEASIBILITY  does a sharp-gap bet EVER have an alternate rung?"); print("="*78)
# Pinnacle read <=6h to tip, gap >= 1pt vs 1xbet
pinn = collections.defaultdict(list)   # (player, market) -> [(t, line)]
for r in load("pinn_board.csv"):
    t, ln = ts(r.get("captured_utc")), f(r.get("pinn_line"))
    if t and ln is not None and r.get("market") in ALL_MK:
        pinn[(_pl(r.get("player")), r.get("market"))].append((t, ln))
for r in load("pinn_snapshots.csv"):
    t, ln = ts(r.get("captured_utc")), f(r.get("pinn_line"))
    if t and ln is not None and r.get("market") in ALL_MK:
        pinn[(_pl(r.get("player")), r.get("market"))].append((t, ln))
for v in pinn.values(): v.sort()
print(f"pinnacle player-markets covered: {len(pinn)}")

gap_rows = []
for r in LAD:
    if r["hrs"] > 6 or r["hrs"] < 0: continue
    pv = pinn.get((r["pl"], r["mk"]))
    if not pv: continue
    # latest pinn read at or before the xbet ping, same game window (within 24h before tip)
    cand = [(t, ln) for t, ln in pv if t <= r["t"] and (r["gt"]-t).total_seconds() <= 24*3600 and t <= r["gt"]]
    if not cand: continue
    pt, pln = cand[-1]
    main = min(r["rung"], key=lambda L: abs(1.0/r["rung"][L]["Over"] - 1.0/r["rung"][L]["Under"]))
    gap = pln - main
    gap_rows.append(dict(r, pln=pln, main=main, gap=gap))
print(f"xbet pings with a Pinnacle read <=6h to tip: {len(gap_rows)}")
sig = [x for x in gap_rows if abs(x["gap"]) >= 1.0]
print(f"  with |gap| >= 1pt (the ALIVE Tier-2 signal):        {len(sig)}"
      f"   games={len(set(x['gt'] for x in sig))}")
alt = [x for x in sig if len(x["rung"]) >= 2]
print(f"  ...AND an alternate rung available at that instant: {len(alt)}")
if alt:
    print("   ->", collections.Counter(x["mk"] for x in alt).most_common())
sigg = [x for x in gap_rows if len(x["rung"]) >= 2]
print(f"  pings with an alternate rung at all (any gap):      {len(sigg)}")

# =====================================================================
print("\n"+"="*78); print("STEP 4  WHERE IS THE LADDER WRONG? fair vs posted, by rung offset"); print("="*78)
# use the ONE-rung-per-instant board too: offset measured vs her own prior distribution
# fair P(over) from empirical CDF (with normal smoothing), edge = fair - posted vig-free
# grade at REAL posted price. Independent unit = game.
def fairP(vals, sd, line):
    if sd <= 0: return None
    # smoothed empirical: average of normal kernels
    h = max(0.9*sd*len(vals)**-0.2, 0.75)
    return sum(1-NCDF((line-x)/h) for x in vals)/len(vals)

# per-ladder rung comparison (the direct within-game test)
rowsL = []
for r in LAD:
    if len(r["rung"]) < 2 or r["sd"] <= 0: continue
    main = min(r["rung"], key=lambda L: abs(1.0/r["rung"][L]["Over"] - 1.0/r["rung"][L]["Under"]))
    for L, s in r["rung"].items():
        fp = fairP(r["vals"], r["sd"], L)
        if fp is None: continue
        post = vf(s["Over"], s["Under"])
        rowsL.append(dict(pl=r["pl"], mk=r["mk"], gt=r["gt"], line=L, off=L-main, is_main=(L==main),
                          fair=fp, post=post, edge=fp-post, oo=s["Over"], ou=s["Under"],
                          won=r["actual"] > L, z=(L-r["mu"])/r["sd"]))
print(f"rungs inside a simultaneous ladder: {len(rowsL)}  (games {len(set(x['gt'] for x in rowsL))})")
for lab, sel in (("MAIN rung", [x for x in rowsL if x["is_main"]]),
                 ("ALT rung ", [x for x in rowsL if not x["is_main"]])):
    if not sel: continue
    print(f"  {lab}: n={len(sel):>4}  median fair-P {statistics.median([x['fair'] for x in sel]):.3f}"
          f"  posted-P {statistics.median([x['post'] for x in sel]):.3f}"
          f"  EDGE(over) {statistics.median([x['edge'] for x in sel]):+.4f}")

print("\n  by |z| of the rung (tails vs middle), edge = fairP - postedP on the OVER:")
for lo, hi, lab in ((-9,-1.0,"deep under-tail z<-1"), (-1.0,-0.35,"z -1..-0.35"), (-0.35,0.35,"MIDDLE |z|<0.35"),
                    (0.35,1.0,"z 0.35..1"), (1.0,9,"deep over-tail z>1")):
    s = [x for x in rowsL if lo <= x["z"] < hi]
    if len(s) < 10: continue
    print(f"    {lab:<22} n={len(s):>4}  median edge {statistics.median([x['edge'] for x in s]):+.4f}"
          f"  mean {statistics.mean([x['edge'] for x in s]):+.4f}")
