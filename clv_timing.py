# clv_timing.py - if we bet at the LAST MINUTE, how do we still measure anything?
# ---------------------------------------------------------------------------------------------
# The question is sharper than it looks, because the two things we want are in direct conflict:
#
#   SKIP-DRIFT wants us to bet LATE.  Drift is odds lengthening between now and tip. If we bet
#              five minutes before tip there is almost no time left for the price to move against
#              us, and - more importantly - the whole drift history is already IN THE PAST, so we
#              can read all of it before deciding. Betting late makes the filter fully observable.
#
#   CLV        wants us to bet EARLY. Closing line value = (our price) vs (the closing price).
#              If we bet at the close, our price IS the closing price, so CLV is zero BY
#              CONSTRUCTION - not because we did badly, but because we removed the gap we were
#              measuring. The instrument breaks.
#
# So this file measures four things:
#   1 HOW MUCH DRIFT IS VISIBLE at each horizon before tip (the case FOR betting late)
#   2 HOW MANY PROPS EXIST at each horizon (the cost OF betting late - lines get posted late)
#   3 WHAT THE FILTER ACTUALLY EARNS if applied causally at each horizon
#   4 WHETHER PINNACLE CAN REPLACE CLV as the measuring instrument for a last-minute bettor
#     (compare our 1xbet price to Pinnacle's no-vig fair price AT THE MOMENT WE BET - this is an
#      edge reading available instantly, with no waiting for a close at all)
import csv, os, sys, math, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
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

# ---- games, tips, and box scores -----------------------------------------------------------------
games = load("data/games_2026.csv")
ginfo = {g.get("game_id"): dict(date=g.get("date", ""), tip=ts(g.get("tip"))) for g in games}
box = {}                       # (date, player) -> actual production
for r in load("data/box_2026.csv"):
    gi = ginfo.get(r.get("game_id"))
    if not gi or not gi["date"]: continue
    pts, reb, ast = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    box[(gi["date"], (r.get("player") or "").lower())] = dict(
        pts=pts, reb=reb, ast=ast, pra=pts+reb+ast, pr=pts+reb, pa=pts+ast, tip=gi["tip"])

# ---- every prop price series on the board --------------------------------------------------------
# CAREFUL: the same player can have the SAME line on many different nights. Keying only on
# (player, market, line) glues weeks of separate games into one fake series - which makes the
# "open" a price from a fortnight ago and the drift meaningless. So after grouping we SPLIT the
# series wherever there is a gap of more than 12 hours between consecutive captures. Each of those
# blocks is one night's line for one game.
raw = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None and b.get("side") == "Over" and b.get("market") in ("pts","pra","pr","pa"):
        raw[((b.get("player") or "").lower(), b.get("market"), ln)].append((t, o))

ser = {}                                             # (player, market, line, block#) -> one night
for (pl, mk, ln), v in raw.items():
    v.sort()
    block, k = [v[0]], 0
    for prev, cur in zip(v, v[1:]):
        if (cur[0] - prev[0]).total_seconds() > 12*3600:      # new night
            ser[(pl, mk, ln, k)] = block; k += 1; block = []
        block.append(cur)
    ser[(pl, mk, ln, k)] = block

# attach each night's series to the game it belongs to (the first tip that follows its first capture)
props = []
for (pl, mk, ln, _k), s in ser.items():
    if len(s) < 2: continue
    cand = [(d, rec) for (d, p2), rec in box.items()
            if p2 == pl and rec["tip"] and s[0][0] <= rec["tip"] <= s[0][0] + datetime.timedelta(hours=36)]
    if not cand: continue
    date, rec = min(cand, key=lambda x: x[1]["tip"])
    props.append(dict(pl=pl, mk=mk, line=ln, tip=rec["tip"], s=s, date=date,
                      full_drift=s[-1][1]/s[0][1] - 1,
                      last_gap_h=(rec["tip"] - s[-1][0]).total_seconds()/3600,
                      won=rec[mk] > ln))
props = [p for p in props if -1.0 <= p["last_gap_h"] <= 36.0]   # drop anything still mis-attached
print(f"{len(props)} prop price series (one per player-line-night) matched to a finished game\n")

