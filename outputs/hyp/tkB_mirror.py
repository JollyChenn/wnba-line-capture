# B - EXPLORATORY (post-hoc, flagged): the INVERTED version of the brief's claim.
# Brief said: back big-positive divergence, fade big-negative. The raw-production check went the
# other way, so price the 4-cell mirror family honestly with its own ceiling.
import os, sys, math, statistics, collections, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
from tk_lib import load_games, annotate, block_boot
random.seed(20260826)

G = annotate(load_games())
hist = collections.defaultdict(list)
for g in G:
    for side, t in (("h", g["home"]), ("a", g["away"])):
        g["hist_" + side] = list(hist[(g["season"], t)])
    d = g["margin"]
    hist[(g["season"], g["home"])].append(d)
    hist[(g["season"], g["away"])].append(-d)

def state(h):
    if len(h) < 15: return None
    r10 = statistics.mean(h[-10:]); std = statistics.mean(h)
    if std < 0 and r10 > 0: return "badEarly_goodLate"
    if std > 0 and r10 < 0: return "goodEarly_badLate"
    return None

MINN = 60
LAB = ["badEarly_goodLate", "goodEarly_badLate"]
BETS = ["ML_back", "ML_fade", "SP_back", "SP_fade"]
print("DECLARED (post-hoc) FAMILY: 2 states x 4 bets = 8 cells, min n = %d" % MINN)

def build(labfn):
    cells = collections.defaultdict(list)
    for g in G:
        if g["spread"] is None: continue
        for side in ("h", "a"):
            st = labfn(g, side)
            if st is None: continue
            if g["ml_h"] and g["ml_a"]:
                wo = (g["margin"] > 0) if side == "h" else (g["margin"] < 0)
                cells[(st, "ML_back")].append(((g["ml_h"] if side == "h" else g["ml_a"]) - 1.0) if wo else -1.0)
                cells[(st, "ML_fade")].append(((g["ml_a"] if side == "h" else g["ml_h"]) - 1.0) if not wo else -1.0)
            if g["sp_h"] and g["sp_a"]:
                d = (g["margin"] + g["spread"]) * (1 if side == "h" else -1)
                if d != 0:
                    cells[(st, "SP_back")].append(((g["sp_h"] if side == "h" else g["sp_a"]) - 1.0) if d > 0 else -1.0)
                    cells[(st, "SP_fade")].append(((g["sp_a"] if side == "h" else g["sp_h"]) - 1.0) if d < 0 else -1.0)
    return cells

real = build(lambda g, s: state(g["hist_" + s]))

# ceiling: permute the (state_h, state_a) pair across games within season
by_s = collections.defaultdict(list)
for g in G:
    if g["spread"] is not None: by_s[g["season"]].append(g)
rnd = random.Random(31337)
bests = []
for _ in range(2000):
    pm = {}
    for s, gs in by_s.items():
        labs = [(state(x["hist_h"]), state(x["hist_a"])) for x in gs]
        rnd.shuffle(labs)
        for x, l in zip(gs, labs): pm[x["gid"]] = l
    c = build(lambda g, s: pm[g["gid"]][0 if s == "h" else 1])
    bests.append(max((sum(v) / len(v) for v in c.values() if len(v) >= MINN), default=-9))
bests.sort()
CEIL = bests[int(0.95 * len(bests))]
print("NOISE CEILING (2000 game-level permutations, best of 8 cells): p95 = %+.2f%%\n" % (CEIL * 100))

print("%-20s %s" % ("state", " ".join("%18s" % b for b in BETS)))
for st in LAB:
    line = "%-20s " % st
    for bt in BETS:
        v = real.get((st, bt), [])
        line += (" %+7.2f%% n=%-4d" % (sum(v) / len(v) * 100, len(v))) if v else "%18s" % "--"
    print(line)

best = max(((sum(v) / len(v), k, len(v)) for k, v in real.items() if len(v) >= MINN))
print("\nBEST: %s ROI=%+.2f%% n=%d  vs ceiling %+.2f%% -> %s" % (
    best[1], best[0] * 100, best[2], CEIL * 100, "CLEARS" if best[0] > CEIL else "UNDER CEILING (noise)"))
lo, hi = block_boot([[x] for x in real[best[1]]], iters=4000)
print("  block-bootstrap CI: [%+.2f%%, %+.2f%%]" % (lo * 100, hi * 100))

print("\nper-season walk-forward, goodEarly_badLate SP_back and ML_back:")
for bt in ("SP_back", "ML_back"):
    per = collections.defaultdict(list)
    for g in G:
        if g["spread"] is None: continue
        for side in ("h", "a"):
            if state(g["hist_" + side]) != "goodEarly_badLate": continue
            if bt == "ML_back" and g["ml_h"] and g["ml_a"]:
                wo = (g["margin"] > 0) if side == "h" else (g["margin"] < 0)
                per[g["season"]].append(((g["ml_h"] if side == "h" else g["ml_a"]) - 1.0) if wo else -1.0)
            if bt == "SP_back" and g["sp_h"] and g["sp_a"]:
                d = (g["margin"] + g["spread"]) * (1 if side == "h" else -1)
                if d != 0: per[g["season"]].append(((g["sp_h"] if side == "h" else g["sp_a"]) - 1.0) if d > 0 else -1.0)
    print("  %-8s %s" % (bt, "  ".join("%d:%+.1f%%(n=%d)" % (s, sum(v) / len(v) * 100, len(v)) for s, v in sorted(per.items()))))
    nseasons_pos = sum(1 for s, v in per.items() if sum(v) > 0)
    print("           seasons profitable: %d of %d" % (nseasons_pos, len(per)))
