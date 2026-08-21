# shade2.py - medians rebuilt the engine's way, then three questions at once.
# ---------------------------------------------------------------------------------------------
# THE FIX. Every cushion and shade figure produced earlier today used a median over a player's
# last 10 games regardless of team. overshoot_overs does not: it filters to CURRENT-TEAM games
# first (cloud_xbet.py:434), which is what stops an All-Star appearance or a mid-season trade from
# poisoning the number. Allisha Gray was the tell - 24.0 unfiltered against 26.0 on ATL only,
# entirely because of one All-Star game, which moved her from cushion +1.5 to +3.5 and across the
# boundary the whole shade finding is built on. Everything below uses med_team().
#
# THREE QUESTIONS:
#
#  1 SHADE, REDONE. Does the opponent-shade result survive the corrected median, at the game-level
#    null that is correct for a game-level label?
#
#  2 IS THE DECAY OURS, OR THE LEAGUE'S? Model S ran +37.1% in early July and +3.6% in August. If
#    OUR edge is decaying, the board's own overs should be unaffected. If the whole LEAGUE started
#    scoring less, every over decays together and there is nothing wrong with the model at all -
#    we are simply betting overs into a slower league. That is a completely different diagnosis
#    with a completely different fix, and it is the control that separates them.
#
#  3 DOES THE SCORING ENVIRONMENT MOVE PLAYER PROPS? The engine already believes it does - it
#    drops pts/PRA overshoot-overs when the team total is low, but keeps assist/rebound markets,
#    on the theory that rebounds rise on misses and assists are flat. That guard has never been
#    tested. With a board-implied total we now have near-full coverage to test it.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260820)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
SIGS = ("flip", "hotover", "overshoot"); BET_MKTS = ("pra", "pr", "pts")
ALLMK = ("pts", "pr", "pra", "pa", "ra", "reb", "ast")

