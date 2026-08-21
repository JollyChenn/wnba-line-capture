# fresh_hunt.py - clean-slate pattern hunt. No Model S. Board-wide, both sides, mechanism first.
# ---------------------------------------------------------------------------------------------
# Every family below is written down WITH its mechanism BEFORE any result is looked at, because
# the season's graveyard is full of scanned cells. A soft book misprices props for knowable,
# boring operational reasons - these are the five with a real story:
#
#  A  SHARP DIVERGENCE. pinn_snapshots.csv holds Pinnacle's player lines (sharp, real-money
#     limits). If 1xbet's line differs by a point or more, 1xbet is the one that is wrong -
#     that is the whole soft-book business model. Bet TOWARD Pinnacle at 1xbet's price.
#     Never tested in this repo as a standalone signal; only ever used as an engine drop-guard.
#  B  ODDS LEAN. At the same line 1xbet often quotes asym odds (Over 1.95 / Under 1.75). That
#     asymmetry is the book's own probability estimate. Is it calibrated on its own board?
#     If following the lean loses AND fading it loses, the lean is pure margin. If one side
#     pays, the book is leaning for a reason (following sharp flow) or overreacting (fadeable).
#  C  REST / BACK-TO-BACK. Fatigue is real and schedules are public. If the book prices props
#     off season medians without a fatigue haircut, overs on tired legs should underperform.
#  D  COPIED LINE + FORM SHIFT. The laziest way to set a line is to copy her last game's line.
#     If the line is IDENTICAL to her previous game AND her recent form moved meaningfully,
#     the copy ignored new information. Bet in the direction of the form move.
#  E  BLOWOUT DISTORTION. A player's last game in a 15+ point blowout has garbage-time minutes
#     (starters sat, benches feasted). If the book's next line chases that distorted stat line,
#     it overshoots: fade the direction of the blowout distortion.
#
# DISCIPLINE: noise ceiling computed FIRST over the full grid of cells this script looks at,
# with game-level relabelling. Real two-sided prices always. Current-team medians (the engine's
# way - the All-Star bug from 08-20 is not being repeated). Player/game-block bootstrap CIs.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260821)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
ALLMK = ("pts", "pr", "pra", "pa", "ra", "reb", "ast")
gof, oppof = {}, {}
realmarg = {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    gof[(hm, t2)] = gid; gof[(aw, t2)] = gid; oppof[(hm, t2)] = aw; oppof[(aw, t2)] = hm
for g in load("data/games_2026.csv"):
    a_, h_ = f(g.get("away_score")), f(g.get("home_score"))
    if a_ is not None and h_ is not None: realmarg[g.get("game_id")] = abs(h_ - a_)

_mc = {}
def med_team(pl, mk, gt):
    k = (pl, mk, gt)
    if k in _mc: return _mc[k]
    g = [r for r in hist.get(pl, []) if r["tip"] < gt]
    out = None
    if g:
        cur = g[-1]["tm"]; g2 = [r for r in g if r["tm"] == cur]
        if len(g2) >= 5: out = statistics.median([r[mk] for r in g2[-10:]])
    _mc[k] = out
    return out
def form3(pl, mk, gt):
    g = [r for r in hist.get(pl, []) if r["tip"] < gt]
    if len(g) < 3: return None
    return statistics.mean([r[mk] for r in g[-3:]])
def lastgame(pl, gt):
    g = [r for r in hist.get(pl, []) if r["tip"] < gt]
    return g[-1] if g else None
def restdays(pl, gt):
    g = [r for r in hist.get(pl, []) if r["tip"] < gt]
    if not g: return None
    return (gt - g[-1]["tip"]).total_seconds() / 86400

# Pinnacle player lines: last capture BEFORE her game tip, per (player, market)
pin = collections.defaultdict(list)
for r in load("pinn_snapshots.csv"):
    cap, ln = ts(r.get("captured_utc")), f(r.get("pinn_line"))
    pl, mk = (r.get("player") or "").lower(), r.get("market")
    if cap and ln is not None and pl and mk: pin[(pl, mk)].append((cap, ln))
for v in pin.values(): v.sort()
def pinn_line(pl, mk, gt):
    got = [x for x in pin.get((pl, mk), []) if x[0] <= gt and (gt - x[0]).total_seconds() < 36*3600]
    return got[-1][1] if got else None
def pinn_combo(pl, mk, gt):
    if mk in ("pts", "reb", "ast"): return pinn_line(pl, mk, gt)
    parts = {"pr": ("pts", "reb"), "pa": ("pts", "ast"), "ra": ("reb", "ast"),
             "pra": ("pts", "reb", "ast")}[mk]
    vs = [pinn_line(pl, p, gt) for p in parts]
    return sum(vs) if all(v is not None for v in vs) else None

# ---- the universe ---------------------------------------------------------------------------
Q = []
for (pl, mk, gt), sdq in side.items():
    if mk not in ALLMK or "Over" not in sdq or "Under" not in sdq: continue
    if abs(sdq["Over"][1] - sdq["Under"][1]) > 0.01: continue
    now = pgrow.get((pl, gt)); tm = teamof.get(pl)
    if not now or mk not in now or not tm: continue
    ln = sdq["Over"][1]
    if now[mk] == ln: continue
    gid = gof[(tm, gt)]
    md = med_team(pl, mk, gt); f3 = form3(pl, mk, gt)
    lg = lastgame(pl, gt); rd = restdays(pl, gt)
    pv = prevline.get((pl, mk, gt))
    pn = pinn_combo(pl, mk, gt)
    lgmarg = realmarg.get(next((g2 for g2, (dd, tt, hh, aa) in gmeta.items()
                                if lg and tt == lg["tip"] and lg["tm"] in (hh, aa)), None)) if lg else None
    Q.append(dict(pl=pl, mk=mk, gt=gt, gid=gid, tm=tm,
                  ln=ln, o_od=sdq["Over"][2], u_od=sdq["Under"][2],
                  o_won=now[mk] > ln, u_won=now[mk] < ln,
                  med=md, gap=(pn - ln) if pn is not None else None,   # sharp minus soft
                  lean=sdq["Under"][2] - sdq["Over"][2],               # >0: book leans OVER
                  rest=rd, copied=(pv is not None and abs(ln - pv) < 0.01),
                  fshift=(f3 - md) if (f3 is not None and md is not None) else None,
                  lgdist=((lg[mk] - md) if (lg and md is not None and mk in lg) else None),
                  lgblow=(lgmarg is not None and lgmarg >= 15)))
print(f"{len(Q)} two-sided quotes; pinnacle gap on {sum(1 for r in Q if r['gap'] is not None)},"
      f" rest on {sum(1 for r in Q if r['rest'] is not None)}")
print("")

def roi(rows, sd): return 100*sum((r[sd+'_od']-1) if r[sd+'_won'] else -1.0 for r in rows)/len(rows) if rows else 0
def hit(rows, sd): return 100*sum(1 for r in rows if r[sd+'_won'])/len(rows) if rows else 0
def gboot(rows, sd, T=2000):
    bg = collections.defaultdict(list)
    for r in rows: bg[r["gid"]].append(r)
    k = list(bg); o = []
    for _ in range(T): o.append(roi([x for p in [random.choice(k) for _ in k] for x in bg[p]], sd))
    o.sort(); return o[int(T*.025)], o[int(T*.975)]
def show(rows, lbl, sd, minn=60):
    if len(rows) < minn: print(f"    {lbl:<52} n={len(rows)} too few"); return None
    lo, hi = gboot(rows, sd)
    star = "  <<<" if lo > 0 else ""
    print(f"    {lbl:<52} n={len(rows):<5}{hit(rows,sd):>6.1f}%{roi(rows,sd):>+8.1f}%  [{lo:+6.1f},{hi:+6.1f}]{star}")
    return roi(rows, sd)

# ---- THE GRID, declared up front so the ceiling covers everything ---------------------------
def grid():
    C = []
    C.append(("A gap<=-1.5 (xbet HIGH, sharp low): UNDER", lambda r: r["gap"] is not None and r["gap"] <= -1.5, "u"))
    C.append(("A gap<=-1.0: UNDER", lambda r: r["gap"] is not None and r["gap"] <= -1.0, "u"))
    C.append(("A gap>=+1.5 (xbet LOW, sharp high): OVER", lambda r: r["gap"] is not None and r["gap"] >= 1.5, "o"))
    C.append(("A gap>=+1.0: OVER", lambda r: r["gap"] is not None and r["gap"] >= 1.0, "o"))
    C.append(("A |gap|<0.5 (books agree): OVER", lambda r: r["gap"] is not None and abs(r["gap"]) < 0.5, "o"))
    C.append(("B book leans OVER (>=0.06): follow OVER", lambda r: r["lean"] >= 0.06, "o"))
    C.append(("B book leans OVER: fade UNDER", lambda r: r["lean"] >= 0.06, "u"))
    C.append(("B book leans UNDER (<=-0.06): follow UNDER", lambda r: r["lean"] <= -0.06, "u"))
    C.append(("B book leans UNDER: fade OVER", lambda r: r["lean"] <= -0.06, "o"))
    C.append(("C back-to-back (rest<1.2d): UNDER", lambda r: r["rest"] is not None and r["rest"] < 1.2, "u"))
    C.append(("C back-to-back: OVER", lambda r: r["rest"] is not None and r["rest"] < 1.2, "o"))
    C.append(("C long rest (>=3d): OVER", lambda r: r["rest"] is not None and r["rest"] >= 3, "o"))
    C.append(("C long rest: UNDER", lambda r: r["rest"] is not None and r["rest"] >= 3, "u"))
    C.append(("D copied line + form UP >=3: OVER", lambda r: r["copied"] and r["fshift"] is not None and r["fshift"] >= 3, "o"))
    C.append(("D copied line + form DOWN <=-3: UNDER", lambda r: r["copied"] and r["fshift"] is not None and r["fshift"] <= -3, "u"))
    C.append(("D copied line, form flat: OVER (control)", lambda r: r["copied"] and r["fshift"] is not None and abs(r["fshift"]) < 3, "o"))
    C.append(("E last game blowout + stat spike >=4: UNDER", lambda r: r["lgblow"] and r["lgdist"] is not None and r["lgdist"] >= 4, "u"))
    C.append(("E last game blowout + stat crater <=-4: OVER", lambda r: r["lgblow"] and r["lgdist"] is not None and r["lgdist"] <= -4, "o"))
    C.append(("E blowout spike, no blowout filter (ctrl): UNDER", lambda r: not r["lgblow"] and r["lgdist"] is not None and r["lgdist"] >= 4, "u"))
    return C
GRID = grid()

# ceiling: relabel game outcomes, rerun every cell, take the best
bgall = collections.defaultdict(list)
for r in Q: bgall[r["gid"]].append(r)
gkeys = list(bgall)
peaks = []
for _ in range(300):
    pool = [(r["o_won"], r["u_won"]) for r in Q]; random.shuffle(pool)
    for r, v in zip(Q, pool): r["_o"], r["_u"] = v
    best = -99
    for lbl, sel, sd in GRID:
        g = [r for r in Q if sel(r)]
        if len(g) < 60: continue
        wk = "_" + sd
        v = 100*sum((r[sd+'_od']-1) if r[wk] else -1.0 for r in g)/len(g)
        best = max(best, v)
    if best > -99: peaks.append(best)
peaks.sort()
CEIL = peaks[int(len(peaks)*0.95)]
print("="*104)
print(f"  NOISE CEILING FIRST: {len(GRID)} declared cells, outcome-shuffled 300x -> p95 best cell {CEIL:+.1f}%")
print(f"  (quote-level shuffle - too TIGHT for game-level families C/E; survivors get game-level nulls)")
print("="*104)
print("")
results = []
fams = {"A": "A. SHARP DIVERGENCE (1xbet line vs Pinnacle)", "B": "B. ODDS LEAN",
        "C": "C. REST / BACK-TO-BACK", "D": "D. COPIED LINE + FORM SHIFT", "E": "E. BLOWOUT DISTORTION"}
cur = ""
for lbl, sel, sd in GRID:
    if lbl[0] != cur:
        cur = lbl[0]; print("  " + fams[cur])
    g = [r for r in Q if sel(r)]
    v = show(g, lbl[2:], sd)
    if v is not None: results.append((v, lbl, len(g)))
    if lbl[0] != (GRID[min(GRID.index((lbl, sel, sd))+1, len(GRID)-1)][0][0]): print("")
print("")
print("="*104)
print("  CELLS ABOVE THE CEILING")
print("="*104)
win = [x for x in results if x[0] > CEIL]
for v, lbl, n in sorted(win, reverse=True): print(f"    {lbl:<56} n={n:<5} ROI {v:+.1f}%")
if not win: print("    none")
