# reaudit_drift.py - attack the "skip-drift adds nothing" finding before believing it.
# ---------------------------------------------------------------------------------------------
# The claim is strong and negative, so it gets the same scepticism a positive result would.
# Four ways it could be wrong, each tested:
#   1 SELECTION - the fixed cohort needs 2+ captures 10h before tip, i.e. EARLY-POSTED lines.
#     If drift mostly afflicts late-posted lines, that cohort excludes the very bets the rule
#     exists for, and the test is rigged against finding an effect.
#   2 VISIBILITY - if most of the open->close move happens in the final hours, then a filter
#     reading the price at T-2h genuinely cannot see it. That would mean the rule is unusable,
#     not that drift is uninformative - a different conclusion with different consequences.
#   3 STALE SERIES - bets_log only records a row when the signal fires. If a bet stops being
#     emitted, its series ends early and "the price then" is actually an older price.
#   4 THE ORIGINAL CLAIM - does the -28%/-22% drifted bucket even reproduce, and is it an
#     artifact of paying at the OPENING price?
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
def st(rets, label="", show=True):
    n = len(rets)
    if n < 8:
        if show: print(f"    {label:<46} n={n} (too few)")
        return None
    m = sum(rets)/n; sd = (sum((x-m)**2 for x in rets)/(n-1))**.5
    t = m/(sd/math.sqrt(n))
    if show: print(f"    {label:<46} n={n:<4} ROI={m*100:+6.1f}%  t={t:+5.2f}")
    return n, m*100, t

LIVE = ("flip", "flip_paper", "overshoot", "cascade"); DRIFT = 0.01
games = load("data/games_2026.csv"); tip_by = {}
for g in games:
    t = ts(g.get("tip"))
    if t:
        for k in ("home", "away"):
            if g.get(k): tip_by[(g.get("date", ""), g[k])] = t
gdm = {g.get("game_id"): g.get("date", "") for g in games}; tip_pl = {}
for r in load("data/box_2026.csv"):
    d, pl, tm = gdm.get(r.get("game_id"), ""), (r.get("player") or "").lower(), r.get("team") or ""
    if d and pl and (d, tm) in tip_by: tip_pl[(d, pl)] = tip_by[(d, tm)]
series = collections.defaultdict(list)
for r in load("bets_log.csv"):
    t, o, ln = ts(r.get("captured_utc")), f(r.get("odds")), f(r.get("line"))
    if t and o: series[(r.get("date"), r.get("player"), r.get("market"), r.get("side"))].append((t, ln, o))
graded = [r for r in load("graded_bets.csv")
          if (r.get("result") or "").upper() in ("WIN", "LOSS") and r.get("src") in LIVE]

def snapshot(r, hrs):
    """What the live system could see `hrs` before this bet's tip. None if not evaluable."""
    d8 = r.get("date", "").replace("-", "")
    tip = tip_pl.get((d8, (r.get("player") or "").lower()))
    if not tip: return None
    sd = f"{d8[:4]}-{d8[4:6]}-{d8[6:8]}"
    ser = sorted(x for x in series.get((sd, r.get("player"), r.get("market"), r.get("side")), [])
                 if x[0] <= tip - datetime.timedelta(hours=hrs))
    if len(ser) < 2: return None
    cur = ser[-1][1]
    cl = [x for x in ser if x[1] == cur]
    if len(cl) < 2: return None
    lag = (tip - datetime.timedelta(hours=hrs) - cl[-1][0]).total_seconds()/3600
    return dict(move=cl[-1][2]/cl[0][2]-1, price=cl[-1][2], ncap=len(cl), lag=lag, tip=tip)

ret_of = lambda r, price: (price-1) if r["result"].upper() == "WIN" else -1.0

print("\n" + "="*78)
print("  4. DOES THE ORIGINAL -28% CLAIM EVEN REPRODUCE?")
print("="*78)
for pay, lbl in ((False, "paid at OPENING price (how it was first reported)"),
                 (True, "paid at CLOSING price (the honest version)")):
    print(f"  {lbl}")
    dr, kp = [], []
    for r in graded:
        o, clv = f(r.get("odds")), f(r.get("odds_clv"))
        if o is None or clv is None: continue
        price = o/(1+clv) if pay else o
        (dr if clv < -DRIFT else kp).append(ret_of(r, price))
    st(kp, "kept (no drift)"); st(dr, "DRIFTED bucket")

