# audit_drift.py - PRE-GO-LIVE AUDIT of the drift filter. Answers the only question that matters:
# would the filter have worked using ONLY information available at bet time?
# The backtest used odds_clv = opening/CLOSING-1, which needs the close. Live you decide at T-Xh with
# a partial price series. This replays the filter with that partial information and compares.
# Also: confound checks (odds level, market, signal mix), duplicate check, and a shuffle control.
import csv, os, sys, math, statistics, datetime, random
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

G = [r for r in csv.DictReader(open(os.path.join(D, "graded_bets.csv"), encoding="utf-8")) if RES(r) in ("WIN", "LOSS")]
# rebuild each bet's price series from the raw capture log
ser = defaultdict(list)
for r in csv.DictReader(open(os.path.join(D, "bets_log.csv"), encoding="utf-8")):
    t = ts(r.get("captured_utc")); o = f(r.get("odds"))
    if t and o:
        ser[(r.get("date", "").replace("-", ""), r.get("player", "").lower(), r.get("market"), r.get("side"))].append((t, f(r.get("line")), o))
def key(r): return (r.get("date", "").replace("-", ""), r.get("player", "").lower(), r.get("market"), r.get("side"))

def stat(rows):
    v = [f(r["pnl"]) or 0 for r in rows]; n = len(v)
    if n < 5: return None
    m = statistics.mean(v); s = statistics.pstdev(v)
    return dict(n=n, w=sum(1 for r in rows if RES(r) == "WIN"), roi=100*m, pl=m*n,
                t=(m/(s/math.sqrt(n)) if s else 0))
def show(lbl, rows):
    st = stat(rows)
    if not st: print(f"  {lbl:44} n={len(rows)} --"); return
    print(f"  {lbl:44}{st['w']}-{st['n']-st['w']} ({100*st['w']/st['n']:>3.0f}%) "
          f"ROI={st['roi']:+5.1f}% P&L={st['pl']:+6.1f}u t={st['t']:+.2f}")

print("=" * 96)
print("TEST 1 — THE DECISIVE ONE: filter using only info available BEFORE the close")
print("  (drift measured from the first capture to the last capture at least X hours before the final one)")
live = [r for r in G if r.get("src") in LIVE]
def live_drift(r, cutoff_h):
    """drift verdict using only captures up to cutoff_h before the bet's LAST capture (proxy for tip)."""
    s = sorted(ser.get(key(r), []))
    if len(s) < 2: return None                      # no read
    last_t = s[-1][0]
    sub = [x for x in s if (last_t - x[0]).total_seconds()/3600 >= cutoff_h]
    if len(sub) < 2: return None
    cur_line = sub[-1][1]
    cl = [x for x in sub if x[1] == cur_line]
    if len(cl) < 2: return None
    return cl[-1][2] / cl[0][2] - 1
show("live menu, NO filter (baseline)", live)
for h in (0, 2, 4, 6, 8):
    kept = []
    for r in live:
        d = live_drift(r, h)
        if d is None or d < 0.01: kept.append(r)     # no read = bet it (that's what the gate does)
    show(f"live menu, skip-drift decided at T-{h}h", kept)
show("live menu, skip-drift using the CLOSE (backtest)",
     [r for r in live if (f(r.get("odds_clv")) or 0) >= -0.01])

print("\n" + "=" * 96)
print("TEST 2 — CONFOUND CHECKS: is 'drift' just a proxy for something else?")
dr = [r for r in G if (f(r.get("odds_clv")) or 0) < -0.01]
nd = [r for r in G if (f(r.get("odds_clv")) or 0) >= -0.01]
def avg(rows, col):
    v = [f(r.get(col)) for r in rows if f(r.get(col)) is not None]
    return statistics.mean(v) if v else 0
print(f"  avg PRICE      drifted {avg(dr,'odds'):.3f}  vs  non-drifted {avg(nd,'odds'):.3f}   "
      f"(if drifted were systematically longer-priced, P&L would be flattered, not hurt)")
print(f"  avg LINE       drifted {avg(dr,'line'):.1f}    vs  non-drifted {avg(nd,'line'):.1f}")
from collections import Counter
cd = Counter(r.get("src") for r in dr); cn = Counter(r.get("src") for r in nd)
print("  signal mix     drifted:", {k: v for k, v in cd.most_common(4)})
print("                 non-dr :", {k: v for k, v in cn.most_common(4)})
print("  market mix     drifted:", {k: v for k, v in Counter(r.get('market') for r in dr).most_common(3)})
print("  side mix       drifted:", dict(Counter(r.get('side') for r in dr)), " non-dr:", dict(Counter(r.get('side') for r in nd)))
# within-signal check: does drift hurt INSIDE each signal? (kills 'drift just picks bad signals')
print("\n  within each signal (kills the 'drift = bad-signal proxy' explanation):")
for s in ("newunder", "cascade", "overshoot", "flip_paper", "flip"):
    a = [r for r in G if r.get("src") == s and (f(r.get("odds_clv")) or 0) < -0.01]
    b = [r for r in G if r.get("src") == s and (f(r.get("odds_clv")) or 0) >= -0.01]
    sa, sb = stat(a), stat(b)
    if sa and sb:
        print(f"    {s:11} drifted ROI={sa['roi']:+6.1f}% (n={sa['n']:>3})  |  clean ROI={sb['roi']:+6.1f}% (n={sb['n']:>3})")

print("\n" + "=" * 96)
print("TEST 3 — DUPLICATES: is any bet counted twice?")
seen = Counter((r.get("date"), r.get("player"), r.get("market"), r.get("side"), r.get("line")) for r in G)
dups = {k: v for k, v in seen.items() if v > 1}
print(f"  graded rows: {len(G)} | unique bet keys: {len(seen)} | duplicated keys: {len(dups)}")
if dups: print("   examples:", list(dups.items())[:3])

print("\n" + "=" * 96)
print("TEST 4 — SHUFFLE CONTROL: assign the drift label at random; the edge must vanish")
random.seed(7)
labels = [(f(r.get("odds_clv")) or 0) < -0.01 for r in G]
real_gap = (stat([r for r, l in zip(G, labels) if not l])["roi"] - stat([r for r, l in zip(G, labels) if l])["roi"])
gaps = []
for _ in range(400):
    sh = labels[:]; random.shuffle(sh)
    a = stat([r for r, l in zip(G, sh) if not l]); b = stat([r for r, l in zip(G, sh) if l])
    if a and b: gaps.append(a["roi"] - b["roi"])
beat = sum(1 for g in gaps if g >= real_gap)
print(f"  real gap (clean − drifted) = {real_gap:+.1f} ROI points")
print(f"  shuffled gaps: mean {statistics.mean(gaps):+.1f}, 95th pct {sorted(gaps)[int(.95*len(gaps))]:+.1f}")
print(f"  shuffles that matched or beat the real gap: {beat}/400  ->  p = {beat/400:.3f}")
