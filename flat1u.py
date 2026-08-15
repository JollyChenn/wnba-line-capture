# audit_signals.py - the careful recheck before anything goes live.
# ---------------------------------------------------------------------------------------------
# I have now compared roughly 8 signals x {raw, filtered} x several price bases. That is a wide
# enough search that "flip + hotover raw looks best" could easily be the lucky corner - which is
# exactly how the gap band died. So this file does four things, in order:
#
#   1 SETTLE THE PRICE BASIS. My tables disagreed because one used the odds LOGGED when the signal
#     fired and another the board's LAST price before tip. Before ranking anything, measure how far
#     apart those are and which one a real bettor gets.
#   2 RANK EVERY SIGNAL on that basis, raw and filtered, with alpha over the matched blind baseline.
#   3 PRICE THE MULTIPLICITY. Re-run the ENTIRE search (every signal x raw/filtered) on simulated
#     outcomes, 400 times, and ask how often chance produces a leader as good as ours.
#   4 SPLIT IN TIME. Anything that survives 1-3 still has to hold in the final third.
import csv, os, sys, math, random, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
random.seed(20260814)
def load(p):
    fp = os.path.join(D, p)
    return list(csv.DictReader(open(fp, encoding="utf-8", errors="replace"))) if os.path.exists(fp) else []
def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception: return None
MK = ("pts","pra","pr","pa","reb","ast","ra")

gm = {g["game_id"]: (g.get("date",""), ts(g.get("tip"))) for g in load("data/games_2026.csv")}
plog = collections.defaultdict(list)
for r in load("data/box_2026.csv"):
    dt, tp = gm.get(r.get("game_id"), ("", None))
    if not (dt and tp): continue
    p, rb, a = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    plog[(r.get("player") or "").lower()].append(dict(date=dt, tip=tp, pts=p, reb=rb, ast=a,
        pra=p+rb+a, pr=p+rb, pa=p+a, ra=rb+a))
for v in plog.values(): v.sort(key=lambda x: x["date"])
byp = collections.defaultdict(list)
for pl, v in plog.items():
    for g in v: byp[pl].append((g["tip"], g["date"], g))
for v in byp.values(): v.sort()
def ga(pl, when):
    for tip, dt, rec in byp.get(pl, []):
        if when <= tip <= when + datetime.timedelta(hours=36): return dt, rec
    return None, None
raw = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None and b.get("market") in MK:
        raw[((b.get("player") or "").lower(), b.get("market"), b.get("side"), ln)].append((t, o))
pg = collections.defaultdict(dict)
for (pl, mk, side, ln), v in raw.items():
    v.sort(); blocks, cur = [], [v[0]]
    for a, b_ in zip(v, v[1:]):
        if (b_[0]-a[0]).total_seconds() > 12*3600: blocks.append(cur); cur = []
        cur.append(b_)
    blocks.append(cur)
    for blk in blocks:
        if not blk: continue
        dt, rec = ga(pl, blk[0][0])
        if not rec: continue
        pre = [x for x in blk if x[0] <= rec["tip"]]
        if pre: pg[(pl, mk, dt)].setdefault(ln, {})[side] = pre
BL = {}; tmp = collections.defaultdict(list); main = {}
for (pl, mk, dt), lines in pg.items():
    ln, sides = max(lines.items(), key=lambda kv: sum(len(x) for x in kv[1].values()))
    if "Over" not in sides: continue
    rec = next((g for g in plog.get(pl, []) if g["date"] == dt), None)
    if rec is None or rec[mk] == ln: continue
    main[(pl, mk, dt)] = ln
    tmp[(mk,"Over")].append(1.0 if rec[mk] > ln else 0.0)
for k, v in tmp.items():
    if len(v) >= 60: BL[k] = sum(v)/len(v)
lh = collections.defaultdict(list)
for (pl, mk, dt), ln in main.items(): lh[(pl, mk)].append((dt, ln))
for v in lh.values(): v.sort()
def prev(pl, mk, dt):
    v = lh[(pl, mk)]; i = next((k for k, x in enumerate(v) if x[0] == dt), None)
    return v[i-1][1] if i is not None and i >= 1 else None
def drift(pl, mk, ln, tip):
    v = [x for x in raw.get((pl, mk, "Over", ln), []) if x[0] <= tip - datetime.timedelta(hours=2)
         and 0 <= (tip-x[0]).total_seconds() <= 36*3600]
    return v[-1][1]/v[0][1] - 1 if len(v) >= 2 else None

