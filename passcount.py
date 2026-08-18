# passcount.py - a lone Model S pass on a team looks very different from a cluster of them.
# ---------------------------------------------------------------------------------------------
# From mate_pattern: among Model-S-shaped quotes, the ROI runs -29.3% / -9.7% / +3.6% as the
# number of passes on the same TEAM-GAME goes 1 / 2 / 3. Monotonic, and with a mechanism that
# does not need a p-value to be plausible:
#
#   the filter fires when the book has NOT raised her since her last game. If the book raised
#   every other starter on that team and left only her, it was paying attention and chose to
#   leave that number - which is information, not neglect. Real inattention looks like three or
#   four numbers on one team going untouched.
#
# That earlier cut used all seven markets and did not dedupe. This one is built the way the card
# actually bets: BET_MKTS only, one position per player, best price. Intervals are GAME-block
# bootstraps here, not player-block - the label being tested lives on the team-game, so that is
# the unit that has to move together.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260918)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
BET_MKTS = ("pra", "pr", "pts")

# Model-S-shaped: bet market, book did not raise her 0.5+ since her previous game
S = [r for r in B if r["mk"] in BET_MKTS and r.get("starred") is True]
# one position per player-game, best price - the live staking rule
best = {}
for r in sorted(S, key=lambda x: -x["over_od"]):
    best.setdefault((r["pl"], r["gt"]), r)
S = sorted(best.values(), key=lambda r: (r["date"], r["pl"]))
PC = collections.Counter((r["tm"], r["gt"]) for r in S)
for r in S: r["pc"] = PC[(r["tm"], r["gt"])]
print(f"{len(S)} Model-S-shaped bets after one-position dedup, on {len(PC)} team-games")
print("")

def roi(rows): return 100*sum((r["over_od"]-1) if r["over_won"] else -1.0 for r in rows)/len(rows) if rows else 0.0
def hit(rows): return 100*sum(1 for r in rows if r["over_won"])/len(rows) if rows else 0.0
def gboot(rows, T=3000):
    bg = collections.defaultdict(list)
    for r in rows: bg[(r["tm"], r["gt"])].append(r)
    keys = list(bg)
    if len(keys) < 8: return None, None
    out = []
    for _ in range(T):
        pick = [random.choice(keys) for _ in keys]
        out.append(roi([r for k in pick for r in bg[k]]))
    out.sort()
    return out[int(T*.025)], out[int(T*.975)]
def show(rows, label, minn=25):
    n = len(rows)
    if n < minn:
        print(f"  {label:<44} n={n:<5} too few"); return
    lo, hi = gboot(rows)
    ng = len({(r["tm"], r["gt"]) for r in rows})
    ci = f"[{lo:+6.1f}%,{hi:+6.1f}%]" if lo is not None else "       -        "
    print(f"  {label:<44} n={n:<5} {ng:>3}g  {hit(rows):5.1f}%  ROI {roi(rows):+6.1f}%  95CI {ci}")

print("="*112)
print("  1. THE FULL GRADIENT")
print("="*112)
for c in range(1, 6):
    show([r for r in S if r["pc"] == c], f"  {c} pass(es) on the team-game", minn=20)
show([r for r in S if r["pc"] >= 3], "  3 or more (the keep)", minn=20)
show([r for r in S if r["pc"] <= 2], "  1 or 2 (the cut)", minn=20)
show(S, "  ALL Model-S-shaped (no filter)", minn=20)
print("")
print("="*112)
print("  2. OUT OF SAMPLE")
print("="*112)
dts = sorted({r["date"] for r in S}); cut = dts[int(len(dts)*0.6)]
print(f"  split {cut}")
for lbl, sel in ((">=3 passes", lambda r: r["pc"] >= 3), ("<=2 passes", lambda r: r["pc"] <= 2),
                 ("no filter", lambda r: True)):
    g = [r for r in S if sel(r)]
    show([r for r in g if r["date"] <  cut], f"    {lbl}  IN ", minn=20)
    show([r for r in g if r["date"] >= cut], f"    {lbl}  OUT", minn=20)
    print("")
