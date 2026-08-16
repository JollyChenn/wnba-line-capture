# sharp_edge.py - the purest form of the thesis: buy where 1xbet's price beats Pinnacle's FAIR.
# ---------------------------------------------------------------------------------------------
# Everything else in this project is a proxy. Our whole reason for betting 1xbet is that it is
# slow on player props - measured at 7.0% below Pinnacle fair, t=-42.9. But we have never used
# that gap DIRECTLY as a signal. We have used the engine's own heuristics (flip/overshoot/hotover)
# and then filtered them with the star.
#
# pinn_snapshots.csv carries Pinnacle's LINE and its DE-VIGGED FAIR DECIMAL ODDS per player-market
# -side. So for any 1xbet quote at the SAME line we can compute the true edge outright:
#       edge = xbet_decimal / pinnacle_fair_decimal - 1
# A positive edge means 1xbet is paying more than the sharp thinks the outcome is worth. That is
# the definition of a good bet, and it needs no model at all.
#
# THE TRAP TO AVOID, and it has caught me four times this week: only compare quotes at the SAME
# LINE. A price at 18.5 is not comparable to a price at 20.5. Rows where the two books differ on
# the number are counted separately, because a line disagreement is a different (and interesting)
# signal from a price disagreement.
import csv, os, sys, math, random, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260829)
D = os.path.dirname(os.path.abspath(__file__))

def load(p):
    fp = os.path.join(D, p)
    return list(csv.DictReader(open(fp, encoding="utf-8", errors="replace"))) if os.path.exists(fp) else []
def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception: return None
def pk(n):
    return " ".join((n or "").lower().replace("-", " ").replace(".", " ").replace("'", "").split())

MKTS = ("pts", "reb", "ast")           # what Pinnacle actually prices; 98% of it is pts
gm = {g.get("game_id"): (g.get("date", ""), ts(g.get("tip"))) for g in load("data/games_2026.csv")}
box = {}
for r in load("data/box_2026.csv"):
    dt, tp = gm.get(r.get("game_id"), ("", None))
    if not dt: continue
    box[(dt, pk(r.get("player")))] = dict(pts=f(r.get("pts")) or 0, reb=f(r.get("reb")) or 0,
                                          ast=f(r.get("ast")) or 0)

# ---- Pinnacle: latest fair quote per (date, player, market, side, line) --------------------------
P = {}
for r in load("pinn_snapshots.csv"):
    d, p_, mk, sd = r.get("date"), pk(r.get("player")), r.get("market"), r.get("side")
    ln, fair, cap = f(r.get("pinn_line")), f(r.get("pinn_fair")), ts(r.get("captured_utc"))
    if not (d and p_ and mk in MKTS and sd and ln is not None and fair and cap): continue
    k = (d, p_, mk, sd, ln)
    if k not in P or cap > P[k][0]: P[k] = (cap, fair)
print(f"{len(P)} Pinnacle fair quotes (date, player, market, side, line)")

# ---- 1xbet: latest quote per the same key -------------------------------------------------------
X = {}
for r in load("xbet_board.csv"):
    cap, ln, od = ts(r.get("captured_utc")), f(r.get("line")), f(r.get("odds"))
    mk, sd, p_ = r.get("market"), r.get("side"), pk(r.get("player"))
    if not (cap and ln is not None and od and mk in MKTS and sd and p_): continue
    d = cap.strftime("%Y-%m-%d")
    for dd in (d, (cap - datetime.timedelta(hours=8)).strftime("%Y-%m-%d")):
        k = (dd, p_, mk, sd, ln)
        if k not in X or cap > X[k][0]: X[k] = (cap, od)
print(f"{len(X)} 1xbet quotes on the same key shape")

# ---- matched at the SAME line -------------------------------------------------------------------
M = []
for k, (pcap, fair) in P.items():
    if k not in X: continue
    xcap, xod = X[k]
    d, p_, mk, sd, ln = k
    act = box.get((d.replace("-", ""), p_))
    if not act: continue
    v = act[mk]
    if v == ln: continue
    won = (v > ln) if sd == "Over" else (v < ln)
    M.append(dict(date=d.replace("-", ""), pl=p_, mk=mk, side=sd, line=ln,
                  xod=xod, fair=fair, edge=xod/fair - 1.0, won=won))
print(f"{len(M)} matched at the SAME line with a graded outcome")
if len(M) < 50:
    print("too few to test"); raise SystemExit
print("")
byside = collections.Counter(r["side"] for r in M)
print(f"  sides: {dict(byside)}   markets: {dict(collections.Counter(r['mk'] for r in M))}")
eds = sorted(r["edge"] for r in M)
print(f"  edge distribution: p10 {100*eds[len(eds)//10]:+.1f}%  median {100*eds[len(eds)//2]:+.1f}%"
      f"  p90 {100*eds[9*len(eds)//10]:+.1f}%")
print("")

def roi(rows): return sum((r["xod"]-1) if r["won"] else -1.0 for r in rows)/len(rows) if rows else 0.0
def show(rows, label, minn=25):
    n = len(rows)
    if n < minn:
        print(f"  {label:<42} n={n:<5} too few"); return
    w = sum(1 for r in rows if r["won"])
    avg = sum(r["xod"] for r in rows)/n
    print(f"  {label:<42} n={n:<5} {100*w/n:5.1f}%  ROI {100*roi(rows):+6.1f}%  "
          f"avg {avg:.3f}  be {100/avg:.1f}%")

print("="*104)
print("  THE DIRECT TEST: does 1xbet's price relative to Pinnacle FAIR predict the outcome?")
print("="*104)
show(M, "everything matched")
for lo, hi, lbl in ((-99, -0.10, "1xbet 10%+ BELOW fair (bad price)"),
                    (-0.10, -0.05, "5-10% below fair"),
                    (-0.05, 0.0,  "0-5% below fair"),
                    (0.0, 0.05,   "0-5% ABOVE fair"),
                    (0.05, 99,    "5%+ ABOVE fair (free money?)")):
    show([r for r in M if lo <= r["edge"] < hi], f"  {lbl}")
print("")
print("  by side, since the 7% gap is known to sit mostly on unders:")
for sd in ("Over", "Under"):
    g = [r for r in M if r["side"] == sd]
    show(g, f"  {sd} - all")
    show([r for r in g if r["edge"] > 0], f"  {sd} - price ABOVE fair")
print("")
print("="*104)
print("  OUT OF SAMPLE + PERMUTATION on the best positive-edge cell")
print("="*104)
best = [r for r in M if r["edge"] > 0]
if len(best) >= 40:
    dts = sorted({r["date"] for r in M}); cut = dts[int(len(dts)*0.6)]
    show([r for r in best if r["date"] <  cut], "  positive edge  IN", minn=12)
    show([r for r in best if r["date"] >= cut], "  positive edge  OUT", minn=12)
    real = roi(best)
    outs = [r["won"] for r in M]
    beat = 0; T = 3000
    for _ in range(T):
        sh = outs[:]; random.shuffle(sh)
        lab = {id(r): w for r, w in zip(M, sh)}
        v = sum((r["xod"]-1) if lab[id(r)] else -1.0 for r in best)/len(best)
        if v >= real: beat += 1
    print(f"  permutation p = {beat/T:.4f}  (shuffling outcomes across all {len(M)} matched quotes)")