tip_on, gof, oppof, dateof = {}, {}, {}, {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    tip_on[(hm, d2)] = t2; tip_on[(aw, d2)] = t2
    gof[(hm, t2)] = gid; gof[(aw, t2)] = gid
    oppof[(hm, t2)] = aw; oppof[(aw, t2)] = hm
    dateof[t2] = d2

_mc = {}
def med_team(pl, mk, gt):
    """THE FIX: last 10 in this market, CURRENT-TEAM games only, strictly before gt."""
    k = (pl, mk, gt)
    if k in _mc: return _mc[k]
    g = [r for r in hist.get(pl, []) if r["tip"] < gt]
    out = None
    if g:
        cur = g[-1]["tm"]; g = [r for r in g if r["tm"] == cur]
        if len(g) >= 5: out = statistics.median([r[mk] for r in g[-10:]])
    _mc[k] = out
    return out

shade = collections.defaultdict(list)
for (pl, mk, gt), sdq in side.items():
    if mk != "pts" or "Over" not in sdq: continue
    tm = teamof.get(pl)
    if not tm: continue
    m = med_team(pl, "pts", gt)
    if m is not None: shade[(tm, gt)].append(sdq["Over"][1] - m)

# board-implied total: sum of both teams' posted points lines
ptsline = collections.defaultdict(list)
for (pl, mk, gt), sdq in side.items():
    if mk == "pts" and "Over" in sdq and teamof.get(pl):
        ptsline[(teamof[pl], gt)].append(sdq["Over"][1])

# ---- every gradable two-sided quote, with corrected features -------------------------------
Q = []
for (pl, mk, gt), sdq in side.items():
    if mk not in ALLMK or "Over" not in sdq or "Under" not in sdq: continue
    if abs(sdq["Over"][1] - sdq["Under"][1]) > 0.01: continue
    now = pgrow.get((pl, gt))
    tm = teamof.get(pl)
    if not now or mk not in now or not tm: continue
    ln = sdq["Over"][1]
    if now[mk] == ln: continue
    md = med_team(pl, mk, gt)
    if md is None: continue
    op = oppof.get((tm, gt)); o_s = shade.get((op, gt), [])
    a, b = ptsline.get((tm, gt), []), ptsline.get((op, gt), [])
    pv = prevline.get((pl, mk, gt))
    Q.append(dict(pl=pl, mk=mk, gt=gt, gid=gof[(tm, gt)], tm=tm, date=dateof.get(gt, ""),
                  ln=ln, o_od=sdq["Over"][2], u_od=sdq["Under"][2],
                  o_won=now[mk] > ln, u_won=now[mk] < ln,
                  cush=md - ln, star=(pv is not None and ln - pv < 0.5),
                  opp=(statistics.mean(o_s) if len(o_s) >= 3 else None),
                  btot=((sum(a)+sum(b)) if (len(a) >= 4 and len(b) >= 4) else None)))
print(f"{len(Q)} two-sided quotes, medians CURRENT-TEAM filtered, {len({r['gid'] for r in Q})} games")

MS = []
for r in load("graded_bets.csv"):
    if (r.get("result") or "").upper() not in ("WIN", "LOSS"): continue
    src, mk, pl = (r.get("src") or ""), (r.get("market") or ""), (r.get("player") or "").lower()
    if src not in SIGS or mk not in BET_MKTS: continue
    tm = teamof.get(pl)
    gt = tip_on.get((tm, r.get("date") or "")) if tm else None
    if not gt: continue
    q = next((x for x in Q if x["pl"] == pl and x["mk"] == mk and x["gt"] == gt), None)
    if not q or not q["star"]: continue
    MS.append(dict(q, src=src, ret=((q["o_od"]-1) if q["o_won"] else -1.0)))
best = {}
for r in sorted(MS, key=lambda x: -x["o_od"]): best.setdefault((r["pl"], r["gt"]), r)
MS = sorted(best.values(), key=lambda r: r["date"])
print(f"Model S after the fix: {len(MS)} bets")
print("")

def roi(rows, sd="o"):
    if not rows: return 0.0
    wk, ok = sd+"_won", sd+"_od"
    return 100*sum((r[ok]-1) if r[wk] else -1.0 for r in rows)/len(rows)
def hit(rows, sd="o"): return 100*sum(1 for r in rows if r[sd+"_won"])/len(rows) if rows else 0
def gboot(rows, sd="o", T=2500):
    bg = collections.defaultdict(list)
    for r in rows: bg[r["gid"]].append(r)
    k = list(bg); o = []
    for _ in range(T): o.append(roi([x for p in [random.choice(k) for _ in k] for x in bg[p]], sd))
    o.sort(); return o[int(T*.025)], o[int(T*.975)]
def show(rows, lbl, sd="o", minn=25):
    if len(rows) < minn: print(f"  {lbl:<48} n={len(rows)} too few"); return
    lo, hi = gboot(rows, sd)
    print(f"  {lbl:<48} n={len(rows):<5}{hit(rows,sd):>6.1f}%{roi(rows,sd):>+8.1f}%  95CI [{lo:+6.1f},{hi:+6.1f}]")

print("="*104)
print("  1. SHADE, WITH THE CORRECTED MEDIAN")
print("="*104)
A = [r for r in MS if r["opp"] is not None]
om = statistics.median(r["opp"] for r in A) if A else 0
show([r for r in A if r["opp"] <= om], "  MODEL S, opponent shaded DOWN", minn=15)
show([r for r in A if r["opp"] > om],  "  MODEL S, opponent shaded UP", minn=15)
# game-level label permutation
gl = {}
for r in A: gl[(r["gid"], r["tm"])] = r["opp"]
keys = list(gl); vals = [gl[k] for k in keys]
real = roi([r for r in A if r["opp"] <= om]) - roi([r for r in A if r["opp"] > om])
T = 5000; beat = 0; sims = []
for _ in range(T):
    random.shuffle(vals); lab = dict(zip(keys, vals))
    a = [r for r in A if lab[(r["gid"], r["tm"])] <= om]
    b = [r for r in A if lab[(r["gid"], r["tm"])] > om]
    if len(a) < 10 or len(b) < 10: continue
    d = roi(a) - roi(b); sims.append(d)
    if d >= real: beat += 1
print(f"    gap {real:+.1f} points   game-level permutation p = {beat/max(len(sims),1):.4f}"
      f"   (was 0.0186 with the poisoned median)")
print("")
DEEP = [r for r in Q if r["cush"] >= 3 and r["opp"] is not None]
show([r for r in DEEP if r["opp"] <= 0], "  BOARD-WIDE cushion 3+, opp shaded DOWN")
show([r for r in DEEP if r["opp"] > 0],  "  BOARD-WIDE cushion 3+, opp shaded UP")
gl2 = {}
for r in DEEP: gl2[(r["gid"], r["tm"])] = r["opp"]
k2 = list(gl2); v2 = [gl2[k] for k in k2]
real2 = roi([r for r in DEEP if r["opp"] <= 0]) - roi([r for r in DEEP if r["opp"] > 0])
beat2 = 0; s2 = []
for _ in range(T):
    random.shuffle(v2); lab = dict(zip(k2, v2))
    a = [r for r in DEEP if lab[(r["gid"], r["tm"])] <= 0]
    b = [r for r in DEEP if lab[(r["gid"], r["tm"])] > 0]
    if len(a) < 40 or len(b) < 40: continue
    d = roi(a) - roi(b); s2.append(d)
    if d >= real2: beat2 += 1
print(f"    gap {real2:+.1f} points   game-level permutation p = {beat2/max(len(s2),1):.4f}"
      f"   (was 0.0816 with the poisoned median)")
print("")
print("="*104)
print("  2. IS THE DECAY OURS, OR THE LEAGUE'S?  - the control that separates them")
print("="*104)
dts = sorted({r["date"] for r in Q if r["date"]})
cuts = [dts[0], dts[len(dts)//3], dts[2*len(dts)//3], dts[-1]]
print(f"  {'period':<22}{'MODEL S':>26}{'BOARD overs':>26}{'league pts/game':>18}")
for i in range(3):
    lo, hi = cuts[i], cuts[i+1]
    ms = [r for r in MS if lo <= r["date"] <= hi]
    bd = [r for r in Q if lo <= r["date"] <= hi]
    gids = {r["gid"] for r in bd}
    tot = []
    for gid in gids:
        d2, t2, hm, aw = gmeta[gid]
        hs, as_ = f(load and None) if False else (None, None)
    scores = []
    for gid in gids:
        g = gmeta[gid]
        pass
    rows = [x for x in load("data/games_2026.csv") if x.get("game_id") in gids]
    for x in rows:
        a_, h_ = f(x.get("away_score")), f(x.get("home_score"))
        if a_ is not None and h_ is not None: scores.append(a_ + h_)
    msr = f"n={len(ms):<4}{roi(ms):+6.1f}%" if len(ms) >= 10 else f"n={len(ms)} few"
    bdr = f"n={len(bd):<5}{roi(bd):+6.1f}%" if len(bd) >= 50 else f"n={len(bd)} few"
    lg = f"{statistics.mean(scores):.1f}" if scores else "-"
    print(f"  {lo}..{hi:<10}{msr:>26}{bdr:>26}{lg:>18}")
print("")
print("  if BOARD overs fall with Model S, the league slowed and every over suffered together.")
print("  if board overs are flat while Model S falls, the decay is ours and the book caught up.")
print("")
print("="*104)
print("  3. DOES THE SCORING ENVIRONMENT MOVE PLAYER PROPS?")
print("="*104)
BT = [r for r in Q if r["btot"] is not None]
v = sorted(r["btot"] for r in BT)
lo3, hi3 = v[len(v)//3], v[2*len(v)//3]
print(f"  board-implied total terciles at {lo3:.1f} / {hi3:.1f}")
for lbl, sel in ((f"  LOW total (<= {lo3:.0f})", lambda r: r["btot"] <= lo3),
                 (f"  MID total", lambda r: lo3 < r["btot"] <= hi3),
                 (f"  HIGH total (> {hi3:.0f})", lambda r: r["btot"] > hi3)):
    g = [r for r in BT if sel(r)]
    show(g, lbl + " : all overs")
print("")
print("  the engine's guard says pts/PRA are total-sensitive and reb/ast are immune. test it:")
TRAP = ("pts", "pra"); SAFE = ("reb", "ast", "ra", "pa")
for grp, nm in ((TRAP, "pts+pra (engine calls these TRAPS)"), (SAFE, "reb/ast/ra/pa (engine calls these SAFE)")):
    lo_ = [r for r in BT if r["mk"] in grp and r["btot"] <= lo3]
    hi_ = [r for r in BT if r["mk"] in grp and r["btot"] > hi3]
    if len(lo_) < 25 or len(hi_) < 25: continue
    print(f"    {nm}")
    print(f"      overs in LOW-total games  n={len(lo_):<5}{hit(lo_):>6.1f}%{roi(lo_):>+8.1f}%")
    print(f"      overs in HIGH-total games n={len(hi_):<5}{hit(hi_):>6.1f}%{roi(hi_):>+8.1f}%")
    print(f"      swing {roi(hi_)-roi(lo_):+.1f} points")
print("")
print("="*104)
print("  4. SHOULD WE FADE LATE SEASON? - unders, by period")
print("="*104)
for i in range(3):
    lo, hi = cuts[i], cuts[i+1]
    bd = [r for r in Q if lo <= r["date"] <= hi]
    if len(bd) < 50: continue
    print(f"  {lo}..{hi}   board OVERS {roi(bd,'o'):+6.1f}%   board UNDERS {roi(bd,'u'):+6.1f}%"
          f"   (margin means both can lose)")