print("="*112)
print("  3. THE CONFOUND - is pass-count just a proxy for how many players the book quotes?")
print("="*112)
print("  a team-game with more QUOTED players mechanically has more chances to produce a pass.")
print("  if the gradient is really about roster coverage it should vanish once that is held fixed.")
print("")
QC = collections.Counter()
for r in B:
    if r["mk"] in BET_MKTS: QC[(r["tm"], r["gt"])] += 1
qs = sorted(QC.values()); qmed = qs[len(qs)//2]
for lbl, sel in ((f"team-games with MANY quotes (>={qmed})", lambda r: QC[(r['tm'], r['gt'])] >= qmed),
                 (f"team-games with FEW quotes (<{qmed})",  lambda r: QC[(r['tm'], r['gt'])] <  qmed)):
    print(f"  --- {lbl} ---")
    for c in (1, 2):
        show([r for r in S if sel(r) and r["pc"] == c], f"      {c} pass(es)", minn=20)
    show([r for r in S if sel(r) and r["pc"] >= 3], "      3+ passes", minn=20)
    print("")
print("  and as a RATE rather than a count - passes divided by players quoted:")
for lo, hi_, lbl in ((0.0, 0.34, "  low pass-rate (<34%)"), (0.34, 0.67, "  mid pass-rate"),
                     (0.67, 1.01, "  high pass-rate (>=67%)")):
    g = [r for r in S if lo <= r["pc"]/max(1, QC[(r["tm"], r["gt"])]) < hi_]
    show(g, lbl, minn=20)
print("")
print("="*112)
print("  4. PERMUTATION - shuffle the pass-count labels BETWEEN team-games")
print("="*112)
print("  each team-game keeps its own bets and outcomes; only the count label moves. that tests")
print("  the gradient without pretending the bets inside a game are independent.")
print("")
bg = collections.defaultdict(list)
for r in S: bg[(r["tm"], r["gt"])].append(r)
keys = list(bg); lab = [PC[k] for k in keys]
BUCK = [("pc==1", lambda c: c == 1), ("pc==2", lambda c: c == 2), ("pc==3", lambda c: c == 3),
        ("pc>=3", lambda c: c >= 3), ("pc<=2", lambda c: c <= 2), ("pc>=4", lambda c: c >= 4)]
def best_of(assign):
    bb, bl = -9e9, ""
    for nm, sel in BUCK:
        rows = [r for k in keys if sel(assign[k]) for r in bg[k]]
        if len(rows) < 60: continue
        v = roi(rows)
        if v > bb: bb, bl = v, nm
    return bb, bl
real, rlbl = best_of(dict(zip(keys, lab)))
T = 4000; beat = 0; sims = []
for _ in range(T):
    random.shuffle(lab)
    v, _ = best_of(dict(zip(keys, lab)))
    sims.append(v)
    if v >= real: beat += 1
sims.sort()
print(f"  real best: {rlbl}  {real:+.1f}%")
print(f"  shuffled best-of-6: median {sims[T//2]:+.1f}%  p95 {sims[int(T*.95)]:+.1f}%  max {sims[-1]:+.1f}%")
print(f"  BLOCK p = {beat/T:.4f}")
print("")
print("="*112)
print("  5. WHAT IT WOULD COST - volume, if we only bet 3+ pass team-games")
print("="*112)
tot_g = len({r["date"] for r in S})
kept = [r for r in S if r["pc"] >= 3]
print(f"  bets: {len(S)} -> {len(kept)}  ({100*len(kept)/len(S):.0f}% kept)")
print(f"  per slate: {len(S)/tot_g:.2f} -> {len(kept)/tot_g:.2f} bets a night over {tot_g} slates")