print("\n" + "="*78)
print("  1. SELECTION - is the fixed cohort rigged against finding an effect?")
print("="*78)
cohort = [r for r in graded if snapshot(r, 10.0) and snapshot(r, 1.0)]
rest = [r for r in graded if r not in cohort]
def drift_rate(rows):
    n = sum(1 for r in rows if f(r.get("odds_clv")) is not None)
    d = sum(1 for r in rows if (f(r.get("odds_clv")) or 0) < -DRIFT)
    return f"{d}/{n} = {100*d/n:.0f}%" if n else "-"
print(f"    drift rate INSIDE the fixed cohort : {drift_rate(cohort)}")
print(f"    drift rate OUTSIDE it              : {drift_rate(rest)}")
print("    -> if these are similar, the cohort is not dodging the drifted bets")

print("\n" + "="*78)
print("  2. VISIBILITY - how much of the final move is on the board at T-2h?")
print("="*78)
seen, total, caught, missed = [], [], 0, 0
for r in graded:
    s = snapshot(r, 2.0); clv = f(r.get("odds_clv"))
    if not s or clv is None: continue
    final = -clv                       # +ve = lengthened by close, same sign as `move`
    seen.append(s["move"]); total.append(final)
    if final > DRIFT:                  # genuinely drifted by close
        if s["move"] >= DRIFT: caught += 1
        else: missed += 1
if seen:
    n = len(seen)
    mx, my = sum(seen)/n, sum(total)/n
    cov = sum((a-mx)*(b-my) for a, b in zip(seen, total))/n
    sx = (sum((a-mx)**2 for a in seen)/n)**.5; sy = (sum((b-my)**2 for b in total)/n)**.5
    print(f"    correlation(move at T-2h, full move to close) = {cov/(sx*sy):+.2f}   (n={n})")
    print(f"    median |move| visible at T-2h = {sorted(abs(x) for x in seen)[n//2]*100:.2f}%")
    print(f"    median |move| by close        = {sorted(abs(x) for x in total)[n//2]*100:.2f}%")
    print(f"    of bets that DID drift by close: {caught} already visible at T-2h, {missed} not yet")
    if caught + missed:
        print(f"    -> the filter can only ever see {100*caught/(caught+missed):.0f}% of them")

print("\n" + "="*78)
print("  3. STALE SERIES - is 'the price then' actually current?")
print("="*78)
lags = [snapshot(r, 2.0)["lag"] for r in graded if snapshot(r, 2.0)]
if lags:
    lags.sort()
    print(f"    hours between the last capture and the T-2h decision point:")
    print(f"      median {lags[len(lags)//2]:.1f}h   75th {lags[int(len(lags)*.75)]:.1f}h   "
          f"90th {lags[int(len(lags)*.90)]:.1f}h   max {lags[-1]:.1f}h")
    print(f"    -> a large lag means we are judging an old price, not the live one")

print("\n" + "="*78)
print("  THE TEST, on the FULL sample (not the cohort), paid at the price then")
print("="*78)
for hrs in (6.0, 2.0):
    print(f"  --- T-{hrs:.0f}h ---")
    keep, skip, allr = [], [], []
    for r in graded:
        s = snapshot(r, hrs)
        if not s: continue
        ret = ret_of(r, s["price"])
        allr.append(ret)
        (skip if s["move"] >= DRIFT else keep).append(ret)
    st(allr, "every bet (no filter)")
    st(keep, "kept by skip-drift")
    st(skip, "THROWN AWAY by skip-drift")

print("\n" + "="*78)
print("  IS 1% TOO TWITCHY FOR A HALF-SEEN SIGNAL? threshold sweep at late horizons")
print("="*78)
for hrs in (2.0, 1.0, 0.5):
    snaps = [(r, snapshot(r, hrs)) for r in graded]
    snaps = [(r, s) for r, s in snaps if s]
    if not snaps: continue
    mv = sorted(abs(s["move"]) for _, s in snaps)
    nz = sum(1 for x in mv if x > 0.001)
    print(f"  --- T-{hrs}h ---   {nz}/{len(mv)} bets have moved AT ALL ({100*nz/len(mv):.0f}%)")
    st([ret_of(r, s["price"]) for r, s in snaps], "no filter")
    for thr in (0.01, 0.02, 0.03, 0.05):
        keep = [ret_of(r, s["price"]) for r, s in snaps if s["move"] < thr]
        drop = [ret_of(r, s["price"]) for r, s in snaps if s["move"] >= thr]
        a = st(keep, "", show=False); b = st(drop, "", show=False)
        if a:
            print(f"    skip if drift >= {thr*100:>2.0f}%    kept n={a[0]:<4} ROI={a[1]:+6.1f}% t={a[2]:+5.2f}"
                  f"   |  dropped n={len(drop):<3} ROI={(f'{b[1]:+.1f}%' if b else 'n/a'):>8}")
