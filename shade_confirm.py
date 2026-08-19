# shade_confirm.py - the board-wide shade cell, tested at the level the label actually lives at.
# ---------------------------------------------------------------------------------------------
# boardhunt.py swept 88 cells and two cleared its ceiling, the best being
#     cushion 3+ AND opponent shaded down -> OVER    n=255   +15.1%   (ceiling +13.5%)
#
# But that ceiling is WRONG for this particular cell, and wrong in the direction that flatters it.
# The permutation shuffled outcomes globally across all 6311 quotes. opp_shade is a GAME-level
# label - every quote in a game shares it - so a global shuffle destroys exactly the clustering
# that makes a game-level claim uncertain. The null comes out too tight and the cell looks better
# than it is. This is the same method law that killed the rank finding in August.
#
# The correct null keeps the games intact and permutes the LABEL across them: reassign which games
# count as "shaded down", holding every outcome exactly where it is. If the real split still beats
# 95% of relabelled worlds, the effect survives its own proper test.
#
# Also here: does it replicate OUT of the Model S sample? shade.py measured this on 91 Model S
# bets and got rho -0.231, p=0.0186. The board sample is 6311 quotes over 139 games and shares
# almost none of those bets. Two independent samples agreeing is worth more than either alone.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260819)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
ALLMK = ("pts", "pr", "pra", "pa", "ra", "reb", "ast")
tip_on, gof, oppof = {}, {}, {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    tip_on[(hm, d2)] = t2; tip_on[(aw, d2)] = t2
    gof[(hm, t2)] = gid; gof[(aw, t2)] = gid
    oppof[(hm, t2)] = aw; oppof[(aw, t2)] = hm
def med_before(pl, mk, gt):
    v = [r[mk] for r in hist.get(pl, []) if r["tip"] < gt]
    return statistics.median(v[-10:]) if len(v) >= 4 else None
shade = collections.defaultdict(list)
for (pl, mk, gt), sdq in side.items():
    if mk != "pts" or "Over" not in sdq: continue
    tm = teamof.get(pl)
    if not tm: continue
    m = med_before(pl, "pts", gt)
    if m is not None: shade[(tm, gt)].append(sdq["Over"][1] - m)

Q = []
for (pl, mk, gt), sdq in side.items():
    if mk not in ALLMK or "Over" not in sdq or "Under" not in sdq: continue
    if abs(sdq["Over"][1] - sdq["Under"][1]) > 0.01: continue
    now = pgrow.get((pl, gt))
    if not now or mk not in now: continue
    ln = sdq["Over"][1]
    if now[mk] == ln: continue
    tm = teamof.get(pl)
    med = med_before(pl, mk, gt)
    if not tm or med is None: continue
    op = oppof.get((tm, gt)); o_s = shade.get((op, gt), [])
    if len(o_s) < 3: continue
    Q.append(dict(pl=pl, mk=mk, gid=gof[(tm, gt)], tm=tm, cush=med - ln,
                  od=sdq["Over"][2], won=now[mk] > ln, opp=statistics.mean(o_s)))
DEEP = [r for r in Q if r["cush"] >= 3]
gshade = {}
for r in Q: gshade.setdefault((r["gid"], r["tm"]), r["opp"])
print(f"{len(Q)} quotes with an opponent-shade reading; {len(DEEP)} have cushion 3+")
print(f"across {len({r['gid'] for r in DEEP})} games")
print("")

def roi(rows): return 100*sum((r["od"]-1) if r["won"] else -1.0 for r in rows)/len(rows) if rows else 0.0
down = [r for r in DEEP if r["opp"] <= 0]; up = [r for r in DEEP if r["opp"] > 0]
print("="*100)
print("  THE CELL")
print("="*100)
for g, lbl in ((down, "cushion 3+, opponent shaded DOWN"), (up, "cushion 3+, opponent shaded UP")):
    n = len(g); w = sum(1 for r in g if r["won"])
    print(f"  {lbl:<40} n={n:<5}{100*w/n:>6.1f}%  ROI {roi(g):+6.1f}%")
print("")

print("="*100)
print("  THE CORRECT NULL - relabel which GAME-SIDES are shaded down, outcomes untouched")
print("="*100)
keys = list(gshade)
vals = [gshade[k] for k in keys]
real = roi(down) - roi(up)
T = 5000; beat = 0; sims = []
for _ in range(T):
    random.shuffle(vals)
    lab = {k: v for k, v in zip(keys, vals)}
    a = [r for r in DEEP if lab[(r["gid"], r["tm"])] <= 0]
    b = [r for r in DEEP if lab[(r["gid"], r["tm"])] > 0]
    if len(a) < 40 or len(b) < 40: continue
    d = roi(a) - roi(b); sims.append(d)
    if d >= real: beat += 1
sims.sort()
print(f"  real gap (down minus up): {real:+.1f} points")
print(f"  relabelled: median {sims[len(sims)//2]:+.1f}   p95 {sims[int(len(sims)*0.95)]:+.1f}"
      f"   p99 {sims[int(len(sims)*0.99)]:+.1f}")
print(f"  GAME-LEVEL PERMUTATION p = {beat/max(len(sims),1):.4f}")
print("")
print("  this is the number that counts. boardhunt's +13.5% ceiling was computed with a global")
print("  outcome shuffle, which is too tight for a label that is constant within a game.")
print("")
print("="*100)
print("  MULTIPLICITY - boardhunt tried 88 cells. correct for that too.")
print("="*100)
print(f"  a single test at p={beat/max(len(sims),1):.4f} becomes, over 88 looks,")
b1 = beat/max(len(sims), 1)
print(f"    Bonferroni-style bound: p_adj <= {min(1.0, b1*88):.3f}")
print(f"    (harsh - the 88 cells overlap heavily, so the true adjustment is milder)")
print("")
print("="*100)
print("  ROBUSTNESS of the board-wide cell")
print("="*100)
bt = collections.Counter(r["tm"] for r in down)
w = sorted((roi([r for r in down if r["tm"] != t]), t) for t in bt)
print(f"  leave-one-TEAM-out : worst {w[0][0]:+.1f}% (drop {w[0][1]})   best {w[-1][0]:+.1f}%")
bm = collections.Counter(r["mk"] for r in down)
print("  by market:")
for m, c in bm.most_common():
    g = [r for r in down if r["mk"] == m]
    if len(g) < 20: continue
    print(f"    {m:<5} n={len(g):<4} ROI {roi(g):+6.1f}%")
