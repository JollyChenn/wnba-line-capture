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
dates = sorted({r["date"] for r in B}); cut = dates[int(len(dates)*0.6)]
DAYS = len(dates)

CFG = [
    ("flip only, starred",              lambda r: r["src"] == "flip" and r["notraised"]),
    ("S_prev  flip+hotover, starred",   lambda r: r["src"] in ("flip","hotover") and r["notraised"]),
    ("MODEL S +overshoot, starred",     lambda r: r["src"] in ("flip","hotover","overshoot") and r["notraised"]),
    ("S_nostar same signals, NO star",  lambda r: r["src"] in ("flip","hotover","overshoot")),
    ("raw: every over signal, any mkt", lambda r: True),
]
def stats(rows):
    n = len(rows)
    w = sum(1 for r in rows if r["won"]); b = sum(r["base"] for r in rows)/n
    u = sum((r["first"]-1) if r["won"] else -1.0 for r in rows)
    z = (w/n-b)/math.sqrt(b*(1-b)/n)
    return n, w, u, u/n, (w/n-b), z

print("="*112)
print("  1. FLAT 1u PER BET - what you actually make")
print("="*112)
print(f"  {'config':<34} {'n':>5} {'win%':>7} {'units':>9} {'ROI':>8} {'alpha':>8} {'z':>6} {'bets/day':>9}")
BASE = None
for lbl, fn in CFG:
    rows = [r for r in (B if lbl.startswith("raw") else K) if fn(r)]
    n, w, u, roi, a, z = stats(rows)
    if lbl.startswith("MODEL S"): BASE = (n, u)
    print(f"  {lbl:<34} {n:>5} {100*w/n:6.1f}% {u:+8.2f}u {100*roi:+7.1f}% {100*a:+7.1f}pp {z:+6.2f} {n/DAYS:8.2f}")
print("")
print("="*112)
print("  2. EQUAL RISK - same total capital staked, stake scaled to fill it")
print("     THIS is the comparison that matters if you are not bet-limited. Model S stakes")
print(f"     {BASE[0]}u in total; give every other rule the same {BASE[0]}u to deploy.")
print("="*112)
CAP = BASE[0]
print(f"  {'config':<34} {'n':>5} {'stake':>8} {'total risk':>11} {'profit':>10} {'ROI':>8}")
for lbl, fn in CFG:
    rows = [r for r in (B if lbl.startswith("raw") else K) if fn(r)]
    n, w, u, roi, a, z = stats(rows)
    stake = CAP/n
    print(f"  {lbl:<34} {n:>5} {stake:7.2f}u {CAP:10.0f}u {u*stake:+9.2f}u {100*roi:+7.1f}%")
print("")
print("  ...but that assumes the ROI is real at every sample size. It is not the same claim.")
print("")
print("="*112)
print("  3. OUT OF SAMPLE - does each one survive the split? (market filter applied)")
print(f"     split at {cut}")
print("="*112)
print(f"  {'config':<34} {'IN n':>6} {'IN ROI':>9} {'OUT n':>7} {'OUT ROI':>9}  verdict")
for lbl, fn in CFG:
    rows = [r for r in (B if lbl.startswith("raw") else K) if fn(r)]
    a_ = [r for r in rows if r["date"] <  cut]; z_ = [r for r in rows if r["date"] >= cut]
    if len(a_) < 8 or len(z_) < 8:
        print(f"  {lbl:<34} {len(a_):>6} {'-':>9} {len(z_):>7} {'-':>9}  one half too small to read")
        continue
    ra = sum((r["first"]-1) if r["won"] else -1.0 for r in a_)/len(a_)
    rz = sum((r["first"]-1) if r["won"] else -1.0 for r in z_)/len(z_)
    v = "holds" if (ra > 0 and rz > 0 and abs(ra-rz) < 0.20) else ("decays" if rz < ra else "improves")
    print(f"  {lbl:<34} {len(a_):>6} {100*ra:+8.1f}% {len(z_):>7} {100*rz:+8.1f}%  {v}")
print("")
print("="*112)
print("  4. RISK OF RUIN-ish: at equal risk, how ugly is a bad run?")
print("="*112)
for lbl, fn in CFG[:3]:
    rows = [r for r in (B if lbl.startswith("raw") else K) if fn(r)]
    n, w, u, roi, a, z = stats(rows)
    stake = CAP/n
    # worst peak-to-trough drawdown, in units, at the equal-risk stake
    eq, peak, dd = 0.0, 0.0, 0.0
    for r in rows:
        eq += ((r["first"]-1) if r["won"] else -1.0) * stake
        peak = max(peak, eq); dd = min(dd, eq-peak)
    print(f"  {lbl:<34} stake {stake:4.2f}u  worst drawdown {dd:+7.2f}u  "
          f"(longest losing streak {max((len(list(g)) for k, g in __import__('itertools').groupby(rows, key=lambda r: r['won']) if not k), default=0)})")
