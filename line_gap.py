# line_gap.py - the case I deliberately excluded, which may be the whole edge.
# ---------------------------------------------------------------------------------------------
# sharp_edge.py compared 1xbet's PRICE to Pinnacle's fair price at the SAME LINE, and found
# nothing: the gap is a near-universal -6.9% and it does not predict outcomes. But that test
# threw away every case where the two books disagree about the NUMBER, and that is the case that
# matters.
#
# Pinnacle fair says what a bet at PINNACLE'S line is worth. If 1xbet is offering the over at a
# LOWER number than Pinnacle has, the bet is easier to win regardless of the price - that is line
# value, not price value, and it is invisible to a same-line comparison.
#
# This is also exactly what the star detects indirectly. The star fires when 1xbet has NOT moved
# a player's number since her last game; if the true number has risen, 1xbet's stale line is now
# below fair. So if the thesis is right, the line gap should work AND should overlap with the star.
import csv, os, sys, math, random, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260830)
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

MKTS = ("pts", "reb", "ast")
gm = {g.get("game_id"): g.get("date", "") for g in load("data/games_2026.csv")}
box = {}
for r in load("data/box_2026.csv"):
    dt = gm.get(r.get("game_id"))
    if not dt: continue
    box[(dt, pk(r.get("player")))] = dict(pts=f(r.get("pts")) or 0, reb=f(r.get("reb")) or 0,
                                          ast=f(r.get("ast")) or 0)

# Pinnacle's LINE per (date, player, market) - one number, whichever side it came from
PL = {}
for r in load("pinn_snapshots.csv"):
    d, p_, mk = r.get("date"), pk(r.get("player")), r.get("market")
    ln, cap = f(r.get("pinn_line")), ts(r.get("captured_utc"))
    if not (d and p_ and mk in MKTS and ln is not None and cap): continue
    k = (d, p_, mk)
    if k not in PL or cap > PL[k][0]: PL[k] = (cap, ln)

# 1xbet's LINE and both prices per (date, player, market)
XL = {}
for r in load("xbet_board.csv"):
    cap, ln, od = ts(r.get("captured_utc")), f(r.get("line")), f(r.get("odds"))
    mk, sd, p_ = r.get("market"), r.get("side"), pk(r.get("player"))
    if not (cap and ln is not None and od and mk in MKTS and sd and p_): continue
    for dd in (cap.strftime("%Y-%m-%d"), (cap - datetime.timedelta(hours=8)).strftime("%Y-%m-%d")):
        k = (dd, p_, mk)
        slot = XL.setdefault(k, {})
        cur = slot.get(sd)
        if cur is None or cap > cur[0]: slot[sd] = (cap, ln, od)

M = []
for k, (pcap, pln) in PL.items():
    x = XL.get(k)
    if not x or "Over" not in x: continue
    d, p_, mk = k
    act = box.get((d.replace("-", ""), p_))
    if not act: continue
    v = act[mk]
    xcap, xln, xod = x["Over"]
    if v == xln: continue
    M.append(dict(date=d.replace("-", ""), pl=p_, mk=mk, xline=xln, pline=pln,
                  gap=pln - xln,                       # + means 1xbet's number is LOWER than sharp
                  xod=xod, won=v > xln, actual=v))
print(f"{len(M)} player-games where BOTH books have a line and the game is graded")
if len(M) < 60:
    print("too few"); raise SystemExit
g = sorted(r["gap"] for r in M)
print(f"  line gap (Pinnacle minus 1xbet): p10 {g[len(g)//10]:+.1f}  median {g[len(g)//2]:+.1f}"
      f"  p90 {g[9*len(g)//10]:+.1f}")
same = sum(1 for r in M if abs(r["gap"]) < 0.01)
print(f"  books agree exactly on {same} of {len(M)} ({100*same/len(M):.0f}%)")
print("")

def roi(rows): return sum((r["xod"]-1) if r["won"] else -1.0 for r in rows)/len(rows) if rows else 0.0
def show(rows, label, minn=20):
    n = len(rows)
    if n < minn:
        print(f"  {label:<44} n={n:<5} too few"); return
    w = sum(1 for r in rows if r["won"])
    avg = sum(r["xod"] for r in rows)/n
    print(f"  {label:<44} n={n:<5} {100*w/n:5.1f}%  ROI {100*roi(rows):+6.1f}%  be {100/avg:.1f}%")

print("="*104)
print("  BETTING THE OVER WHEN 1XBET'S NUMBER IS BELOW PINNACLE'S")
print("="*104)
show(M, "every matched player-game (over)")
for lo, hi, lbl in ((-99, -1.0, "1xbet line ABOVE sharp by 1+  (rich)"),
                    (-1.0, -0.01, "1xbet slightly above sharp"),
                    (-0.01, 0.01, "books AGREE"),
                    (0.01, 1.0,  "1xbet below sharp by <1"),
                    (1.0, 2.0,   "1xbet BELOW sharp by 1-2   (cheap)"),
                    (2.0, 99,    "1xbet BELOW sharp by 2+    (very cheap)")):
    show([r for r in M if lo <= r["gap"] < hi], f"  {lbl}")
print("")
print("="*104)
print("  OUT OF SAMPLE + PERMUTATION on the cheap-line cell")
print("="*104)
cheap = [r for r in M if r["gap"] >= 1.0]
if len(cheap) >= 30:
    dts = sorted({r["date"] for r in M}); cut = dts[int(len(dts)*0.6)]
    show([r for r in cheap if r["date"] <  cut], "  1xbet cheap by 1+   IN", minn=10)
    show([r for r in cheap if r["date"] >= cut], "  1xbet cheap by 1+   OUT", minn=10)
    real = roi(cheap)
    outs = [r["won"] for r in M]
    beat = 0; T = 3000
    for _ in range(T):
        sh = outs[:]; random.shuffle(sh)
        lab = {id(r): w for r, w in zip(M, sh)}
        v = sum((r["xod"]-1) if lab[id(r)] else -1.0 for r in cheap)/len(cheap)
        if v >= real: beat += 1
    print(f"  permutation p = {beat/T:.4f}")
    print("")
    print("  monthly:")
    for mo in sorted({r["date"][:6] for r in cheap}):
        show([r for r in cheap if r["date"][:6] == mo], f"    {mo}", minn=8)
else:
    print(f"  only {len(cheap)} cheap-line rows")
