# minutes_verify.py - is the minutes model REAL PROFIT? Every gate, causally, no shortcuts.
# ---------------------------------------------------------------------------------------------
# The previous run reported +12.1% for "minutes edge>3 + skip-drift" and +16.8% for the shortened
# tier. Both used drift measured to the LAST capture, which can be AFTER the moment you would bet.
# That is look-ahead - the same flaw that made the original -28% drift claim look tradeable when it
# was not. This file redoes it with everything frozen at a real decision time:
#
#   DECISION POINT   T-6h before that player's tip (where the alert actually fires)
#   PRICE            the odds on the board at that moment - not the open, not the close
#   DRIFT            open -> that moment only
#   FORECAST         minutes and per-minute rate from PRIOR GAMES only
#   SPLIT            first 2/3 of dates search, last 1/3 tested once
#   CLUSTER          one bet per player-game (several lines on one player = one event)
#   NULL             300 sims drawing each result from the LINE's own implied probability
#   COST             1xbet's posted prices, so its ~11% prop margin is already inside the ROI
import csv, os, sys, math, random, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
random.seed(20260811)
def load(p):
    fp = os.path.join(D, p)
    return list(csv.DictReader(open(fp, encoding="utf-8"))) if os.path.exists(fp) else []
def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception: return None
def dparse(d):
    try: return datetime.date(int(d[:4]), int(d[4:6]), int(d[6:8]))
    except Exception: return None

games = load("data/games_2026.csv")
ginfo = {g.get("game_id"): dict(date=g.get("date", ""), tip=ts(g.get("tip")),
                                home=g.get("home"), away=g.get("away")) for g in games}
plog = collections.defaultdict(list)
for r in load("data/box_2026.csv"):
    gi = ginfo.get(r.get("game_id"))
    if not gi or not gi["date"]: continue
    pts, reb, ast = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    plog[(r.get("player") or "").lower()].append(
        dict(date=gi["date"], d=dparse(gi["date"]), tip=gi["tip"], team=r.get("team"),
             min=f(r.get("min")) or 0, pts=pts, reb=reb, ast=ast,
             pra=pts+reb+ast, pr=pts+reb, pa=pts+ast))
for v in plog.values(): v.sort(key=lambda x: x["date"])

# ---- forecast per player-game, from PRIOR games only ---------------------------------------------
FC = {}
for pl, v in plog.items():
    for i, g in enumerate(v):
        prev = v[:i]
        if len(prev) < 6: continue
        l10, l3 = prev[-10:], prev[-3:]
        m10 = sum(x["min"] for x in l10)/len(l10)
        if m10 <= 8: continue
        pred_min = max(0.0, m10 + 0.5*((sum(x["min"] for x in l3)/3 - m10) + (prev[-1]["min"] - m10)))
        tot = sum(x["min"] for x in l10)
        if tot <= 0: continue
        FC[(pl, g["date"])] = dict(pred_min=pred_min, tip=g["tip"], actual=g,
                                   rate={mk: sum(x[mk] for x in l10)/tot for mk in ("pts","pra","pr","pa")})

# ---- board series, so we can freeze the state at any decision time -------------------------------
ser = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None and b.get("side") == "Over" and b.get("market") in ("pts","pra","pr","pa"):
        ser[((b.get("player") or "").lower(), b.get("market"), ln)].append((t, o))
for v in ser.values(): v.sort()

HRS = float(__import__('sys').argv[1]) if len(__import__('sys').argv)>1 else 6.0
bets = []
for (pl, mk, ln), s in ser.items():
    # which player-game does this line belong to? the one whose tip follows the first capture
    cand = [(d, fc) for (p2, d), fc in FC.items() if p2 == pl and fc["tip"]
            and s[0][0] <= fc["tip"] <= s[0][0] + datetime.timedelta(hours=72)]
    if not cand: continue
    date, fc = min(cand, key=lambda x: x[1]["tip"])
    cut = fc["tip"] - datetime.timedelta(hours=HRS)
    pre = [x for x in s if x[0] <= cut]
    if len(pre) < 2: continue                       # need a price AND a drift read at decision time
    price = pre[-1][1]
    drift = pre[-1][1]/pre[0][1] - 1                # OPEN -> DECISION TIME only
    if fc["rate"].get(mk) is None: continue
    bets.append(dict(date=date, pl=pl, mk=mk, line=ln, odds=price, drift=drift,
                     edge=fc["pred_min"]*fc["rate"][mk] - ln,
                     won=fc["actual"][mk] > ln))
