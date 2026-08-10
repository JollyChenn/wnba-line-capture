# backtest_guard.py - does the LIVE strategy match what we actually backtested?
# ---------------------------------------------------------------------------------------------
# The backtest filters on odds_clv, which is OPEN vs CLOSE - a number that only exists after tip.
# The live gate filters on OPEN vs NOW at ping time, and then guard() adds rules the backtest never
# saw at all (span, freshness, board liveness). So the live strategy is a NARROWER, DIFFERENT
# population than the one we measured +6.1% on, and its expectancy is not automatically the same.
#
# This replays every graded bet as the live system would have seen it at a chosen hour before tip:
#   - price series truncated to what existed then
#   - drift measured open->then, not open->close
#   - guard rules applied on that partial information
#   - paid at the price available THEN
# Then compares that to the backtest's number on the same bets.
import csv, os, sys, math, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
def load(p):
    fp = os.path.join(D, p)
    return list(csv.DictReader(open(fp, encoding="utf-8"))) if os.path.exists(fp) else []
def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception: return None

LIVE = ("flip", "flip_paper", "overshoot", "cascade")
DRIFT, MIN_SPAN_H, MIN_CAPS, BOARD_ALIVE = 0.01, 3.0, 4, 0.10

# ---- tip time per (game date, team), then per player via their box appearance ------------------
games = load("data/games_2026.csv")
tip_by = {}
for g in games:
    t = ts(g.get("tip"))
    if not t: continue
    for k in ("home", "away"):
        if g.get(k): tip_by[(g.get("date", ""), g[k])] = t
gdate = {g.get("game_id"): g.get("date", "") for g in games}
tip_pl = {}                                   # (date, player) -> tip
for r in load("data/box_2026.csv"):
    d, pl, tm = gdate.get(r.get("game_id"), ""), (r.get("player") or "").lower(), r.get("team") or ""
    if d and pl and (d, tm) in tip_by: tip_pl[(d, pl)] = tip_by[(d, tm)]

# ---- price series per bet, per slate -----------------------------------------------------------
series = collections.defaultdict(list)
for r in load("bets_log.csv"):
    t, o, ln = ts(r.get("captured_utc")), f(r.get("odds")), f(r.get("line"))
    if t and o: series[(r.get("date"), r.get("player"), r.get("market"), r.get("side"))].append((t, ln, o))

graded = [r for r in load("graded_bets.csv")
          if (r.get("result") or "").upper() in ("WIN", "LOSS") and r.get("src") in LIVE]

def summarise(rets, label):
    n = len(rets)
    if n < 10: print(f"  {label:<44} n={n:<4} (too few)"); return None
    m = sum(rets)/n; sd = (sum((x-m)**2 for x in rets)/(n-1))**.5
    t = m/(sd/math.sqrt(n))
    print(f"  {label:<44} n={n:<4} ROI={m*100:+6.1f}%  t={t:+5.2f}  {sum(rets):+6.1f}u")
    return n, m*100, t

print("\n=== A. the BACKTEST number (open vs CLOSE - uses post-tip information) ===")
bt_keep, bt_all = [], []
for r in graded:
    o, clv = f(r.get("odds")), f(r.get("odds_clv"))
    if o is None: continue
    price = o/(1+clv) if clv is not None else o                 # paid at close, the honest version
    ret = (price-1) if r["result"].upper() == "WIN" else -1.0
    bt_all.append(ret)
    if (clv or 0) >= -DRIFT: bt_keep.append(ret)
summarise(bt_all, "no filter at all")
summarise(bt_keep, "backtest filter (odds_clv >= -1%)")

print("\n=== B. the LIVE system replayed causally at each decision point ===")
print("     (drift measured open->then, guard rules applied, paid at the price available then)\n")
for HRS in (10.0, 8.0, 6.0, 5.0, 4.0, 3.0, 2.0, 1.0):
    # board liveness at this hour, per slate: share of that slate's bets that had moved by then
    board = collections.defaultdict(lambda: [0, 0])
    partial = {}
    for r in graded:
        key = (r.get("date", "").replace("-", ""), (r.get("player") or "").lower())
        d8 = r.get("date", "").replace("-", "")
        tip = tip_pl.get((d8, (r.get("player") or "").lower()))
        if not tip: continue
        cut = tip - datetime.timedelta(hours=HRS)
        sd = f"{d8[:4]}-{d8[4:6]}-{d8[6:8]}"
        ser = sorted(x for x in series.get((sd, r.get("player"), r.get("market"), r.get("side")), [])
                     if x[0] <= cut)
        if len(ser) < 2: continue
        cur_line = ser[-1][1]
        cl = [x for x in ser if x[1] == cur_line]
        if len(cl) < 2: continue
        move = cl[-1][2]/cl[0][2] - 1
        span = (cl[-1][0] - cl[0][0]).total_seconds()/3600
        partial[id(r)] = (move, span, len(cl), cl[-1][2], r)
        board[sd][0] += 1
        if abs(move) > 0.003: board[sd][1] += 1

    # DECOMPOSE. Bundling the rules hides which one is carrying the result and which is merely
    # shrinking the sample. Each bucket adds exactly one rule to the one above it.
    B = {k: [] for k in ("menu only, no rules", "+ skip-drift", "+ window", "+ dead-board",
                         "ONLY shortened (<=-0.5%)")}
    for (move, span, ncap, price_then, r) in partial.values():
        sd = r.get("date", "")[:4] + "-" + r.get("date", "")[4:6] + "-" + r.get("date", "")[6:8]
        tot, mv = board[sd]
        ret = (price_then-1) if r["result"].upper() == "WIN" else -1.0
        B["menu only, no rules"].append(ret)
        if move >= DRIFT: continue
        B["+ skip-drift"].append(ret)
        if move <= -0.005: B["ONLY shortened (<=-0.5%)"].append(ret)
        if not (span >= MIN_SPAN_H or ncap >= MIN_CAPS): continue
        B["+ window"].append(ret)
        if tot >= 8 and mv/tot < BOARD_ALIVE: continue
        B["+ dead-board"].append(ret)
    # PROPOSED CONFIG: bet late, and relax the two rules that were costing ROI. dead-board drops
    # 10% -> 3% (catch only a genuinely no-data board, not a quiet one); window 3h -> 2h.
    prop = []
    for (move, span, ncap, price_then, r) in partial.values():
        sd = r.get("date", "")[:4] + "-" + r.get("date", "")[4:6] + "-" + r.get("date", "")[6:8]
        tot, mv = board[sd]
        ret = (price_then-1) if r["result"].upper() == "WIN" else -1.0
        if move >= DRIFT: continue
        if ncap < 2: continue                      # >=2 observations, no span requirement
        if tot >= 8 and mv/tot < 0.03: continue    # only a genuinely no-data board
        prop.append(ret)
    print(f"  --- T-{HRS:.0f}h ---")
    for k in ("menu only, no rules", "+ skip-drift", "+ window", "+ dead-board",
              "ONLY shortened (<=-0.5%)"):
        summarise(B[k], k)
    summarise(prop, "PROPOSED (skip-drift, caps>=2, board 3%)")

print("\nNOTE: B pays at the price actually on the board at that hour, so it is directly comparable")
print("to what you can collect. A pays at the close and needs post-tip information to select bets.")
