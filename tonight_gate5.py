# tonight_gate5.py - apply the proposed gate 5 to tonight's actual card, and price it.
import csv, os, sys, random, collections, datetime, statistics
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260924)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "gate5.py"), encoding="utf-8").read()
     .split('print(f"{len(A)} bets with gates 1+2 on')[0])

print("=" * 96)
print("  PART 1 - PERMUTATION on gate 5, to price the multiplicity I skipped")
print("=" * 96)
print("  the label is shuffled between GAMES, keeping each game's bets together, because the")
print("  thing being tested is a property of a night's board and not of a single quote.")
print("")
bg = collections.defaultdict(list)
for r in A: bg[(r["pl"], r["gt"])].append(r)
keys = list(bg)
def roiof(rows):
    return 100*sum((r["od"]-1) if r["won"] else -1.0 for r in rows)/len(rows) if rows else 0.0
VAR = [("net", lambda r: r["net"]), ("nevup", lambda r: r["nevup"]), ("ismin", lambda r: r["ismin"])]
GRID = []
for nm, sel in VAR:
    GRID.append((f"gate5 {nm} alone", lambda r, s=sel: s(r)))
    GRID.append((f"gate3+gate5 {nm}", lambda r, s=sel: s(r) and r["star"] == "starred"))
GRID.append(("gate3 alone", lambda r: r["star"] == "starred"))
def best(assign):
    bb, bl = -9e9, ""
    for nm, sel in GRID:
        rows = [r for k in keys for r in bg[k] if sel(dict(r, **assign[k]))]
        if len(rows) < 40: continue
        v = roiof(rows)
        if v > bb: bb, bl = v, nm
    return bb, bl
real_assign = {k: {"net": bg[k][0]["net"], "nevup": bg[k][0]["nevup"],
                   "ismin": bg[k][0]["ismin"], "star": bg[k][0]["star"]} for k in keys}
real, rlbl = best(real_assign)
pool = list(real_assign.values())
T = 4000; beat = 0; sims = []
for _ in range(T):
    random.shuffle(pool)
    v, _ = best(dict(zip(keys, pool)))
    sims.append(v)
    if v >= real: beat += 1
sims.sort()
print(f"  best real cell: {rlbl}  ROI {real:+.1f}%")
print(f"  shuffled best-of-{len(GRID)}: median {sims[T//2]:+.1f}%  p95 {sims[int(T*.95)]:+.1f}%  max {sims[-1]:+.1f}%")
print(f"  GAME-BLOCK p = {beat/T:.4f}")
print("")
print("=" * 96)
print("  PART 2 - TONIGHT'S CARD THROUGH GATE 5")
print("=" * 96)
CARD = [("nalyssa smith", "pr", 17.5), ("jackie young", "pr", 22.5), ("angel reese", "pr", 28.5)]
now = datetime.datetime.now(datetime.timezone.utc)
for pl, mk, shown in CARD:
    tm = teamof.get(pl)
    gt = None
    for t in tips_of.get(tm, []):
        if t >= now and (t - now).total_seconds() <= 60*3600: gt = t; break
    q = seq.get((pl, mk, gt), []) if gt else []
    if not q:
        print(f"  {pl:<18} {mk:<4} no board history"); continue
    lines = [x[1] for x in q]
    o_l, p_l = q[0][1], q[-1][1]
    verdict = "PASS" if p_l <= o_l else "FAIL - drop"
    trip = " (round trip: peaked at %.1f)" % max(lines) if max(lines) > o_l and p_l <= o_l else ""
    print(f"  {pl:<18} {mk:<4} shown {shown}  tonight opened {o_l} -> now {p_l}  "
          f"({len(q)} quotes, first {(gt-q[0][0]).total_seconds()/3600:.0f}h out)   GATE5 {verdict}{trip}")
