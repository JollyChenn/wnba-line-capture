# reaudit_rank.py - the check I owed the rank finding before quoting a p-value on it.
# ---------------------------------------------------------------------------------------------
# mega_sweep permuted outcomes across all 6,077 quotes independently. That is the WRONG null for
# rank, and it flatters it badly. Rank is not a property of a quote, it is a property of a PLAYER
# for most of a season - the same handful of women fill the rank-2 slot every night. So n=1471 is
# not 1471 independent draws; it is a few dozen players multiplied by their own season. Shuffling
# quote-by-quote breaks that clustering and hands back a p-value computed against a null that
# could never have produced the data.
#
# Three tests that respect the clustering:
#   A  how many DISTINCT players actually carry each cell (the effective sample size)
#   B  leave-one-player-out - does one good season carry the whole thing
#   C  a BLOCK permutation that shuffles rank labels BETWEEN players, keeping each player's games
#      and outcomes welded together. That asks the only question worth asking: given these players
#      and these seasons, could a random assignment of ranks look this good?
#   D  a player-block bootstrap for an honest confidence interval
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260916)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])

def roi(rows, which):
    if not rows: return 0.0
    if which == "over":
        return 100*sum((r["over_od"]-1) if r["over_won"] else -1.0 for r in rows)/len(rows)
    return 100*sum((r["under_od"]-1) if not r["over_won"] else -1.0 for r in rows)/len(rows)

CELLS = (("rank 2 OVER", 2, "over"), ("rank 4 UNDER", 4, "under"))
print(f"{len(B)} quotes")
print("")
print("="*104)
print("  A. EFFECTIVE SAMPLE SIZE - how many players is this really?")
print("="*104)
for nm, k, w in CELLS:
    g = [r for r in B if r["rank"] == k]
    pls = collections.Counter(r["pl"] for r in g)
    tot = sum(pls.values())
    top = pls.most_common(5)
    print(f"  {nm}:  n={tot} quotes but only {len(pls)} DISTINCT PLAYERS")
    print(f"      top 5 by volume: " + ", ".join(f"{p.split()[-1]} {c}" for p, c in top)
          + f"  ({100*sum(c for _, c in top)/tot:.0f}% of the cell)")
    # a player appears in up to 7 markets per game - count games, not quotes
    gms = len({(r["pl"], r["gt"]) for r in g})
    print(f"      and only {gms} distinct player-GAMES ({tot/gms:.1f} correlated quotes each)")
    print("")
print("="*104)
print("  B. LEAVE-ONE-PLAYER-OUT - does one season carry it?")
print("="*104)
for nm, k, w in CELLS:
    g = [r for r in B if r["rank"] == k]
    base = roi(g, w)
    outs = []
    for pl in {r["pl"] for r in g}:
        rest = [r for r in g if r["pl"] != pl]
        if len(rest) < 100: continue
        outs.append((roi(rest, w), pl, len(g)-len(rest)))
    outs.sort()
    print(f"  {nm}  full {base:+.1f}%")
    print(f"      worst 3 drops: " + " | ".join(f"-{p.split()[-1]}({c}) -> {v:+.1f}%" for v, p, c in outs[:3]))
    print(f"      best  3 drops: " + " | ".join(f"-{p.split()[-1]}({c}) -> {v:+.1f}%" for v, p, c in outs[-3:]))
    neg = sum(1 for v, _, _ in outs if v <= 0)
    print(f"      removing ONE player turns it non-positive in {neg} of {len(outs)} cases")
    print("")
print("="*104)
print("  C. BLOCK PERMUTATION - shuffle RANK between players, keep each player's season intact")
print("="*104)
print("  every quote keeps its own outcome and its own price. only the rank LABEL moves, and it")
print("  moves a whole player at a time, so the clustering that quote-level shuffling destroys is")
print("  preserved. this is the null that could actually have produced the data.")
print("")
byplayer = collections.defaultdict(list)
for r in B: byplayer[r["pl"]].append(r)
# a player's modal rank - the label the block carries
pmode = {}
for pl, rows in byplayer.items():
    pmode[pl] = collections.Counter(r["rank"] for r in rows).most_common(1)[0][0]
labels = list(pmode.values()); players = list(pmode.keys())
GRID = [(f"rank{k} {w}", k, w) for k in range(1, 8) for w in ("over", "under")]
def best_under(assign):
    bb, bl = -9e9, ""
    for nm, k, w in GRID:
        g = [r for pl in players if assign[pl] == k for r in byplayer[pl]]
        if len(g) < 120: continue
        v = roi(g, w)
        if v > bb: bb, bl = v, nm
    return bb, bl
real_b, real_l = best_under(pmode)
T = 2000; beat = 0; sims = []
for _ in range(T):
    random.shuffle(labels)
    v, _ = best_under(dict(zip(players, labels)))
    sims.append(v)
    if v >= real_b: beat += 1
sims.sort()
print(f"  real best cell (modal-rank version): {real_l}  {real_b:+.1f}%")
print(f"  block-shuffled best-of-grid: median {sims[T//2]:+.1f}%  p95 {sims[int(T*.95)]:+.1f}%  max {sims[-1]:+.1f}%")
print(f"  BLOCK p = {beat/T:.4f}")
print("")
print(f"  compare: the quote-level permutation in mega_sweep gave p=0.0207 with a p95 ceiling of")
print(f"  +4.2%. the block ceiling is {sims[int(T*.95)]:+.1f}%.")
print("")
print("="*104)
print("  D. PLAYER-BLOCK BOOTSTRAP - honest confidence interval")
print("="*104)
for nm, k, w in CELLS:
    g = [r for r in B if r["rank"] == k]
    bp = collections.defaultdict(list)
    for r in g: bp[r["pl"]].append(r)
    keys = list(bp)
    outs = []
    for _ in range(3000):
        pick = [random.choice(keys) for _ in keys]
        rows = [r for p in pick for r in bp[p]]
        outs.append(roi(rows, w))
    outs.sort()
    lo, hi = outs[int(3000*.025)], outs[int(3000*.975)]
    print(f"  {nm:<15} point {roi(g, w):+.1f}%   95% CI [{lo:+.1f}%, {hi:+.1f}%]   "
          f"{'EXCLUDES 0' if lo > 0 else 'includes 0'}")
print("")
print("  (a quote-level bootstrap would give a band roughly sqrt(quotes-per-player) times tighter")
print("   and would be wrong for the same reason the quote-level permutation is.)")
