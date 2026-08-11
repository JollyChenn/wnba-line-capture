# minutes_hunt.py - MINUTES are what kill props. Can we predict them, and does the book price it?
# ---------------------------------------------------------------------------------------------
# drift_mechanism.py (n=2331) showed prop drift is NOT a minutes read - drifted players actually
# play slightly MORE than their norm. Yet minutes are the thing that destroys a prop: Juskaite
# played 14 min and scored 0 on a 9.5 line. So the book is not obviously pricing minutes risk,
# which makes it the one place left worth hunting.
#
# PHASE 1  what predicts a player's minutes deviating from their own trailing norm?
# PHASE 2  does that prediction translate into prop profit, after every gate:
#            - date split, search IN-SAMPLE only
#            - exhaustive pre-declared grid, no hand-picked cells
#            - 300-run calibration-preserving null (simulate outcomes from the line's own implied
#              probability, so "the line is right" is the hypothesis being tested)
#            - single OOS test of the winner
#            - 1xbet prop vig is ~11%, so break-even at 1.80 is 55.6% - that is the real bar
# ALL features use PRIOR games only. Any feature touching the game itself is look-ahead.
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

# ---- games -------------------------------------------------------------------------------------
games = load("data/games_2026.csv")
ginfo = {}
for g in games:
    hs, as_ = f(g.get("home_score")), f(g.get("away_score"))
    ginfo[g.get("game_id")] = dict(date=g.get("date", ""), home=g.get("home"), away=g.get("away"),
                                   hs=hs, as_=as_,
                                   margin=(abs(hs-as_) if hs is not None and as_ is not None else None),
                                   total=((hs+as_) if hs is not None and as_ is not None else None))

# ---- per-player game log, in date order ---------------------------------------------------------
plog = collections.defaultdict(list)
for r in load("data/box_2026.csv"):
    gi = ginfo.get(r.get("game_id"))
    if not gi or not gi["date"]: continue
    pl = (r.get("player") or "").lower()
    pts, reb, ast = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    plog[pl].append(dict(date=gi["date"], d=dparse(gi["date"]), gid=r.get("game_id"),
                         team=r.get("team"), min=f(r.get("min")) or 0,
                         pts=pts, reb=reb, ast=ast, pra=pts+reb+ast, pr=pts+reb, pa=pts+ast,
                         fouls=f(r.get("pf")) or 0, margin=gi["margin"],
                         home=(r.get("team") == gi["home"])))
for v in plog.values(): v.sort(key=lambda x: x["date"])

# team game dates, for team-level rest
tdates = collections.defaultdict(set)
for pl, v in plog.items():
    for g in v:
        if g["team"] and g["d"]: tdates[g["team"]].add(g["d"])

# ---- FEATURES, all from PRIOR games only --------------------------------------------------------
rows = []
for pl, v in plog.items():
    for i, g in enumerate(v):
        prev = v[:i]
        if len(prev) < 6: continue                      # need a baseline
        last10 = prev[-10:]; last3 = prev[-3:]; last5 = prev[-5:]
        m10 = sum(x["min"] for x in last10)/len(last10)
        if m10 <= 8: continue                           # deep-bench noise
        m3 = sum(x["min"] for x in last3)/3
        m5 = sum(x["min"] for x in last5)/5
        sd10 = (sum((x["min"]-m10)**2 for x in last10)/max(1, len(last10)-1))**.5
        rest = (g["d"] - prev[-1]["d"]).days if (g["d"] and prev[-1]["d"]) else None
        team_prev = sorted(d for d in tdates.get(g["team"], set()) if g["d"] and d < g["d"])
        trest = (g["d"] - team_prev[-1]).days if team_prev else None
        rows.append(dict(
            pl=pl, date=g["date"], gid=g["gid"], team=g["team"], mk_actual=g,
            # --- predictors (prior only) ---
            min_norm=m10, min_trend=m3-m10, min_trend5=m5-m10, min_sd=sd10,
            min_cv=sd10/m10, rest=rest, team_rest=trest,
            b2b=1.0 if (rest is not None and rest <= 1) else 0.0,
            long_rest=1.0 if (rest is not None and rest >= 4) else 0.0,
            prev_min=prev[-1]["min"], prev_min_vs_norm=prev[-1]["min"]-m10,
            prev_fouls=prev[-1]["fouls"],
            prev_blowout=1.0 if (prev[-1]["margin"] or 0) >= 20 else 0.0,
            home=1.0 if g["home"] else 0.0,
            games_in=len(prev),
            # --- outcome ---
            min_dev=g["min"]-m10, min_ratio=g["min"]/m10,
        ))
print(f"PHASE 1: {len(rows)} player-games with a 6+ game history\n")

def corr(xs, ys):
    n = len(xs)
    if n < 30: return None
    mx, my = sum(xs)/n, sum(ys)/n
    cov = sum((a-mx)*(b-my) for a, b in zip(xs, ys))/n
    sx = (sum((a-mx)**2 for a in xs)/n)**.5; sy = (sum((b-my)**2 for b in ys)/n)**.5
    if not (sx and sy): return None
    r = cov/(sx*sy)
    t = r*math.sqrt((n-2)/max(1e-9, 1-r*r))
    return r, t, math.erfc(abs(t)/math.sqrt(2)), n

