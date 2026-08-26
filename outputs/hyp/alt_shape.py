# What ARE the 577 simultaneous 2-rung quotes? Real alternates, or capture artifacts?
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

def vigfree(oo, ou):
    po, pu = 1/oo, 1/ou
    return po/(po+pu)

pairs = []
for (pl, mk, t), v in inst.items():
    rung = {ln: s for ln, s in v.items() if "Over" in s and "Under" in s}
    if len(rung) != 2: continue
    a, b2 = sorted(rung)
    pairs.append(dict(pl=pl, mk=mk, t=t, lo=a, hi=b2, d=b2-a,
                      lo_o=rung[a]["Over"], lo_u=rung[a]["Under"],
                      hi_o=rung[b2]["Over"], hi_u=rung[b2]["Under"]))
print(f"simultaneous 2-rung quotes: {len(pairs)}")
print("\nRUNG SPACING (hi - lo):")
c = collections.Counter(round(p["d"],1) for p in pairs)
for k in sorted(c): print(f"  {k:>5}: {c[k]:>4}  ({100*c[k]/len(pairs):.1f}%)")

print("\nMARKET mix:", collections.Counter(p["mk"] for p in pairs).most_common())

# does the over price DROP as line rises (a real ladder must)?
mono = sum(1 for p in pairs if p["hi_o"] > p["lo_o"])
same = sum(1 for p in pairs if abs(p["hi_o"]-p["lo_o"]) < 1e-9)
print(f"\nHigher line pays MORE on the over (correct ladder direction): {mono}/{len(pairs)} = {100*mono/len(pairs):.1f}%")
print(f"Identical over price at both rungs (=stale duplicate):        {same}/{len(pairs)} = {100*same/len(pairs):.1f}%")
wrong = len(pairs)-mono-same
print(f"WRONG direction (higher line pays LESS):                      {wrong}/{len(pairs)} = {100*wrong/len(pairs):.1f}%")

# implied prob drop per point
dp = []
for p in pairs:
    if p["d"] <= 0: continue
    plo, phi = vigfree(p["lo_o"], p["lo_u"]), vigfree(p["hi_o"], p["hi_u"])
    dp.append(((plo-phi)/p["d"], p["mk"], p["d"], plo, phi, p["lo"]))
print(f"\nIMPLIED vig-free P(over) drop per point of line, n={len(dp)}:")
v = sorted(x[0] for x in dp)
print(f"  median {statistics.median(v):+.4f}/pt   IQR [{v[len(v)//4]:+.4f},{v[3*len(v)//4]:+.4f}]  mean {statistics.mean(v):+.4f}")
print(f"  fraction <= 0 (prob did NOT fall as line rose): {sum(1 for x in v if x<=0)}/{len(v)} = {100*sum(1 for x in v if x<=0)/len(v):.1f}%")

for mk in ("pts","reb","ast","pra","pr","pa","ra"):
    s = [x[0] for x in dp if x[1]==mk]
    if len(s)>=8: print(f"  {mk:<4} n={len(s):>4} median {statistics.median(s):+.4f}/pt")