bets.sort(key=lambda x: x["date"])
print(f"{len(bets)} props with a real price AND a causal drift read at T-{HRS:.0f}h")

def collapse(rows):
    """One bet per player-game: several lines on one player resolve as a single event."""
    best = {}
    for p in rows:
        k = (p["date"], p["pl"])
        if k not in best or abs(p["edge"]) > abs(best[k]["edge"]): best[k] = p
    return sorted(best.values(), key=lambda x: x["date"])

def stat(xs, minn=25):
    n = len(xs)
    if n < minn: return None
    m = sum(xs)/n; sd = (sum((x-m)**2 for x in xs)/(n-1))**.5
    return (m/(sd/math.sqrt(n)), m*100, n) if sd else None
def show(xs, lbl, minn=25):
    r = stat(xs, minn)
    print(f"  {lbl:<46} n={r[2]:<5} ROI={r[1]:+6.1f}%  t={r[0]:+5.2f}" if r
          else f"  {lbl:<46} n={len(xs)} too few")
    return r
ret = lambda p: (p["odds"]-1) if p["won"] else -1.0

C = collapse(bets)
cut_i = int(len(C)*2/3)
IN, OUT = C[:cut_i], C[cut_i:]
print(f"clustered to {len(C)} player-games  ->  IN {len(IN)} (to {IN[-1]['date']})  "
      f"OUT {len(OUT)} (from {OUT[0]['date']})\n")

print("=== the rule, causally, on IN-SAMPLE ===")
show([ret(p) for p in IN], "every prop (baseline)")
show([ret(p) for p in IN if p["edge"] > 3.0], "minutes edge>3")
show([ret(p) for p in IN if p["edge"] > 3.0 and p["drift"] < 0.01], "minutes edge>3 + skip-drift")
show([ret(p) for p in IN if p["edge"] > 3.0 and p["drift"] <= -0.005], "minutes edge>3 + already SHORTENED")

print("\n=== NULL: 300 sims, each result drawn from the LINE's own implied probability ===")
EDGES = (1.0, 2.0, 3.0, 4.0); DR = (("any", 99.0), ("skip-drift", 0.01), ("shortened", -0.005))
def search(rows, outcomes=None):
    best = None
    for e in EDGES:
        for dn, dv in DR:
            sel = [i for i, p in enumerate(rows) if p["edge"] > e and p["drift"] < dv]
            xs = [((rows[i]["odds"]-1) if (outcomes[i] if outcomes else rows[i]["won"]) else -1.0)
                  for i in sel]
            r = stat(xs)
            if r and (best is None or r[0] > best[0][0]): best = (r, (e, dn))
    return best
implied = lambda p: min(0.97, max(0.03, (1/p["odds"])/1.055))
nulls = []
for _ in range(300):
    sim = [random.random() < implied(p) for p in IN]
    b = search(IN, sim)
    if b: nulls.append(b[0][0])
nulls.sort()
real = search(IN)
beat = sum(1 for x in nulls if x >= real[0][0])/len(nulls)
print(f"  null best-t: median {nulls[len(nulls)//2]:+.2f}  95th {nulls[int(len(nulls)*.95)]:+.2f}  "
      f"max {nulls[-1]:+.2f}")
print(f"  our best in-sample: {real[1]} -> t={real[0][0]:+.2f}, ROI={real[0][1]:+.1f}%, n={real[0][2]}")
print(f"  null beats it {beat*100:.1f}% of the time  ({'PASSES' if beat < 0.05 else 'FAILS'})")

print("\n=== OUT-OF-SAMPLE, tested once ===")
e, dn = real[1]; dv = dict(DR)[dn]
o = show([ret(p) for p in OUT if p["edge"] > e and p["drift"] < dv],
         f"edge>{e} + {dn}", minn=12)
if o:
    print(f"  break-even needs ROI > 0 at 1xbet's own prices (vig already inside)")
    print(f"  -> {'REAL PROFIT out of sample' if o[1] > 0 else 'NO PROFIT out of sample'}")