FEATS = ["min_trend", "min_trend5", "min_sd", "min_cv", "rest", "team_rest", "b2b", "long_rest",
         "prev_min_vs_norm", "prev_fouls", "prev_blowout", "home", "games_in", "min_norm"]
print(f"  {'feature':<22}{'r vs minutes deviation':>24}{'t':>8}{'p':>9}")
res1 = []
for k in FEATS:
    xs = [r[k] for r in rows if r.get(k) is not None]
    ys = [r["min_dev"] for r in rows if r.get(k) is not None]
    c = corr(xs, ys)
    if c:
        res1.append((abs(c[1]), k, c))
        print(f"  {k:<22}{c[0]:>24.3f}{c[1]:>8.2f}{c[2]:>9.4f}")
res1.sort(reverse=True)
print(f"\n  {len(FEATS)} features tested -> Bonferroni threshold p < {0.05/len(FEATS):.4f}")
print(f"  survivors: " + (", ".join(k for _, k, c in res1 if c[2] < 0.05/len(FEATS)) or "NONE"))

# =================================================================================================
# PHASE 2 - minutes are predictable. Does the BOOK already price that?
# =================================================================================================
# Build a minutes forecast from the surviving features, turn it into a production forecast using
# the player's own per-minute rate, and compare to the posted line. If the book prices minutes
# properly there is no edge; if it does not, the gap should predict the over/under.
print("\n" + "="*78)
print("  PHASE 2: does a minutes forecast beat the posted prop line?")
print("="*78)

idx = {(r["pl"], r["date"]): r for r in rows}
for r in rows:                                        # per-minute rate from PRIOR games only
    v = plog[r["pl"]]
    prev = [x for x in v if x["date"] < r["date"]][-10:]
    tot_min = sum(x["min"] for x in prev)
    r["rate"] = {mk: (sum(x[mk] for x in prev)/tot_min if tot_min > 0 else None)
                 for mk in ("pts", "pra", "pr", "pa")}
    # forecast: the two strongest predictors, both already in minutes units
    r["pred_dev"] = 0.5*(r["min_trend"] + r["prev_min_vs_norm"])
    r["pred_min"] = max(0.0, r["min_norm"] + r["pred_dev"])

props = []
seen = set()
for b in load("xbet_board.csv"):
    t, ln = ts(b.get("captured_utc")), f(b.get("line"))
    od = f(b.get("odds"))
    mk, sd = b.get("market"), b.get("side")
    if not (t and ln is not None and od and mk in ("pts", "pra", "pr", "pa")): continue
    pl = (b.get("player") or "").lower()
    d8 = t.strftime("%Y%m%d")
    r = idx.get((pl, d8))
    if not r:
        nd = dparse(d8)
        r = idx.get((pl, (nd + datetime.timedelta(days=1)).strftime("%Y%m%d"))) if nd else None
    if not r or r["rate"].get(mk) is None: continue
    key = (r["date"], pl, mk, sd, ln)
    if key in seen: continue
    seen.add(key)
    pred = r["pred_min"] * r["rate"][mk]
    actual = r["mk_actual"][mk]
    props.append(dict(date=r["date"], pl=pl, mk=mk, side=sd, line=ln, odds=od,
                      pred=pred, edge=pred-ln, actual=actual,
                      won=(actual > ln) if sd == "Over" else (actual < ln),
                      pred_dev=r["pred_dev"]))
props.sort(key=lambda x: x["date"])
cut = int(len(props)*2/3)
IN, OUT = props[:cut], props[cut:]
print(f"  {len(props)} priced props matched  ->  IN {len(IN)} (to {IN[-1]['date']})  "
      f"OUT {len(OUT)} (from {OUT[0]['date']})")

EDGES = (0.5, 1.0, 1.5, 2.0, 3.0)
SIDES = ("Over", "Under")
MKS = ("any", "pts", "pra", "pr", "pa")
def evaluate(rows_, side, thr, mk, outcomes=None):
    out = []
    for i, p in enumerate(rows_):
        if p["side"] != side: continue
        if mk != "any" and p["mk"] != mk: continue
        # bet the side our forecast disagrees with the line about
        if side == "Over" and p["edge"] < thr: continue
        if side == "Under" and p["edge"] > -thr: continue
        won = outcomes[i] if outcomes is not None else p["won"]
        out.append((p["odds"]-1) if won else -1.0)
    return out
def tstat(xs, minn=25):
    n = len(xs)
    if n < minn: return None
    m = sum(xs)/n; sd = (sum((x-m)**2 for x in xs)/(n-1))**.5
    return (m/(sd/math.sqrt(n)), m*100, n) if sd else None
