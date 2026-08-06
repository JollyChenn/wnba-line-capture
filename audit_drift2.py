# audit_drift2.py - CORRECTED live-replay of the drift filter.
# Fix vs v1: build each bet's price series the way grade_bets (and drift_gate) do — merge captures
# across slate dates for the same (player,market,side), anchor on the OPENING line, and cut off by
# REAL TIP TIME rather than "hours before the last capture".
# Question: at T-Xh before tip, would the filter have improved the live menu?
import csv, os, sys, math, statistics, datetime
from collections import defaultdict
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
def f(x):
    try: return float(x)
    except Exception: return None
def RES(r): return (r.get("result") or "").upper()
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception: return None
LIVE = ("flip", "flip_paper", "overshoot", "cascade")

# tip time per (player, game-date): from games + box
gt = {}
for r in csv.DictReader(open(os.path.join(D, "data/games_2026.csv"), encoding="utf-8")):
    t = ts(r.get("tip"))
    if t: gt[r["game_id"]] = (r.get("date", ""), t)
ptip = {}
for r in csv.DictReader(open(os.path.join(D, "data/box_2026.csv"), encoding="utf-8")):
    g = gt.get(r.get("game_id"))
    if g: ptip[(r.get("player", "").lower(), g[0])] = g[1]

# all captures per (player, market, side) — NO date key, exactly like drift_gate
caps = defaultdict(list)
for b in csv.DictReader(open(os.path.join(D, "bets_log.csv"), encoding="utf-8")):
    t = ts(b.get("captured_utc")); o = f(b.get("odds")); ln = f(b.get("line"))
    if t and o and ln is not None:
        caps[(b.get("player", "").lower(), b.get("market"), b.get("side"))].append((t, ln, o))

G = [r for r in csv.DictReader(open(os.path.join(D, "graded_bets.csv"), encoding="utf-8")) if RES(r) in ("WIN", "LOSS")]
live = [r for r in G if r.get("src") in LIVE]

def drift_at(r, cutoff_h):
    """Drift verdict for bet r using only captures >= cutoff_h before ITS OWN TIP.
       Opening-line anchored, same as grade_bets. None = no read."""
    tip = ptip.get((r.get("player", "").lower(), r.get("date", "")))
    s = sorted(caps.get((r.get("player", "").lower(), r.get("market"), r.get("side")), []))
    if not tip or len(s) < 2: return None
    # captures belonging to THIS game: after the previous day, before tip
    s = [x for x in s if x[0] < tip and (tip - x[0]).total_seconds() <= 60*3600]
    if len(s) < 2: return None
    vis = [x for x in s if (tip - x[0]).total_seconds()/3600 >= cutoff_h]
    if len(vis) < 2: return None
    ol = vis[0][1]                                   # opening line
    at = [x for x in vis if x[1] == ol]
    if len(at) < 2: return None
    return at[-1][2] / at[0][2] - 1

def show(lbl, rows):
    v = [f(r["pnl"]) or 0 for r in rows]; n = len(v)
    if n < 5: print(f"  {lbl:48} n={n} --"); return
    m = statistics.mean(v); s = statistics.pstdev(v); w = sum(1 for r in rows if RES(r) == "WIN")
    print(f"  {lbl:48}{w}-{n-w} ({100*w/n:>3.0f}%) ROI={100*m:+5.1f}% P&L={m*n:+6.1f}u t={(m/(s/math.sqrt(n)) if s else 0):+.2f}")

print("CORRECTED LIVE REPLAY — drift measured only from captures available X hours before TIP")
show("live menu, NO filter (baseline)", live)
for h in (8, 6, 4, 2, 1, 0):
    kept = [r for r in live if (drift_at(r, h) is None or drift_at(r, h) < 0.01)]
    show(f"skip-drift using only info at T-{h}h", kept)
show("skip-drift via stored odds_clv (full close)",
     [r for r in live if (f(r.get("odds_clv")) or 0) >= -0.01])
cov = sum(1 for r in live if drift_at(r, 4) is not None)
print(f"\n  coverage: {cov}/{len(live)} live-menu bets have a usable T-4h read "
      f"({100*cov/len(live):.0f}%) — the rest are 'no read' and get bet by default")