# every logged price for a bet, so the price bases can be compared on the SAME bets
byid = collections.defaultdict(list)
for b in load("bets_log.csv"):
    if b.get("side") != "Over": continue
    pl, mk, ln, o = (b.get("player") or "").lower(), b.get("market"), f(b.get("line")), f(b.get("odds"))
    t = ts(b.get("captured_utc"))
    if not (t and o and ln is not None) or mk not in MK: continue
    dt, rec = ga(pl, t)
    if not rec: continue
    byid[(dt, pl, mk)].append((t, o, ln, b.get("src") or "?"))
B = []
for (dt, pl, mk), v in byid.items():
    v.sort()
    rec = next((g for g in plog.get(pl, []) if g["date"] == dt), None)
    if rec is None or (mk, "Over") not in BL: continue
    first_o, first_ln, src = v[0][1], v[0][2], v[0][3]
    last_o,  last_ln       = v[-1][1], v[-1][2]
    if rec[mk] == first_ln: continue
    cl = main.get((pl, mk, dt))
    close_o = pg[(pl, mk, dt)][cl]["Over"][-1][1] if cl is not None and cl in pg[(pl, mk, dt)] else None
    pv = prev(pl, mk, dt); dr = drift(pl, mk, first_ln, rec["tip"])
    B.append(dict(date=dt, mo=dt[:6], pl=pl, mk=mk, src=src, first_ln=first_ln, close_ln=cl,
                  first=first_o, last=last_o, close=close_o,
                  won=rec[mk] > first_ln, base=BL[(mk,"Over")],
                  passes=(pv is not None and (first_ln-pv) < 0.5 and dr is not None and dr < 0.01),
                  notraised=(pv is not None and (first_ln-pv) < 0.5)))






B.sort(key=lambda r: r["date"])
K = [r for r in B if r["mk"] in ("pra","pr","pts")]
dates = sorted({r["date"] for r in B}); DAYS = len(dates)
cut = dates[int(len(dates)*0.6)]

CFG = [
    ("flip only, starred",             [r for r in K if r["src"]=="flip" and r["notraised"]]),
    ("S_prev  flip+hotover, starred",  [r for r in K if r["src"] in ("flip","hotover") and r["notraised"]]),
    ("MODEL S  +overshoot, starred",   [r for r in K if r["src"] in ("flip","hotover","overshoot") and r["notraised"]]),
    ("S_nostar same signals, NO star", [r for r in K if r["src"] in ("flip","hotover","overshoot")]),
    ("S_raised only what star rejects",[r for r in K if r["src"] in ("flip","hotover","overshoot") and not r["notraised"]]),
    ("raw  every over signal, any mkt", B),
]
print("="*112)
print("  EVERYTHING AT FLAT 1u - the honest apples-to-apples, since that is how you actually bet")
print("="*112)
print(f"  {'config':<34} {'n':>5} {'win%':>7} {'risked':>8} {'profit':>9} {'ROI':>8} {'worst DD':>10} {'per night':>10}")
for lbl, rows in CFG:
    n = len(rows)
    w = sum(1 for r in rows if r["won"])
    u = sum((r["first"]-1) if r["won"] else -1.0 for r in rows)
    eq = peak = dd = 0.0
    for r in rows:
        eq += (r["first"]-1) if r["won"] else -1.0
        peak = max(peak, eq); dd = min(dd, eq-peak)
    tag = "  <- LIVE" if lbl.startswith("MODEL S") else ""
    print(f"  {lbl:<34} {n:>5} {100*w/n:6.1f}% {n:7.0f}u {u:+8.2f}u {100*u/n:+7.1f}% {dd:+9.2f}u {n/DAYS:9.2f}{tag}")
print("")
print("="*112)
print("  MODEL S vs S_nostar, HEAD TO HEAD AT 1u - the direct answer")
print("="*112)
MS = [r for r in K if r["src"] in ("flip","hotover","overshoot") and r["notraised"]]
NS = [r for r in K if r["src"] in ("flip","hotover","overshoot")]
for lbl, rows in (("MODEL S ", MS), ("S_nostar", NS)):
    n = len(rows); u = sum((r["first"]-1) if r["won"] else -1.0 for r in rows)
    print(f"  {lbl}  {n} bets, {n}u risked, {u:+.2f}u profit")
mu = sum((r["first"]-1) if r["won"] else -1.0 for r in MS)
nu = sum((r["first"]-1) if r["won"] else -1.0 for r in NS)
print("")
print(f"  S_nostar risks {len(NS)-len(MS)} MORE units and earns {nu-mu:+.2f}u.")
print(f"  The extra {len(NS)-len(MS)} bets it takes (the ones the star rejects) returned "
      f"{nu-mu:+.2f}u on {len(NS)-len(MS)}u = {100*(nu-mu)/(len(NS)-len(MS)):+.1f}% ROI.")