def search(rows_, outcomes=None):
    best = None
    for side in SIDES:
        for thr in EDGES:
            for mk in MKS:
                r = tstat(evaluate(rows_, side, thr, mk, outcomes))
                if r and (best is None or r[0] > best[0][0]): best = (r, (side, thr, mk))
    return best

allc = []
for side in SIDES:
    for thr in EDGES:
        for mk in MKS:
            r = tstat(evaluate(IN, side, thr, mk))
            if r: allc.append((r, (side, thr, mk)))
allc.sort(key=lambda x: -x[0][0])
print(f"\n  {len(SIDES)*len(EDGES)*len(MKS)} cells declared, {len(allc)} with n>=25")
print(f"  {'rule':<34}{'n':>6}{'ROI':>9}{'t':>7}")
for (t, roi, n), (s, th, mk) in allc[:6]:
    print(f"  {f'{s} when edge>{th} [{mk}]':<34}{n:>6}{roi:>8.1f}%{t:>7.2f}")

print("\n  --- null: simulate each result from the LINE's own implied probability ---")
# implied p from the posted odds, de-vigged crudely at 11% (1xbet prop margin)
def implied(p): return min(0.98, max(0.02, (1/p["odds"]) / 1.055))
nulls = []
for _ in range(300):
    sim = [random.random() < implied(p) for p in IN]
    b = search(IN, sim)
    if b: nulls.append(b[0][0])
nulls.sort()
best_in, best_rule = allc[0]
beat = sum(1 for x in nulls if x >= best_in[0])/len(nulls)
print(f"    best t on 300 null searches: median {nulls[len(nulls)//2]:+.2f}  "
      f"95th {nulls[int(len(nulls)*.95)]:+.2f}  max {nulls[-1]:+.2f}")
print(f"    our best in-sample t = {best_in[0]:+.2f}  ->  null beats it {beat*100:.1f}% of the time  "
      f"({'PASSES' if beat < 0.05 else 'FAILS'})")

side, thr, mk = best_rule
o = tstat(evaluate(OUT, side, thr, mk), minn=15)
print(f"\n  --- OUT-OF-SAMPLE, tested once: {side} when edge>{thr} [{mk}] ---")
print(f"    in-sample     n={best_in[2]:<5} ROI={best_in[1]:+6.1f}%  t={best_in[0]:+5.2f}")
if o:
    print(f"    OUT-OF-SAMPLE n={o[2]:<5} ROI={o[1]:+6.1f}%  t={o[0]:+5.2f}")
    print(f"    -> {'HOLDS' if o[1] > 0 else 'DOES NOT HOLD'} out of sample")
else:
    print(f"    OUT-OF-SAMPLE too few bets")

# =================================================================================================
# AUDIT - a result that passes the gates gets attacked harder than one that fails
# =================================================================================================
print("\n" + "="*78)
print("  AUDIT")
print("="*78)
print(f"  1. CLUSTERING. {len(props)} props come from ~{len(set((p['date'],p['pl']) for p in props))}")
print("     player-games - the same player has several lines, and those outcomes are one event.")
print("     t-stats above are therefore INFLATED. Re-run with one bet per player-game:")
def collapse(rows_):
    best = {}
    for p in rows_:
        k = (p["date"], p["pl"])
        if k not in best or abs(p["edge"]) > abs(best[k]["edge"]): best[k] = p
    return sorted(best.values(), key=lambda x: x["date"])
cIN, cOUT = collapse(IN), collapse(OUT)
for nm, rows_ in (("IN-SAMPLE", cIN), ("OUT-OF-SAMPLE", cOUT)):
    r = tstat(evaluate(rows_, side, thr, mk), minn=10)
    print(f"     {nm:<16} n={r[2]:<5} ROI={r[1]:+6.1f}%  t={r[0]:+5.2f}" if r
          else f"     {nm:<16} too few")

print("\n  2. IS THE EDGE JUST 'BET OVERS'? the menu is over-heavy, and 2026 is a high-scoring year.")
allover = [(p["odds"]-1) if p["won"] else -1.0 for p in props if p["side"] == "Over"]
r = tstat(allover, minn=50)
print(f"     EVERY over on the board, no filter:  n={r[2]:<5} ROI={r[1]:+6.1f}%  t={r[0]:+5.2f}")
print("     -> if this is already positive, the 'edge' may be a market-wide over bias, not our model")

print("\n  3. DOES THE EDGE SIZE MATTER MONOTONICALLY? (a real signal should scale)")
for lo_, hi_ in ((0, 1), (1, 2), (2, 3), (3, 5), (5, 99)):
    sel = [(p["odds"]-1) if p["won"] else -1.0
           for p in props if p["side"] == "Over" and lo_ <= p["edge"] < hi_]
    r = tstat(sel, minn=40)
    if r: print(f"     edge {lo_}-{hi_}:  n={r[2]:<5} ROI={r[1]:+6.1f}%  t={r[0]:+5.2f}")

print("\n  4. COST. 1xbet prop margin is ~11%; these are its own posted prices, so the vig is")
print("     already inside every ROI above. No further haircut needed.")
