# boardhunt.py - build a NEW rule for any player prop, on the whole board.
# ---------------------------------------------------------------------------------------------
# Everything tried so far has been an adjustment to Model S, and Model S buys 2 bets a night. This
# asks a different question: forget the three signals entirely, and ask whether a rule built from
# pre-tip features alone can find bettable props ANYWHERE on the board.
#
# The board is the right place for this. 6000+ two-sided quotes means the noise ceiling is a few
# percent, not the 45% that made the n=78 hunts hopeless. If an edge exists here it is findable.
#
# WHAT TODAY SAYS TO LOOK FOR. The gate ladder was the most informative thing all session:
#     the three signals alone     54.3% - exactly the breakeven rate. nothing.
#     gate 3 alone (wider srcs)   +1.0%. nothing.
#     the two together            +15.9%.
# Neither ingredient works by itself. So sweeping single features - which is what every hunt this
# season did, including mega_sweep's 74 cells - was always going to come back empty. This sweeps
# INTERACTIONS: cushion x star, cushion x drift, star x shade, and so on, both sides, and prices
# every one from the real two-sided quote so the 7.4% margin is always being paid.
#
# METHOD LAW: the ceiling is computed BEFORE any result is looked at, by permuting outcomes within
# GAME blocks and re-running the entire grid, so it accounts for every cell tried at once. A cell
# that does not clear the p95 line is not a finding no matter how good it looks.
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

# pre-tip price walk, per player-market-game, at a fixed line
walk = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if not (t and o and ln is not None) or b.get("side") != "Over": continue
    pl, mk = (b.get("player") or "").lower(), b.get("market")
    tm = teamof.get(pl)
    if not tm: continue
    gt = game_for(tm, t)
    if gt: walk[(pl, mk, gt)].append((t, ln, o))
for v in walk.values(): v.sort()

def stat_before(pl, mk, gt):
    v = [r[mk] for r in hist.get(pl, []) if r["tip"] < gt]
    if len(v) < 4: return None, None, None
    w = v[-10:]
    sd = statistics.pstdev(w) if len(w) > 1 else None
    mn = [r["min"] for r in hist.get(pl, []) if r["tip"] < gt]
    return statistics.median(w), sd, (statistics.mean(mn[-3:]) - statistics.mean(mn[-8:-3])
                                      if len(mn) >= 8 else None)
shade = collections.defaultdict(list)
for (pl, mk, gt), sdq in side.items():
    if mk != "pts" or "Over" not in sdq: continue
    tm = teamof.get(pl)
    if not tm: continue
    m, _, _ = stat_before(pl, "pts", gt)
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
    if not tm: continue
    med, sd, mtr = stat_before(pl, mk, gt)
    if med is None: continue
    pv = prevline.get((pl, mk, gt))
    q = walk.get((pl, mk, gt), [])
    same = [x for x in q if abs(x[1] - ln) < 0.01]
    pre = (same[-1][2] - same[0][2]) if len(same) >= 2 else None
    op = oppof.get((tm, gt)); o_s = shade.get((op, gt), [])
    Q.append(dict(pl=pl, mk=mk, gt=gt, gid=gof[(tm, gt)], tm=tm, ln=ln,
                  o_od=sdq["Over"][2], u_od=sdq["Under"][2],
                  o_won=now[mk] > ln, u_won=now[mk] < ln,
                  cush=med - ln, csd=((med - ln)/sd) if sd else None,
                  star=(pv is not None and ln - pv < 0.5), hasprev=(pv is not None),
                  drift=pre, mtr=mtr,
                  opp=(statistics.mean(o_s) if len(o_s) >= 3 else None)))
print(f"{len(Q)} two-sided board quotes with a median, across {len({r['gid'] for r in Q})} games")
mo = statistics.mean(r["o_od"] for r in Q); mu = statistics.mean(r["u_od"] for r in Q)
print(f"  mean Over {mo:.3f} / Under {mu:.3f} -> margin {100*(1/mo+1/mu-1):.1f}%,"
      f" breakeven {100/mo/(1/mo+1/mu)*(1/mo+1/mu):.1f}% ... i.e. about {100/mo:.1f}% on the over")
print("")

