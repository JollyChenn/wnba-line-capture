# audit_final.py - LAST CHECK BEFORE REAL MONEY. Five failure modes not yet ruled out:
#  A. post-tip leak      : any capture at/after tip would encode the result -> fatal look-ahead
#  B. tip coverage       : bets with no tip time are excluded; are they systematically different?
#  C. clustering         : bets on the same game aren't independent -> t is inflated
#  D. time split         : does the filter work in BOTH halves of the season (real out-of-sample)?
#  E. threshold fitting  : is 1% special, or does any threshold work (i.e. not cherry-picked)?
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

gt = {}
for r in csv.DictReader(open(os.path.join(D, "data/games_2026.csv"), encoding="utf-8")):
    t = ts(r.get("tip"))
    if t: gt[r["game_id"]] = (r.get("date", ""), t)
ptip, pgame = {}, {}
for r in csv.DictReader(open(os.path.join(D, "data/box_2026.csv"), encoding="utf-8")):
    g = gt.get(r.get("game_id"))
    if g:
        ptip[(r.get("player", "").lower(), g[0])] = g[1]
        pgame[(r.get("player", "").lower(), g[0])] = r.get("game_id")
caps = defaultdict(list)
for b in csv.DictReader(open(os.path.join(D, "bets_log.csv"), encoding="utf-8")):
    t = ts(b.get("captured_utc")); o = f(b.get("odds")); ln = f(b.get("line"))
    if t and o and ln is not None:
        caps[(b.get("player", "").lower(), b.get("market"), b.get("side"))].append((t, ln, o))
G = [r for r in csv.DictReader(open(os.path.join(D, "graded_bets.csv"), encoding="utf-8")) if RES(r) in ("WIN", "LOSS")]
live = [r for r in G if r.get("src") in LIVE]
def ser(r):
    tip = ptip.get((r.get("player", "").lower(), r.get("date", "")))
    s = sorted(caps.get((r.get("player", "").lower(), r.get("market"), r.get("side")), []))
    if not tip: return None, None
    return [x for x in s if x[0] < tip and (tip - x[0]).total_seconds() <= 60*3600], tip
def drift(r, cut=8.0, thr=0.01):
    s, tip = ser(r)
    if not s or len(s) < 2: return None
    vis = [x for x in s if (tip - x[0]).total_seconds()/3600 >= cut]
    if len(vis) < 2: return None
    ol = vis[0][1]; at = [x for x in vis if x[1] == ol]
    return (at[-1][2]/at[0][2] - 1) if len(at) > 1 else None
def stat(rows):
    v = [f(r["pnl"]) or 0 for r in rows]; n = len(v)
    if n < 5: return None
    m = statistics.mean(v); s = statistics.pstdev(v)
    return dict(n=n, w=sum(1 for r in rows if RES(r) == "WIN"), roi=100*m, pl=m*n,
                t=(m/(s/math.sqrt(n)) if s else 0), sd=s)
def show(lbl, rows):
    st = stat(rows)
    print(f"  {lbl:46}" + (f"{st['w']}-{st['n']-st['w']} ({100*st['w']/st['n']:>3.0f}%) ROI={st['roi']:+5.1f}% "
          f"P&L={st['pl']:+6.1f}u t={st['t']:+.2f}" if st else f"n={len(rows)} --"))

print("="*98)
print("A. POST-TIP LEAK — any capture at/after tip encodes the result")
late = 0; total = 0; worst = None
for r in G:
    s, tip = ser(r)
    if not tip: continue
    allc = sorted(caps.get((r.get("player", "").lower(), r.get("market"), r.get("side")), []))
    for x in allc:
        if (tip - x[0]).total_seconds() <= 60*3600:
            total += 1
            if x[0] >= tip:
                late += 1
                if worst is None or x[0] > worst: worst = x[0]
print(f"  captures used: {total} | at/after tip: {late}  ({'CLEAN' if late == 0 else 'LEAK!'})")
mins = []
for r in G:
    s, tip = ser(r)
    if s: mins.append((tip - s[-1][0]).total_seconds()/60)
if mins:
    mins.sort()
    print(f"  closest capture to tip: {mins[0]:.0f} min before | median last capture {statistics.median(mins):.0f} min before tip")

print("\n" + "="*98)
print("B. TIP COVERAGE — are the excluded bets different?")
have = [r for r in live if ptip.get((r.get("player", "").lower(), r.get("date", "")))]
miss = [r for r in live if not ptip.get((r.get("player", "").lower(), r.get("date", "")))]
show("live bets WITH a tip time (used)", have)
show("live bets WITHOUT a tip time (excluded)", miss)

print("\n" + "="*98)
print("C. CLUSTERING — bets on the same game are not independent")
kept = [r for r in live if (drift(r) is None or drift(r) < 0.01)]
games = defaultdict(list)
for r in kept:
    g = pgame.get((r.get("player", "").lower(), r.get("date", "")), r.get("date", "") + r.get("player", ""))
    games[g].append(f(r["pnl"]) or 0)
per_game = [sum(v) for v in games.values()]          # treat each GAME as one observation
n_g = len(per_game); m_g = statistics.mean(per_game); s_g = statistics.pstdev(per_game)
st = stat(kept)
print(f"  bet-level : n={st['n']} ROI={st['roi']:+.1f}% t={st['t']:+.2f}")
print(f"  game-level: {n_g} games, mean {m_g:+.3f}u/game, t={(m_g/(s_g/math.sqrt(n_g))):+.2f}  <- the honest t")
print(f"  avg bets per game: {st['n']/n_g:.1f}")

print("\n" + "="*98)
print("D. TIME SPLIT — does it hold in BOTH halves? (real out-of-sample)")
dates = sorted({r["date"] for r in live})
mid = dates[len(dates)//2]
for lbl, sub in (("first half " + dates[0] + "-" + mid, [r for r in live if r["date"] <= mid]),
                 ("second half " + mid + "-" + dates[-1], [r for r in live if r["date"] > mid])):
    base = sub
    filt = [r for r in sub if (drift(r) is None or drift(r) < 0.01)]
    b, fl = stat(base), stat(filt)
    if b and fl:
        print(f"  {lbl:34} baseline ROI={b['roi']:+5.1f}%  ->  skip-drift ROI={fl['roi']:+5.1f}% (n={fl['n']}, t={fl['t']:+.2f})")

print("\n" + "="*98)
print("E. THRESHOLD SENSITIVITY — is 1% cherry-picked?")
for thr in (0.005, 0.01, 0.015, 0.02, 0.03):
    kept = [r for r in live if (drift(r, 8.0) is None or drift(r, 8.0) < thr)]
    show(f"skip-drift threshold {thr*100:.1f}%", kept)
