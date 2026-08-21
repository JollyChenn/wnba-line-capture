# cross_hunt.py - two untested directions: props -> game markets, and the book vs itself.
# ---------------------------------------------------------------------------------------------
#  A  THE BOOK vs ITSELF. 1xbet posts pts, reb, ast AND the combos (pr, pa, ra, pra) for the same
#     player. The combos are sums, so the lines must add up: pts_ln + reb_ln ~ pr_ln. If they do
#     not - say pts 14.5 + reb 6.5 = 21 but PR is posted at 18.5 - the book disagrees WITH ITSELF
#     and one of the two numbers is wrong. Bet the cheap side of the inconsistency: combo line
#     BELOW the sum of parts -> combo OVER; above -> combo UNDER. This needs no sharp reference,
#     no median, no model - it is internal arithmetic, and it has never been checked.
#     (Half-line note: a combo of two .5 lines lands on a whole number, so the sum runs ~0.5 high
#     of the combo's natural posting. The threshold below is >=1.5 to sit clear of that.)
#
#  B  PROPS -> GAME MARKETS. The reverse of everything tried so far. The player board is 200+
#     numbers per slate; the game total is one. If the prop board's implied scoring disagrees
#     with Pinnacle's posted total, which one knows? Bet the game TOTAL in the direction the prop
#     board points, graded against the realised score. Same for the spread via the difference of
#     team sums. Grading assumes a standard 1.91 total/spread price - stated, not hidden.
#
# Nulls: A at the player block (the inconsistency is a player-market attribute), B at the game
# level (one bet per game, so a plain binomial CI is honest).
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260822)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
gof, oppof = {}, {}
realtot, realmarg = {}, {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    gof[(hm, t2)] = gid; gof[(aw, t2)] = gid; oppof[(hm, t2)] = aw; oppof[(aw, t2)] = hm
for g in load("data/games_2026.csv"):
    a_, h_ = f(g.get("away_score")), f(g.get("home_score"))
    if a_ is not None and h_ is not None:
        realtot[g.get("game_id")] = a_ + h_
        realmarg[g.get("game_id")] = h_ - a_          # signed, home minus away
GL = collections.defaultdict(dict)
for r in load("gamelines.csv"):
    st = (r.get("start") or "")[:10].replace("-", "")
    tmn = (r.get("teams") or "").split("|")
    if len(tmn) != 2: continue
    ab = tuple(sorted(FULL.get(t.strip(), "") for t in tmn))
    if "" in ab: continue
    cap, pts = ts(r.get("captured_utc")), f(r.get("points"))
    if not cap: continue
    s = GL[(st, ab)]
    if r.get("type") == "total" and pts is not None and ("tot" not in s or cap > s["tot"][0]):
        s["tot"] = (cap, pts)

# ============================ A. THE BOOK vs ITSELF =========================================
COMBOS = {"pr": ("pts", "reb"), "pa": ("pts", "ast"), "ra": ("reb", "ast"),
          "pra": ("pts", "reb", "ast")}
A = []
for (pl, mk, gt), sdq in side.items():
    if mk not in COMBOS or "Over" not in sdq or "Under" not in sdq: continue
    if abs(sdq["Over"][1] - sdq["Under"][1]) > 0.01: continue
    parts = []
    for p_ in COMBOS[mk]:
        ps = side.get((pl, p_, gt))
        if not ps or "Over" not in ps: parts = None; break
        parts.append(ps["Over"][1])
    if parts is None: continue
    now = pgrow.get((pl, gt)); tm = teamof.get(pl)
    if not now or mk not in now or not tm: continue
    ln = sdq["Over"][1]
    if now[mk] == ln: continue
    inc = sum(parts) - ln                              # + : combo posted LOW vs its own parts
    A.append(dict(pl=pl, mk=mk, gt=gt, gid=gof[(tm, gt)], ln=ln, inc=inc,
                  o_od=sdq["Over"][2], u_od=sdq["Under"][2],
                  o_won=now[mk] > ln, u_won=now[mk] < ln))
def ret(r, sd): return ((r[sd+"_od"]-1) if r[sd+"_won"] else -1.0)
def roi2(rows): return 100*sum(x[1] for x in rows)/len(rows) if rows else 0.0
def pboot2(rows, T=2500):
    bp = collections.defaultdict(list)
    for r, v in rows: bp[r["pl"]].append((r, v))
    k = list(bp); o = []
    for _ in range(T): o.append(roi2([x for p in [random.choice(k) for _ in k] for x in bp[p]]))
    o.sort(); return o[int(T*.025)], o[int(T*.975)]
print("="*100)
print("  A. THE BOOK vs ITSELF - combo line vs the sum of its own parts")
print("="*100)
print(f"  {len(A)} combo quotes where every part is also posted")
dist = collections.Counter(round(r["inc"]*2)/2 for r in A)
print("  inconsistency (parts minus combo): " + ", ".join(
    f"{k:+.1f}:{v}" for k, v in sorted(dist.items()) if v >= 20))
for thr in (1.5, 2.0):
    bets = ([(r, ret(r, "o")) for r in A if r["inc"] >= thr] +
            [(r, ret(r, "u")) for r in A if r["inc"] <= -thr])
    hits = ([1 if r["o_won"] else 0 for r in A if r["inc"] >= thr] +
            [1 if r["u_won"] else 0 for r in A if r["inc"] <= -thr])
    if len(bets) < 25:
        print(f"    |inconsistency| >= {thr}: n={len(bets)} too few"); continue
    lo, hi = pboot2(bets)
    star = "  <<<" if lo > 0 else ""
    print(f"    bet the cheap side, |inc| >= {thr:<4} n={len(bets):<5}"
          f"{100*sum(hits)/len(hits):>6.1f}%{roi2(bets):>+8.1f}%  [{lo:+6.1f},{hi:+6.1f}]{star}")
ctrl = [(r, ret(r, "o")) for r in A if abs(r["inc"]) < 1.0]
if len(ctrl) >= 25:
    print(f"    control, consistent combos (over)      n={len(ctrl):<5}{'':>6}{roi2(ctrl):>+8.1f}%")
print("")

# ============================ B. PROPS -> GAME MARKETS ======================================
ptsline = collections.defaultdict(list)
for (pl, mk, gt), sdq in side.items():
    if mk == "pts" and "Over" in sdq and teamof.get(pl):
        ptsline[(teamof[pl], gt)].append(sdq["Over"][1])
print("="*100)
print("  B. PROPS -> GAME TOTAL   (graded vs realised score, priced at a flat 1.91)")
print("="*100)
G = []
for gid, (d2, t2, hm, aw) in gmeta.items():
    if gid not in realtot: continue
    s = GL.get((d2, tuple(sorted((hm, aw)))), {})
    tot = s.get("tot", (None, None))[1]
    if tot is None: continue
    a, b = ptsline.get((hm, t2), []), ptsline.get((aw, t2), [])
    if len(a) < 4 or len(b) < 4: continue
    # coverage-normalised: board's per-line mean scaled to 5 starters x 2 x (bench share ~1.35)
    impl = (statistics.mean(a) + statistics.mean(b)) * 5 * 1.35
    G.append(dict(gid=gid, date=d2, tot=tot, impl=impl, diff=impl - tot,
                  real=realtot[gid]))
print(f"  {len(G)} games with a Pinnacle total, 4+ pts lines each side, and a final score")
if len(G) >= 25:
    # calibration first: does the board's implied number even track the real total,
    # BEYOND what Pinnacle's own total already says?
    xs = [g["diff"] for g in G]; ys = [g["real"] - g["tot"] for g in G]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((x-mx)*(y-my) for x, y in zip(xs, ys))
    den = math.sqrt(sum((x-mx)**2 for x in xs)*sum((y-my)**2 for y in ys))
    r_ = num/den if den else 0
    print(f"  corr( board-implied minus Pinnacle , realised minus Pinnacle ) = {r_:+.3f}")
    print("  (this is the ONLY number that matters: it asks whether the prop board knows")
    print("   anything Pinnacle's total does not. near zero = it does not.)")
    for thr in (5.0, 10.0):
        bets = [(g, 1 if (g["real"] > g["tot"]) == (g["diff"] > 0) else 0)
                for g in G if abs(g["diff"]) >= thr and g["real"] != g["tot"]]
        if len(bets) < 15: print(f"    |board vs total| >= {thr:>4}: n={len(bets)} too few"); continue
        w = sum(x[1] for x in bets); n = len(bets)
        u = sum((0.91 if x[1] else -1.0) for x in bets)
        se = math.sqrt(0.25/n)
        print(f"    bet total toward the board, edge>={thr:>4}  n={n:<4}{100*w/n:>6.1f}%"
              f"  ROI {100*u/n:+6.1f}%   (needs 52.4%; +/-{100*1.96*se:.0f}pp at this n)")
print("")
print("="*100)
print("  B2. PROPS -> SPREAD   (same idea, home-minus-away)")
print("="*100)
S2 = []
for gid, (d2, t2, hm, aw) in gmeta.items():
    if gid not in realmarg: continue
    a, b = ptsline.get((hm, t2), []), ptsline.get((aw, t2), [])
    if len(a) < 4 or len(b) < 4: continue
    S2.append(dict(gid=gid, impl=(statistics.mean(a) - statistics.mean(b)) * 5 * 1.35,
                   real=realmarg[gid]))
if len(S2) >= 30:
    xs = [g["impl"] for g in S2]; ys = [g["real"] for g in S2]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((x-mx)*(y-my) for x, y in zip(xs, ys))
    den = math.sqrt(sum((x-mx)**2 for x in xs)*sum((y-my)**2 for y in ys))
    print(f"  {len(S2)} games: corr(board-implied margin, realised margin) = {num/den if den else 0:+.3f}")
    w = sum(1 for g in S2 if (g["impl"] > 0) == (g["real"] > 0))
    print(f"  board-implied favourite WON the game: {w} of {len(S2)} = {100*w/len(S2):.1f}%")
    print("  (an ML bet needs ~its own odds' breakeven; this only says whether the board can")
    print("   pick winners at all. To beat the ML market it must beat the PRICE, tested next)")
    # vs Pinnacle spread where we have it
    hit_v_line = []
    for g in S2:
        gid = g["gid"]; d2, t2, hm, aw = gmeta[gid]
        s = GL.get((d2, tuple(sorted((hm, aw)))), {})
        spr = s.get("spr", (None, None))[1]
        if spr is None: continue
        # does the board know the margin better than the posted spread magnitude?
        hit_v_line.append(1 if abs(g["impl"]) - spr == 0 else
                          (1 if (abs(g["real"]) > spr) == (abs(g["impl"]) > spr) else 0))
    if len(hit_v_line) >= 20:
        print(f"  vs the posted spread magnitude: right on {sum(hit_v_line)} of {len(hit_v_line)}"
              f" = {100*sum(hit_v_line)/len(hit_v_line):.1f}%   (needs 52.4%)")