# ---- the grid ------------------------------------------------------------------------------
def cells():
    """every (label, selector, side) triple we are willing to consider"""
    C = []
    CUSH = (("cushion 3+", lambda r: r["cush"] >= 3), ("cushion 1..3", lambda r: 1 <= r["cush"] < 3),
            ("cushion -1..1", lambda r: -1 <= r["cush"] < 1), ("cushion <-1", lambda r: r["cush"] < -1))
    STAR = (("star", lambda r: r["star"]), ("raised", lambda r: r["hasprev"] and not r["star"]))
    DRIF = (("price shortened", lambda r: r["drift"] is not None and r["drift"] < -0.005),
            ("price drifted", lambda r: r["drift"] is not None and r["drift"] > 0.005))
    SHAD = (("opp shaded down", lambda r: r["opp"] is not None and r["opp"] <= 0),
            ("opp shaded up", lambda r: r["opp"] is not None and r["opp"] > 0))
    MINS = (("minutes rising", lambda r: r["mtr"] is not None and r["mtr"] >= 2),
            ("minutes falling", lambda r: r["mtr"] is not None and r["mtr"] <= -2))
    for sd in ("o", "u"):
        for a, fa in CUSH:
            C.append((a, fa, sd))
            for grp in (STAR, DRIF, SHAD, MINS):
                for b, fb in grp:
                    C.append((f"{a} + {b}", lambda r, fa=fa, fb=fb: fa(r) and fb(r), sd))
        for grp in (STAR, DRIF, SHAD, MINS):
            for b, fb in grp: C.append((b, fb, sd))
    return C
GRID = cells()

def roi(rows, sd):
    wk, ok = (sd + "_won"), (sd + "_od")
    if not rows: return None
    return 100*sum((r[ok]-1) if r[wk] else -1.0 for r in rows)/len(rows)
MINN = 120
real = []
for lbl, sel, sd in GRID:
    g = [r for r in Q if sel(r)]
    if len(g) < MINN: continue
    real.append((roi(g, sd), lbl, sd, len(g)))

# ---- ceiling FIRST, permuting outcomes inside game blocks ------------------------------------
bg = collections.defaultdict(list)
for r in Q: bg[r["gid"]].append(r)
peaks = []
T = 400
for _ in range(T):
    pool = [(r["o_won"], r["u_won"]) for r in Q]
    random.shuffle(pool)
    for r, v in zip(Q, pool): r["_o"], r["_u"] = v
    best = -99
    for lbl, sel, sd in GRID:
        g = [r for r in Q if sel(r)]
        if len(g) < MINN: continue
        wk = "_o" if sd == "o" else "_u"; ok = sd + "_od"
        v = 100*sum((r[ok]-1) if r[wk] else -1.0 for r in g)/len(g)
        best = max(best, v)
    peaks.append(best)
peaks.sort()
CEIL = peaks[int(len(peaks)*0.95)]
print("="*104)
print(f"  NOISE CEILING, COMPUTED FIRST: {len(GRID)} cells swept, outcomes reshuffled {T} times.")
print(f"  the best cell reaches ROI {CEIL:+.1f}% at p95 by luck alone (median {peaks[len(peaks)//2]:+.1f}%).")
print(f"  ANY cell below {CEIL:+.1f}% is noise. Minimum cell size {MINN}.")
print("="*104)
print("")
real.sort(reverse=True)
print(f"  {'rule':<44}{'side':>6}{'n':>7}{'ROI':>9}   verdict")
for v, lbl, sd, n in real[:18]:
    verdict = "CLEARS" if v > CEIL else ""
    print(f"  {lbl:<44}{('over' if sd=='o' else 'under'):>6}{n:>7}{v:>+8.1f}%   {verdict}")
print("")
cl = [x for x in real if x[0] > CEIL]
print(f"  cells clearing the ceiling: {len(cl)} of {len(real)}")
print("")
print("="*104)
print("  THE MODEL S RECIPE, APPLIED BOARD-WIDE - can we bet ANY player this way?")
print("="*104)
def show(sel, lbl, sd="o"):
    g = [r for r in Q if sel(r)]
    if len(g) < 40: print(f"  {lbl:<50} n={len(g)} too few"); return
    wk, ok = sd+"_won", sd+"_od"
    n = len(g); w = sum(1 for r in g if r[wk]); v = roi(g, sd)
    bgg = collections.defaultdict(list)
    for r in g: bgg[r["gid"]].append(r)
    k = list(bgg); o = []
    for _ in range(2000):
        s = [x for p in [random.choice(k) for _ in k] for x in bgg[p]]
        o.append(100*sum((x[ok]-1) if x[wk] else -1.0 for x in s)/len(s))
    o.sort()
    print(f"  {lbl:<50} n={n:<5}{100*w/n:>6.1f}%{v:>+8.1f}%  95CI [{o[50]:+6.1f},{o[1949]:+6.1f}]")
show(lambda r: r["cush"] >= 3, "  cushion 3+ (the overshoot rule), any player")
show(lambda r: r["cush"] >= 3 and r["star"], "  cushion 3+ AND star (Model S recipe)")
show(lambda r: r["cush"] >= 3 and r["star"] and r["mk"] in ("pra", "pr", "pts"),
     "  cushion 3+ AND star AND pra/pr/pts")
show(lambda r: r["cush"] >= 3 and r["star"] and r["opp"] is not None and r["opp"] <= 0,
     "  cushion 3+ AND star AND opp shaded down")
print("")
print("  Model S itself returns about +15% on 90 bets. If the same recipe applied board-wide")
print("  returns near zero, then the three signals are contributing something the recipe alone")
print("  does not capture - and volume cannot be bought by copying the recipe outward.")