print("="*84)
print("  0. HOW LATE DOES OUR DATA ACTUALLY GO? (you cannot bet on a price you never captured)")
print("="*84)
gaps = sorted(p["last_gap_h"] for p in props)
def pct(v, q): return v[min(len(v)-1, int(len(v)*q))]
print(f"    hours between our LAST capture and tip-off:")
print(f"      median {pct(gaps,.50):.1f}h   75th {pct(gaps,.75):.1f}h   "
      f"90th {pct(gaps,.90):.1f}h   worst {gaps[-1]:.1f}h")
for w in (0.5, 1.0, 2.0):
    n = sum(1 for g in gaps if g <= w)
    print(f"      captured within {w:.1f}h of tip: {n}/{len(gaps)} ({100*n/len(gaps):.0f}%)")
print("    -> 'betting at the last minute' is only possible where this number is small.")

# ---- 1 + 2 + 3: the horizon sweep ----------------------------------------------------------------
print("\n" + "="*84)
print("  1-3. THE HORIZON SWEEP: what you can SEE, what you can BET, and what it EARNS")
print("="*84)

def corr(xs, ys):
    n = len(xs)
    if n < 10: return None, None
    mx, my = sum(xs)/n, sum(ys)/n
    sx = (sum((a-mx)**2 for a in xs)/n)**.5; sy = (sum((b-my)**2 for b in ys)/n)**.5
    if not (sx and sy): return None, None
    r = sum((a-mx)*(b-my) for a, b in zip(xs, ys))/n/(sx*sy)
    return r, r*math.sqrt((n-2)/max(1e-9, 1-r*r))

def roi(xs):
    n = len(xs)
    if n < 20: return None
    m = sum(xs)/n; sd = (sum((x-m)**2 for x in xs)/(n-1))**.5
    return (m*100, m/(sd/math.sqrt(n)) if sd else 0, n)

HORIZONS = [("T-8h", 8.0), ("T-6h", 6.0), ("T-4h", 4.0), ("T-3h", 3.0), ("T-2h", 2.0),
            ("T-1h", 1.0), ("T-30m", 0.5), ("T-15m", 0.25), ("last capture", -99.0)]
print(f"    {'horizon':<14}{'props':>7}{'see drift':>11}{'catch rate':>12}"
      f"{'all overs':>12}{'skip-drift':>13}{'t':>7}")
rows_out = []
for label, h in HORIZONS:
    vis, ful, all_r, skip_r = [], [], [], []
    for p in props:
        if h < 0:                                     # "last capture" = the true last-minute bet,
            if p["last_gap_h"] > 1.0: continue        # and only where we really captured near tip
            pre = p["s"]
        else:
            cut = p["tip"] - datetime.timedelta(hours=h)
            pre = [x for x in p["s"] if x[0] <= cut]
        if len(pre) < 2: continue
        price = pre[-1][1]
        d = pre[-1][1]/pre[0][1] - 1                  # drift OPEN -> this horizon only
        vis.append(d); ful.append(p["full_drift"])
        r = (price - 1) if p["won"] else -1.0
        all_r.append(r)
        if d < 0.01: skip_r.append(r)                 # the live rule: skip if lengthened >=1%
    if len(vis) < 20: continue
    r_, _ = corr(vis, ful)
    drifters = [(v, fu) for v, fu in zip(vis, ful) if fu >= 0.01]
    catch = sum(1 for v, fu in drifters if v >= 0.01)/len(drifters) if drifters else 0
    a, sk = roi(all_r), roi(skip_r)
    print(f"    {label:<14}{len(vis):>7}{(r_ or 0):>11.2f}{catch*100:>11.0f}%"
          f"{(f'{a[0]:+.1f}%' if a else '-'):>12}{(f'{sk[0]:+.1f}%' if sk else '-'):>13}"
          f"{(f'{sk[1]:+.2f}' if sk else '-'):>7}")
    rows_out.append((label, len(vis), r_, catch, a, sk))
print("\n    'see drift'  = correlation between the drift visible NOW and the final open->close drift")
print("    'catch rate' = of the props that DO end up drifting, how many already show it by then")
print("    -> this is the whole argument for betting late: the filter only works on what you can see.")

