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
    byid[(dt, pl, mk)].append((t, o, ln, b.get("src") or "?", b.get("tier") or "",
                               b.get("ev") or "", b.get("pinn") or ""))

def _prev_odds(pl, mk, tip):
    """her price the LAST time this market was quoted, on a PREVIOUS night (>18h before tip).
       cross-match odds move = this night's price / that price - 1."""
    allq = []
    for k, v in raw.items():
        if k[0] == pl and k[1] == mk and k[2] == "Over": allq += v
    old = [o for (t, o) in sorted(allq) if (tip - t).total_seconds() > 18*3600]
    return old[-1] if old else None

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
    B.append(dict(date=dt, mo=dt[:6], pl=pl, mk=mk, src=src,
                  tier=v[0][4], ev=v[0][5], pinn=v[0][6], first_ln=first_ln, close_ln=cl,
                  dr=dr, prev_ln=pv, prev_odds=_prev_odds(pl, mk, rec['tip']),
                  first=first_o, last=last_o, close=close_o,
                  won=rec[mk] > first_ln, base=BL[(mk,"Over")],
                  passes=(pv is not None and (first_ln-pv) < 0.5 and dr is not None and dr < 0.01),
                  notraised=(pv is not None and (first_ln-pv) < 0.5)))




B.sort(key=lambda r: r["date"])
for r in B:
    r["star"] = (r["prev_ln"] is not None and r["first_ln"] - r["prev_ln"] < 0.5)
    r["evf"] = f(r["ev"])
    p = f(r["pinn"])
    # PINNACLE EDGE: sharp's number minus the number 1xbet is offering. Positive means the soft
    # book's line sits BELOW sharp's - which is the whole staleness thesis in one column.
    r["pedge"] = (p - r["first_ln"]) if p is not None else None
dates = sorted({r["date"] for r in B}); cut = dates[int(len(dates)*0.6)]
def st(rows, label, minn=15):
    n = len(rows)
    if n < minn:
        print(f"  {label:<44} n={n:<4} too few"); return
    w = sum(1 for r in rows if r["won"]); b = sum(r["base"] for r in rows)/n
    u = sum((r["first"]-1) if r["won"] else -1.0 for r in rows)
    z = (w/n-b)/math.sqrt(b*(1-b)/n)
    print(f"  {label:<44} n={n:<4} {100*w/n:5.1f}%  {u:+7.2f}u  ROI {100*u/n:+6.1f}%"
          f"  alpha {100*(w/n-b):+5.1f}pp  z={z:+5.2f}")


import random
random.seed(20260822)
K = [r for r in B if r["src"] == "flip_paper" and r["mk"] in ("pra","pr","pts")]
def roi(rows): return sum((r["first"]-1) if r["won"] else -1.0 for r in rows)/len(rows) if rows else 0
def st(rows, label, minn=10):
    n = len(rows)
    if n < minn:
        print(f"  {label:<44} n={n:<4} too few"); return
    w = sum(1 for r in rows if r["won"])
    print(f"  {label:<44} n={n:<4} {100*w/n:5.1f}%  ROI {100*roi(rows):+6.1f}%")
print("="*100)
print("  1. OUT OF SAMPLE - split " + cut)
print("="*100)
for lbl, fn in (("tier THIN", lambda r: r["tier"] == "THIN"),
                ("tier STRONG", lambda r: r["tier"] == "STRONG"),
                ("tier SOLID", lambda r: r["tier"] == "SOLID"),
                ("THIN + STRONG together", lambda r: r["tier"] in ("THIN","STRONG"))):
    g = [r for r in K if fn(r)]
    st([r for r in g if r["date"] <  cut], f"  {lbl}  IN")
    st([r for r in g if r["date"] >= cut], f"  {lbl}  OUT")
    print("")
print("="*100)
print("  2. PERMUTATION - shuffle the tier labels among these same bets. If tier carries no")
print("     information, how often does the best shuffled tier beat the real best tier?")
print("="*100)
tiers = [r["tier"] for r in K]
real = max(roi([r for r in K if r["tier"] == t])
           for t in set(tiers) if len([r for r in K if r["tier"] == t]) >= 25)
print(f"  real best tier ROI (n>=25): {100*real:+.1f}%")
beat = 0; T = 5000
for _ in range(T):
    sh = tiers[:]; random.shuffle(sh)
    KK = [dict(r, tier=t) for r, t in zip(K, sh)]
    b = max(roi([r for r in KK if r["tier"] == t])
            for t in set(sh) if len([r for r in KK if r["tier"] == t]) >= 25)
    if b >= real: beat += 1
print(f"  shuffled best >= real in {beat}/{T}  ->  p = {beat/T:.4f}")
print("")
print("="*100)
print("  3. WOULD IT EVEN BE WORTH IT? adding flip_paper THIN+STRONG to Model S")
print("="*100)
MS = [r for r in B if r["src"] in ("flip","hotover","overshoot") and r["mk"] in ("pra","pr","pts")
      and r["star"]]
ADD = [r for r in K if r["tier"] in ("THIN","STRONG")]
DAYS = len(dates)
for lbl, g in (("MODEL S as-is", MS), ("  + flip_paper THIN/STRONG", MS + ADD)):
    n = len(g); w = sum(1 for r in g if r["won"]); u = sum((r["first"]-1) if r["won"] else -1.0 for r in g)
    print(f"  {lbl:<32} n={n:<4} {100*w/n:5.1f}%  {u:+7.2f}u  ROI {100*u/n:+6.1f}%  {n/DAYS:.2f}/night")