# ---- 4. the replacement instrument ---------------------------------------------------------------
print("\n" + "="*84)
print("  4. IF CLV DIES, WHAT REPLACES IT? -> PINNACLE'S FAIR PRICE, READ AT BET TIME")
print("="*84)
pinn = collections.defaultdict(list)
for r in load("pinn_snapshots.csv"):
    t, ln, fair = ts(r.get("captured_utc")), f(r.get("pinn_line")), f(r.get("pinn_fair"))
    if t and ln is not None and fair:
        pinn[(r.get("date",""), (r.get("player") or "").lower(), r.get("market"), r.get("side"))].append((t, ln, fair))
for v in pinn.values(): v.sort()
print(f"    {sum(len(v) for v in pinn.values())} Pinnacle prop snapshots across {len(pinn)} player-market-sides")

# TIME-ALIGNED match: for each Pinnacle snapshot, find the 1xbet price on the IDENTICAL line
# captured within 90 minutes of it. Comparing "our last price" to "their last price" would mix
# readings taken hours apart, which is not a fair comparison of two books at one moment.
board = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None and b.get("market") in ("pts","pra","pr","pa"):
        board[((b.get("player") or "").lower(), b.get("market"), b.get("side"), ln)].append((t, o))
for v in board.values(): v.sort()

matched = []
for (dkey, pl, mk, side), pv in pinn.items():
    for pt, pln, fair in pv:
        cand = board.get((pl, mk, side, pln))
        if not cand: continue
        near = min(cand, key=lambda x: abs((x[0]-pt).total_seconds()))
        if abs((near[0]-pt).total_seconds()) > 90*60: continue
        matched.append(dict(pl=pl, mk=mk, side=side, line=pln, ours=near[1], fair=fair,
                            lag_m=abs((near[0]-pt).total_seconds())/60))
if matched:
    ev = [m["ours"]/m["fair"] - 1 for m in matched]
    mu = sum(ev)/len(ev)
    sd = (sum((x-mu)**2 for x in ev)/(len(ev)-1))**.5
    beats = sum(1 for x in ev if x > 0)
    print(f"    {len(matched)} time-aligned pairs (same player, market, side, line; within 90 min)")
    print(f"    median time gap between the two readings: "
          f"{sorted(m['lag_m'] for m in matched)[len(matched)//2]:.0f} min")
    print(f"    mean (1xbet price / Pinnacle FAIR price - 1) = {mu*100:+.1f}%   "
          f"t={mu/(sd/math.sqrt(len(ev))):+.1f}")
    print(f"    1xbet priced ABOVE fair: {beats}/{len(matched)} ({100*beats/len(matched):.1f}%)")
    for lbl, sel in (("Over", [m for m in matched if m["side"]=="Over"]),
                     ("Under", [m for m in matched if m["side"]=="Under"])):
        if len(sel) >= 10:
            e = [m["ours"]/m["fair"]-1 for m in sel]
            print(f"      {lbl:<6} n={len(sel):<5} mean {100*sum(e)/len(e):+.1f}%   "
                  f"above fair {100*sum(1 for x in e if x>0)/len(e):.0f}%")
    print(f"\n    READ THIS AS THE PRICE OF ADMISSION:")
    print(f"      every 1xbet prop we take starts {abs(mu)*100:.1f}% behind the sharp fair price.")
    print(f"      A filter has to find a mispricing BIGGER than that before a bet makes money.")
    good = sorted([m for m in matched if m["ours"] > m["fair"]], key=lambda m: -(m["ours"]/m["fair"]))
    print(f"    pairs where 1xbet was actually the better price: {len(good)}")
    for m in good[:6]:
        print(f"        {m['pl'][:20]:<20} {m['mk']:<4} {m['side']:<5} {m['line']:<5} "
              f"1xbet {m['ours']:.2f} vs fair {m['fair']:.2f} = {100*(m['ours']/m['fair']-1):+.1f}%")
else:
    print("    NO time-aligned overlap. Pinnacle cannot serve as the reference on this data.")

print("\n" + "="*84)
print("  WHAT THIS MEANS FOR A LAST-MINUTE BETTOR")
print("="*84)
print("    * Odds-CLV against OUR OWN close is dead by construction - we would be the close.")
print("    * Drift stops being a risk and becomes a fully-observable filter input.")
print("    * The measuring instrument has to move to an EXTERNAL reference read at bet time,")
print("      not a later one: our price vs Pinnacle's fair price on the identical line.")
